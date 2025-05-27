import asyncio
import os
import datetime
import time

import ccxt.pro as ccxtpro
import ccxt


def calc_price(base, pct_change, level):
    # 计算等差级数：固定差值 = base * pct_change
    delta = round(base * pct_change, 2)
    price = base + delta * level
    return price

async def initialize_grid(base_price, exchange, symbol, order_size=0.1, levels_num=2, effective_pct=0.1/100):
    grid_status = [{'price': base_price, 'order': None}]

    for i in range(1, levels_num + 1):
        price_up = calc_price(base_price, effective_pct, i)
        sell = await exchange.create_order(symbol, 'limit', 'sell', order_size, price_up)
        grid_status.append({'price': price_up, 'order': sell})

        price_down = calc_price(base_price, -effective_pct, i)
        buy = await exchange.create_order(symbol, 'limit', 'buy', order_size, price_down)
        grid_status.append({'price': price_down, 'order': buy})

    # 按 price 从大到小排序并返回
    return sorted(grid_status, key=lambda x: x['price'], reverse=True), round(base_price * effective_pct, 2)

def display_grid_status(grid_status):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  当前网格状态：")
    print(f"{'Price':>10} | {'Side':^6} | {'Status':^8} | {'Order ID'}")
    print('-' * 50)
    for cell in grid_status:
        price = cell['price']
        order = cell['order']
        if order:
            side   = order.get('side')   or '—'
            status = order.get('status') or '—'
            oid    = order.get('id')     or '—'
        else:
            side, status, oid = '—', '—', '—'
        print(f"{price:>10.2f} | {side:^6} | {status:^8} | {oid}")
    print('-' * 50)


async def fetch_all_orders(exchange, symbol):
    try:
        # 并行获取三种状态的订单
        open_orders_task     = asyncio.create_task(exchange.fetchOpenOrders(symbol))
        closed_orders_task   = asyncio.create_task(exchange.fetchClosedOrders(symbol))
        canceled_orders_task = asyncio.create_task(exchange.fetchCanceledOrders(symbol))

        open_orders, closed_orders, canceled_orders = await asyncio.gather(
            open_orders_task,
            closed_orders_task,
            canceled_orders_task,
        )
    except Exception as e:
        print(f"[fetch_all_orders] 获取订单失败: {e}")
        return []  # 返回空列表，主循环不会出错

    for o in open_orders:     o['__source'] = 'open'
    for o in closed_orders:   o['__source'] = 'closed'
    for o in canceled_orders: o['__source'] = 'canceled'

    return open_orders + closed_orders + canceled_orders


async def run_grid(symbol, base_price, exchange, grid_ratio, order_size, levels_num):
    if base_price is None:
        ticker = await exchange.fetchTicker(symbol)
        base_price = ticker['last']

    grid_status, delta = await initialize_grid(
        base_price=base_price,
        exchange=exchange,
        symbol=symbol,
        order_size=order_size,
        effective_pct=grid_ratio,
        levels_num=levels_num
    )

    display_grid_status(grid_status)

    while True:
        try:
            # 1) 拉取訂單狀態
            order_list = await fetch_all_orders(exchange, symbol)

            # 2) 獲取最新報價
            ticker = await exchange.fetchTicker(symbol)
            last_price = ticker['last']

            update = False
            for cell in grid_status:
                if not cell['order']:
                    continue        
                oid = cell['order']['id']
                match = next((o for o in order_list if o['id'] == oid), None)
                if match and match['__source'] in ('closed', 'canceled'):
                    cell['order'] = None
                    update = True
                elif match:
                    cell['order'] = match

            # 3) 如果有成交
            if update:
                empty = [c for c in grid_status if c['order'] is None]
                center_price = min(empty, key=lambda c: abs(c['price'] - last_price))['price']
                center_idx = next(i for i, c in enumerate(grid_status) if c['price'] == center_price)
                
                mid_layer = levels_num

                # > 0往下補買單
                # < 0往上補賣單
                for _ in range(abs(center_idx-mid_layer)):
                    if center_idx - mid_layer > 0:
                        price_down = grid_status[-1]['price'] - delta
                        old_cell = grid_status.pop(0)
                        # 如果有下單就先取消
                        if old_cell.get('order'):
                            try:
                                await exchange.cancel_order(old_cell['order']['id'], symbol)
                            except Exception as e:
                                print(f"[run_grid] cancel_order failed for {old_cell['order']['id']}: {e}")
                        # 再在尾端 append 新的空格子
                        grid_status.append({'price': price_down, 'order': None})
                    
                    elif center_idx - mid_layer < 0:
                        price_up = grid_status[0]['price'] + delta
                        # 先把最下面那個 cell pop 出來
                        old_cell = grid_status.pop(-1)
                        if old_cell.get('order'):
                            try:
                                await exchange.cancel_order(old_cell['order']['id'], symbol)
                            except Exception as e:
                                print(f"[run_grid] cancel_order failed for {old_cell['order']['id']}: {e}")
                        # 再在最前面 insert 新的空格子
                        grid_status.insert(0, {'price': price_up, 'order': None})



                for layer, cell in enumerate(grid_status):
                    if cell['order'] is None and layer !=  mid_layer:
                        side = 'sell' if cell['price'] > grid_status[mid_layer]['price'] else 'buy'
                        try:
                            cell['order'] = await exchange.create_order(
                                symbol, 'limit', side, order_size, cell['price']
                            )
                        except Exception as e:
                            print(f"[run_grid] place order fail (price={cell['price']}, side={side}): {e}")
                display_grid_status(grid_status)

        except Exception as e:
            print(f"[run_grid main loop] 遇到异常: {e}")

        await asyncio.sleep(0.05)

async def main():
    # symbol = 'BTC/USDT:USDT'
    # exchange = ccxtpro.bybit({
    #     'apiKey': 'WvQdYKShPIMXVGDPvn',            
    #     'secret': 'Y3Nx62HzOgzmA02RicNimnWeJNh3gH5hZkkJ',
    #     'enableRateLimit': True,
    #     'options': {
    #         'defaultType': 'future',
    #     },
    # })
    # await exchange.load_markets()
    symbol = 'BTC/USDT'  # 永續合約在 unified market 裡也是這個符號
    exchange = ccxtpro.binance({  # 或者 ccxtpro.binanceusdm
        'apiKey': 'cc0ca83dfe29326a123d6f6603f16261144a86c53ffac0212c8afe96400139e3',
        'secret': 'f8c2ae97a77fd609b28792064685b52bd197d12d293c2edadb032c5585daa749',
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',   # 切到 USDⓈ-M 永續合約
        },
    })
    # 切換到沙盒測試網（自動使用 testnet URL）
    exchange.set_sandbox_mode(True)  # :contentReference[oaicite:2]{index=2}
    try:
        await exchange.set_leverage(20, symbol)
    except:
        print('same leverage')
    print('Exchange initialized')

    try:
        # 运行网格，直到抛出异常或被取消
        await run_grid(
            symbol=symbol,
            exchange=exchange,
            grid_ratio=0.05/100,
            order_size=0.001,
            levels_num=2,
            base_price=None
        )
    finally:
        # 不管是正常退出还是异常/中断，都确保调用 close()
        await exchange.close()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 適用於 Windows
    asyncio.run(main())