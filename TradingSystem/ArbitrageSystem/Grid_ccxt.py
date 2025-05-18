import asyncio
import ccxt.pro as ccxtpro
import ccxt

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

    # 3. 加载市场 (可选，但推荐用于方便后续调用)
    await exchange.load_markets()
    grid_center = None
    buy_id = sell_id = None

    while True:
        # 2. 行情订阅，获取最新买一卖一
        ob = await exchange.watchOrderBook(symbol)
        best_bid = ob['bids'][0][0]
        best_ask = ob['asks'][0][0]
        mid_price = (best_bid + best_ask) / 2

        if grid_center is None:
            grid_center = mid_price
            print(f"初始化网格中心价格: {grid_center:.8f}")

        # 3. 若无挂单，则下买卖限价单并打印信息
        if not buy_id and not sell_id:
            price_up   = grid_center * (1 + grid_ratio)
            price_down = grid_center * (1 - grid_ratio)

            # 下卖单
            sell = await exchange.create_order(symbol, 'limit', 'sell', order_size, price_up)
            sell_id = sell['id']
            print(f"↓ 卖单已下: symbol={symbol}, price={price_up:.8f}, size={order_size}, order_id={sell_id}")

            # 下买单
            buy  = await exchange.create_order(symbol, 'limit', 'buy',  order_size, price_down)
            buy_id = buy['id']
            print(f"↑ 买单已下: symbol={symbol}, price={price_down:.8f}, size={order_size}, order_id={buy_id}")

        # 4. 监听个人成交
        orders = await exchange.watchOrders(symbol)
        for order in orders:
            oid    = order.get('id')
            status = order.get('status')
            filled = float(order.get('filled', 0))
            amount = float(order.get('amount', 0))

            # 只关心当前挂单之一，且完全成交（closed 或 filled == amount）
            if oid in (buy_id, sell_id) and (status == 'closed' or filled >= amount):
                side = 'BUY' if oid == buy_id else 'SELL'
                exec_price = float(order.get('average', order.get('price')))
                print(f"{side} 完全成交: order_id={oid}, price={exec_price:.8f}, filled={filled}")

                # 4. 撤销对边挂单
                opp_id = sell_id if oid == buy_id else buy_id
                if opp_id:
                    print(f"撤销对边订单: {opp_id}")
                    try:
                        cancel_res = await exchange.cancel_order(opp_id, symbol)
                        print("撤单返回:", opp_id)
                    except ccxt.OrderNotFound as e:
                        print(f"对边订单 {opp_id} 不存在或已被撮合: {e}")

                # 5. 更新网格中心并重置状态
                grid_center = exec_price
                buy_id = sell_id = None
                print(f"网格中心更新为: {grid_center:.8f}")
                break  # 跳出 for-loop，进入下一轮下单


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 適用於 Windows
    asyncio.run(run_grid('BTC/USDT', 0.01/100, 1))

