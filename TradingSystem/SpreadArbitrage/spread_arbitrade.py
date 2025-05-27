import asyncio
import ccxt.pro as ccxtpro
import ccxt

async def spread_arbitrader(symbol0, symbol1, exchange, threshold=0.4, base_size=1.0):
    pyramid_count = 0
    side = 0         # +1 多价差，-1 空价差
    last_spread = None

    # 建立 WebSocket 订阅
    ws0 = exchange.watchTicker(symbol0)
    ws1 = exchange.watchTicker(symbol1)

    while True:
        try:
            # 并行获取最新价
            ticker0, ticker1 = await asyncio.gather(ws0, ws1)
            px0 = float(ticker0['close'])
            px1 = float(ticker1['close'])
            spread = (px0 - px1) * 2.0 / (px0 + px1)

            now = exchange.milliseconds()
            dt = exchange.iso8601(now)

            # 1) 跨零点平仓
            if side != 0 and last_spread is not None and last_spread * spread < 0:
                print(f'[{dt}] cross zero: {last_spread:.4f} → {spread:.4f}, closing all')
                # 平 XAUT
                try:
                    await exchange.createOrder(symbol0, 'market', 'buy' if side < 0 else 'sell', base_size * pyramid_count)
                except Exception as e:
                    print(f'[{dt}] Error closing {symbol0}: {type(e).__name__} {e}')
                # 平 PAXG
                try:
                    await exchange.createOrder(symbol1, 'market', 'sell' if side < 0 else 'buy', base_size * pyramid_count)
                except Exception as e:
                    print(f'[{dt}] Error closing {symbol1}: {type(e).__name__} {e}')
                pyramid_count = 0
                side = 0

            # 2) 首次进场
            elif side == 0:
                if spread > threshold:
                    side = -1
                elif spread < -threshold:
                    side = +1
                if side != 0:
                    pyramid_count = 1
                    action0 = 'sell' if side < 0 else 'buy'
                    action1 = 'buy' if side < 0 else 'sell'
                    print(f'[{dt}] enter {"SHORT" if side<0 else "LONG"} spread: {spread:.4f}')
                    try:
                        await exchange.createOrder(symbol0, 'market', action0, base_size)
                        await exchange.createOrder(symbol1, 'market', action1, base_size)
                    except Exception as e:
                        print(f'[{dt}] Error entering position: {type(e).__name__} {e}')
                        # 如果首次进场失败，重置状态
                        side = 0
                        pyramid_count = 0

            # 3) 金字塔加码
            else:
                next_level = threshold * (pyramid_count + 1)
                # 加码空价差
                if side < 0 and spread > next_level:
                    pyramid_count += 1
                    print(f'[{dt}] pyramid ADD SHORT #{pyramid_count}: spread={spread:.4f}')
                    try:
                        await exchange.createOrder(symbol0, 'market', 'sell', base_size)
                        await exchange.createOrder(symbol1, 'market', 'buy', base_size)
                    except Exception as e:
                        print(f'[{dt}] Error pyramid add short: {type(e).__name__} {e}')
                        pyramid_count -= 1
                # 加码多价差
                elif side > 0 and spread < -next_level:
                    pyramid_count += 1
                    print(f'[{dt}] pyramid ADD LONG #{pyramid_count}: spread={spread:.4f}')
                    try:
                        await exchange.createOrder(symbol0, 'market', 'buy', base_size)
                        await exchange.createOrder(symbol1, 'market', 'sell', base_size)
                    except Exception as e:
                        print(f'[{dt}] Error pyramid add long: {type(e).__name__} {e}')
                        pyramid_count -= 1

            last_spread = spread

        except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
            # 网络或交易所级别错误，稍后重试
            now = exchange.iso8601(exchange.milliseconds())
            print(f'[{now}] Caught network/exchange error: {type(exc).__name__} {exc}')
            await asyncio.sleep(5)
        except Exception as exc:
            # 未知错误，不退出循环
            now = exchange.iso8601(exchange.milliseconds())
            print(f'[{now}] Unexpected error: {type(exc).__name__} {exc}')
            await asyncio.sleep(5)

        # 控制节奏，避免过度频繁下单
        await asyncio.sleep(1.0)

async def main():
    symbol0 = 'XAUT/USDT:USDT'
    symbol1 = 'PAXG/USDT:USDT'
    exchange = ccxtpro.bybit({
        'apiKey': 'WvQdYKShPIMXVGDPvn',            
        'secret': 'Y3Nx62HzOgzmA02RicNimnWeJNh3gH5hZkkJ',
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        },
    })
    await exchange.load_markets()
    print('Exchange initialized')
    
    await exchange.set_leverage(20, symbol0)
    await exchange.set_leverage(20, symbol1)

    # await spread_arbitrader(symbol0=symbol0
    #                         symbol1=symbol1, 
    #                         exchange=exchange,
    #                         threshold=0.4/100,
    #                         base_size==0.05)

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
