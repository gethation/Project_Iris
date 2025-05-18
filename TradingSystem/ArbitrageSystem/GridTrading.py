import asyncio
import os
import datetime

import ccxt.pro as ccxtpro
import ccxt


def calc_price(base, pct_change, level):
    # 计算等差级数：固定差值 = base * pct_change
    delta = base * pct_change
    price = base + delta * level
    return round(price, 2)

async def initialize_grid(base_price, exchange, symbol, order_size=0.1, levels_num=8, effective_pct=0.1/100):
    grid_status = [{'price': base_price, 'order_id': None}]

    for i in range(1, levels_num + 1):
        price_up = calc_price(base_price, effective_pct, i)
        sell = await exchange.create_order(symbol, 'limit', 'sell', order_size, price_up)
        grid_status.append({'price': price_up, 'order_id': sell['id']})

        price_down = calc_price(base_price, -effective_pct, i)
        buy = await exchange.create_order(symbol, 'limit', 'buy', order_size, price_down)
        grid_status.append({'price': price_down, 'order_id': buy['id']})

    # 按 price 从大到小排序并返回
    return sorted(grid_status, key=lambda x: x['price'], reverse=True)
    
def display_grid_status(grid_status):
    # 清屏（Windows 用 cls，Linux/macOS 用 clear）
    os.system('cls' if os.name == 'nt' else 'clear')
    # 打印当前时间
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"===== Grid Status @ {now} =====")
    print(f"{'Idx':>3} | {'Price':>10} | {'Order ID':>20}")
    print("-" * 40)
    for idx, cell in enumerate(grid_status):
        oid = cell['order_id'] or '─'
        print(f"{idx:>3} | {cell['price']:>10.2f} | {oid:>20}")
    print("\n")  # 留一行空白


async def run_grid(symbol, grid_ratio, order_size):
    exchange = ccxtpro.binance({
        'apiKey': 'cc0ca83dfe29326a123d6f6603f16261144a86c53ffac0212c8afe96400139e3',
        'secret': 'f8c2ae97a77fd609b28792064685b52bd197d12d293c2edadb032c5585daa749',
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',   # 默认使用永续合约
        },
    })
    exchange.set_sandbox_mode(True)
    await exchange.load_markets()

    ticker = await exchange.watch_ticker(symbol)
    grid_status = await initialize_grid(
        base_price=ticker['last'],
        exchange=exchange,
        symbol=symbol,
        order_size=order_size,
        effective_pct=grid_ratio
    )

    since = None
    display_grid_status(grid_status)

    while True:
        # 只拉取 since 之后的新订单
        orders = await exchange.watchOrders(symbol=symbol, since=since)

        # 收集所有成交格子的索引
        filled = []
        for idx, cell in enumerate(grid_status):
            oid = cell['order_id']
            if not oid:
                continue
            for o in orders:
                if o.get('id') == oid and (
                   o.get('status') == 'closed' or
                   float(o.get('filled', 0)) >= float(o.get('amount', 0))
                ):
                    filled.append((idx, o))
                    break

        if filled:
            # 按买（升序）和卖（降序）分开处理
            buy_idxs  = sorted([i for i,o in filled if o.get('side') == 'buy'])
            sell_idxs = sorted([i for i,o in filled if o.get('side') == 'sell'], reverse=True)

            # 先处理买单：向上挂卖单
            for layer in buy_idxs:
                grid_status[layer]['order_id'] = None
                if layer - 1 >= 0:
                    price_up = grid_status[layer - 1]['price']
                    sell = await exchange.create_order(symbol, 'limit', 'sell', order_size, price_up)
                    grid_status[layer - 1]['order_id'] = sell['id']

            # 再处理卖单：向下挂买单
            for layer in sell_idxs:
                grid_status[layer]['order_id'] = None
                if layer + 1 < len(grid_status):
                    price_down = grid_status[layer + 1]['price']
                    buy = await exchange.create_order(symbol, 'limit', 'buy', order_size, price_down)
                    grid_status[layer + 1]['order_id'] = buy['id']

            # ——在这里更新 since——
            # 找出这批订单里最大的 timestamp（CCXT 的订单里通常有 'timestamp' 字段，单位是毫秒）
            timestamps = [o.get('timestamp') for _,o in filled if o.get('timestamp') is not None]
            if timestamps:
                since = max(timestamps) -1 


            ticker = await exchange.watch_ticker(symbol)
            for cell in grid_status:
                if cell['order_id'] is None:
                    side = 'sell' if cell['price'] > ticker['last'] else 'buy'
                    new_o = await exchange.create_order(
                        symbol, 'limit', side, order_size, cell['price']
                    )
                    cell['order_id'] = new_o['id']
            display_grid_status(grid_status)

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 適用於 Windows
    asyncio.run(run_grid('BTC/USDT', 0.01/100, 0.01))


            
