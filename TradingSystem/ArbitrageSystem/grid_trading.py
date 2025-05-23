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
    return round(price, )

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

async def run_grid(symbol, base_price, exchange, grid_ratio, order_size):
    # exchange = ccxtpro.binance({
    #     'apiKey': 'cc0ca83dfe29326a123d6f6603f16261144a86c53ffac0212c8afe96400139e3',
    #     'secret': 'f8c2ae97a77fd609b28792064685b52bd197d12d293c2edadb032c5585daa749',
    #     'enableRateLimit': True,
    #     'options': {
    #         'defaultType': 'future',   # 默认使用永续合约
    #     },
    # })
    # exchange.set_sandbox_mode(True)
    # await exchange.load_markets()

    if base_price is None:
        ticker = await exchange.fetchTicker(symbol)
        base_price = ticker['last']

    grid_status, base_price = await initialize_grid(
        base_price=base_price,
        exchange=exchange,
        symbol=symbol,
        order_size=order_size,
        effective_pct=grid_ratio
    )

    display_grid_status(grid_status)

    while True:
        order_list = await exchange.fetchOrders(symbol=symbol, limit=100)
        ticker = await exchange.fetchTicker(symbol)
        update = False

        for cell in grid_status:
            if cell['order'] is None:
                continue
            for order in order_list:
                if cell['order'].get('id') == order.get('id'):
                    status = order.get('status')
                    if status == 'closed':
                        cell['order'] = None
                        update = True
                    else:
                        cell['order'] = order
                    break

        if update:

            empty = [c for c in grid_status if c['order'] is None]
            center_price = min(empty, key=lambda c: abs(c['price'] - ticker['last']))['price']

            for cell in grid_status:
                if cell['order'] is None and cell['price'] != center_price:

                    side = 'sell' if cell['price'] > center_price else 'buy'
                    cell['order'] = await exchange.create_order(
                        symbol, 'limit', side, order_size, cell['price'])
        
            display_grid_status(grid_status)
                

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 適用於 Windows
    asyncio.run(run_grid('BTC/USDT', 0.1/100, 0.001))