import asyncio
import os
import datetime
import time

import ccxt.pro as ccxtpro
import ccxt


def calc_price(base, pct_change, level):
    # 计算等差级数：固定差值 = base * pct_change
    delta = base * pct_change
    price = base + delta * level
    return round(price, 2)

async def initialize_grid(base_price, exchange, symbol, order_size=0.1, levels_num=8, effective_pct=0.1/100):
    grid_status = [{'price': base_price, 'order': None}]

    for i in range(1, levels_num + 1):
        price_up = calc_price(base_price, effective_pct, i)
        sell = await exchange.create_order(symbol, 'limit', 'sell', order_size, price_up)
        grid_status.append({'price': price_up, 'order': sell})

        price_down = calc_price(base_price, -effective_pct, i)
        buy = await exchange.create_order(symbol, 'limit', 'buy', order_size, price_down)
        grid_status.append({'price': price_down, 'order': buy})

    # 按 price 从大到小排序并返回
    return sorted(grid_status, key=lambda x: x['price'], reverse=True), base_price

def display_grid_status(grid_status):
    """
    清屏并打印当前网格每一层的关键信息：
      - 挂单价 price
      - 方向 side
      - 状态 status
      - 订单 ID
    """
    # Windows 用 cls，Linux/Mac 用 clear
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  当前网格状态：")
    print(f"{'Price':>10} | {'Side':^6} | {'Status':^8} | {'Order ID'}")
    print('-' * 50)
    for cell in grid_status:
        price = cell['price']
        order = cell['order']
        if order:
            side   = order.get('side', '—')
            status = order.get('status', '—')
            oid    = order.get('id',   '—')
        else:
            side, status, oid = ('—', 'None', '—')
        print(f"{price:>10.2f} | {side:^6} | {status:^8} | {oid}")
    print('-' * 50)

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
    grid_status, base_price = await initialize_grid(
        base_price=ticker['last'],
        exchange=exchange,
        symbol=symbol,
        order_size=order_size,
        effective_pct=grid_ratio
    )

    display_grid_status(grid_status)

    while True:
        order_list = await exchange.fetchOrders(symbol=symbol, limit=100)
        ticker = await exchange.fetchTicker(symbol)
        closed_flag = False

        # 更新已成交或部分成交的订单状态
        for cell in grid_status:
            if cell['order'] is None:
                continue  # 安全跳过空单 :contentReference[oaicite:7]{index=7}
            for order in order_list:
                if cell['order'].get('id') == order.get('id'):
                    status = order.get('status')
                    if status == 'closed':  # 使用 'closed' 判断 :contentReference[oaicite:8]{index=8}
                        cell['order'] = None
                        closed_flag = True
                    else:
                        cell['order'] = order
                    break

        # 若有订单成交，重算中心价并补单
        if closed_flag:
            min_spread = float('inf')  # 无穷大初值 :contentReference[oaicite:9]{index=9}
            center_price = base_price  # 默认中心价，防止未定义 :contentReference[oaicite:10]{index=10}
            # 找到最接近当前价的空格子作为新中心
            for cell in grid_status:
                if cell['order'] is not None:
                    continue
                spread = abs(cell['price'] - ticker['last'])
                if spread < min_spread:
                    min_spread = spread
                    center_price = cell['price']
            # 针对所有空格子重新挂单
            for cell in grid_status:
                if cell['order'] is None and cell['price'] != center_price:

                    side = 'sell' if cell['price'] > center_price else 'buy'
                    cell['order'] = await exchange.create_order(
                        symbol, 'limit', side, order_size, cell['price']
                    )
        
            display_grid_status(grid_status)
        await asyncio.sleep(0.5)
                

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 適用於 Windows
    asyncio.run(run_grid('BTC/USDT', 0.05/100, 0.001))


            
