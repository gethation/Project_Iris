import asyncio
import ccxt.pro as ccxtpro
import ccxt  # 這是同步 API

async def watch_ticker(symbol):
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

    # 4. 监听指定交易对的“我的成交”流
    symbol = 'BTC/USDT'
    while True:
        try:
            trades = await exchange.watch_my_trades(symbol)  # :contentReference[oaicite:1]{index=1}
            print(exchange.iso8601(exchange.milliseconds()), 'My trades:', trades)
        except Exception as e:
            print('Error:', str(e))
            # 根据需要决定是否 break 或继续重试
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 適用於 Windows
    asyncio.run(watch_ticker("BTC/USDT"))
