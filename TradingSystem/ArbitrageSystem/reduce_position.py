import ccxt.pro as ccxtpro
import ccxt

async def reduce_position(exchange, symbol):
    # 1. 取得倉位
    balance = await exchange.fetch_balance()
    positions = balance['info']['positions']
    pos_info = next((p for p in positions if p['symbol'] == symbol.replace('/', '')), None)
    if not pos_info:
        print('找不到持倉資訊')
        return

    amt = float(pos_info['positionAmt'])
    if amt == 0:
        print('當前無未平倉位，無需取消反邊訂單')
        return

    # 2. 決定要取消的方向
    cancel_side = 'buy' if amt > 0 else 'sell'
    print(f"檢測到持倉方向：{'多單' if amt > 0 else '空單'}，將取消所有 {cancel_side} 單")

    # 3. 拉取並過濾訂單
    all_orders = await exchange.fetch_orders(symbol)
    to_cancel = [o for o in all_orders if o['status'] == 'open' and o['side'] == cancel_side]
    print(f"共找到 {len(to_cancel)} 筆 open 的 {cancel_side} 單，開始取消...")

    # 4. 逐筆取消
    for order in to_cancel:
        try:
            res = await exchange.cancel_order(order['id'], order['symbol'])
            print(f"已取消訂單 {order['id']} ({order['side']} @ {order.get('price')})")
        except Exception as e:
            print(f"取消訂單 {order['id']} 時發生錯誤：{e}")

async def close_position(exchange, symbol):
    """
    1. 取消所有 open 掛單
    2. 根据當前持倉量，以市價單清倉
    """
    # 1. 取消所有 open 掛單
    all_orders = await exchange.fetch_orders(symbol)
    open_orders = [o for o in all_orders if o['status'] == 'open']
    if open_orders:
        print(f"Found {len(open_orders)} open orders, start cancelling...")
        for o in open_orders:
            try:
                await exchange.cancel_order(o['id'], o['symbol'])
                print(f"Cancelled order {o['id']} ({o['side']} @ {o.get('price', 'market')})")
            except Exception as e:
                print(f"Error cancelling {o['id']}: {e}")
    else:
        print("No open orders to cancel.")

    # 2. 获取持仓量
    balance = await exchange.fetch_balance()
    positions = balance['info']['positions']
    pos = next((p for p in positions if p['symbol'] == symbol.replace('/', '')), None)
    if not pos:
        print("No position info found.")
        return

    amt = float(pos['positionAmt'])
    if amt == 0:
        print("No open position to close.")
        return

    # 3. 根据持仓方向发市价单平仓
    side = 'sell' if amt > 0 else 'buy'
    amount = abs(amt)
    print(f"Closing position: side={side}, amount={amount} (market)")

    try:
        order = await exchange.create_order(symbol, 'market', side, amount)
        print(f"Close order placed: {order['id']} ({order['side']} {order['amount']})")
    except Exception as e:
        print(f"Error placing market close order: {e}")

