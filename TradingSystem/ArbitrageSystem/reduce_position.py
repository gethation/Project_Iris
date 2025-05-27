import ccxt.pro as ccxtpro
import ccxt
import asyncio

async def reduce_position(exchange, symbol):
    # 1. 取得倉位資訊
    balance = await exchange.fetch_balance()
    positions = balance['info']['positions']
    # Bybit 回傳的 symbol 沒有斜線，因此要去掉 '/'
    pos_info = next(
        (p for p in positions if p['symbol'] == symbol.replace('/', '')),
        None
    )
    if not pos_info:
        print('找不到持倉資訊')
        return

    amt = float(pos_info['positionAmt'])
    if amt == 0:
        print('當前無未平倉位，無需取消反邊訂單')
        return

    # 2. 決定要取消的方向（持多單則取消買單；持空單則取消賣單）
    cancel_side = 'buy' if amt > 0 else 'sell'
    direction = '多單' if amt > 0 else '空單'
    print(f"檢測到持倉方向：{direction}，將取消所有 {cancel_side} 單")

    # 3. 取得所有開啟訂單 (Bybit 支援)
    open_orders = await exchange.fetch_open_orders(symbol)
    to_cancel = [o for o in open_orders if o['side'] == cancel_side]
    print(f"共找到 {len(to_cancel)} 筆 open 的 {cancel_side} 單，開始取消...")

    # 4. 逐筆取消
    for order in to_cancel:
        try:
            res = await exchange.cancel_order(order['id'], symbol)
            price = order.get('price') or '市價'
            print(f"已取消訂單 {order['id']} ({order['side']} @ {price})")
        except Exception as e:
            print(f"取消訂單 {order['id']} 時發生錯誤：{e}")

async def fetch_open_orders(exchange, symbol):
    """
    获取指定 symbol 的所有 open 挂单
    """
    try:
        return await exchange.fetchOpenOrders(symbol)
    except NotImplementedError:
        # 部分交易所可能只支持 fetchOrders
        all_orders = await exchange.fetchOrders(symbol)
        return [o for o in all_orders if o.get('status') == 'open']

async def close_position(exchange, symbol):
    """
    1. 取消所有 open 挂单（并行执行）
    2. 根据当前持仓量，以市价单清仓
    """
    # ------------------------
    # 1) 并行取消所有 open 挂单
    # ------------------------
    open_orders = await fetch_open_orders(exchange, symbol)
    if open_orders:
        print(f"Found {len(open_orders)} open orders, cancelling…")
        # 并行发起取消请求
        cancel_tasks = []
        for o in open_orders:
            oid, osym = o['id'], o.get('symbol', symbol)
            cancel_tasks.append(
                asyncio.create_task(
                    _cancel_order(exchange, oid, osym)
                )
            )
        # 等待全部取消完成
        await asyncio.gather(*cancel_tasks)
    else:
        print("No open orders to cancel.")

    # ------------------------
    # 2) 市价清仓
    # ------------------------
    # 2.1 拉取持仓信息
    balance = await exchange.fetch_balance()
    positions = balance.get('info', {}).get('positions', [])
    # Bybit UTA 中，positionAmt 字段表示多正空负
    pos = next((p for p in positions if p['symbol'] == symbol.replace('/', '')), None)
    if not pos:
        print("No position info found.")
        return

    amt = float(pos.get('positionAmt', 0))
    if amt == 0:
        print("No open position to close.")
        return

    side = 'sell' if amt > 0 else 'buy'
    amount = abs(amt)
    print(f"Closing position with market order: side={side}, amount={amount}")

    try:
        order = await exchange.create_order(symbol, 'market', side, amount)
        print(f"Close order placed: id={order.get('id')} filled={order.get('filled', amount)}")
    except Exception as e:
        print(f"Error placing market close order: {e}")

async def _cancel_order(exchange, order_id, symbol):
    """
    单笔取消辅助，捕获并打印错误
    """
    try:
        res = await exchange.cancel_order(order_id, symbol)
        print(f"  • Cancelled {order_id}: {res.get('status', 'unknown')}")
    except Exception as e:
        print(f"  • Error cancelling {order_id}: {e}")

