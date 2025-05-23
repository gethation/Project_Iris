import asyncio
from datetime import datetime, date, time, timedelta
import pytz
import ccxt.pro as ccxtpro
from grid_trading import run_grid
from reduce_position import reduce_position, close_position

tz = pytz.timezone("America/New_York")

async def wait_until(dt: datetime):
    """带倒计时的等待，直到纽约时区的 dt"""
    target_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    while True:
        now = datetime.now(tz)
        delta = (dt - now).total_seconds()
        if delta <= 0:
            print()  # 撑开倒计时行
            return
        total = int(delta)
        hrs, rem = divmod(total, 3600)
        mins, secs = divmod(rem, 60)
        print(f"\rCountdown to {target_str}: {hrs:02d}:{mins:02d}:{secs:02d}", end="", flush=True)
        await asyncio.sleep(1)

async def daily_scheduler(symbol, exchange):
    while True:
        today = datetime.now(tz).date()

        # 1) 17:00 启动网格
        t1 = tz.localize(datetime.combine(today, time(17, 0)))
        print(f"\n→ Next run_grid at: {t1.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await wait_until(t1)
        grid_task = asyncio.create_task(run_grid(
            symbol=symbol,
            exchange=exchange,
            grid_ratio=0.1/100,
            order_size=0.05
        ))
        print("→ run_grid started")

        # 2) 18:00 停止网格 + 启动减仓
        t2 = tz.localize(datetime.combine(today, time(18, 0)))
        print(f"\n→ Next reduce_position at: {t2.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await wait_until(t2)
        grid_task.cancel()
        print("\n← run_grid stopped")
        red_task = asyncio.create_task(reduce_position(symbol=symbol, exchange=exchange))
        print("→ reduce_position started")

        # 3) 18:03 停止减仓
        t3 = tz.localize(datetime.combine(today, time(18, 3)))
        print(f"\n→ Next stop reduce_position at: {t3.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await wait_until(t3)
        red_task.cancel()
        print("\n← reduce_position stopped")

        # 4) 立即执行 close_position
        print("Executing close_position …")
        await close_position(symbol=symbol, exchange=exchange)
        print("→ close_position executed")

        # 5) 等到第二天的 00:00，再循环
        tomorrow = today + timedelta(days=1)
        t_midnight = tz.localize(datetime.combine(tomorrow, time(0, 0)))
        print(f"\n→ Next loop at midnight: {t_midnight.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await wait_until(t_midnight)

async def main():

    symbol = 'PAXG/USDT'
    exchange = ccxtpro.binanceusdm({
        'apiKey': '90tbMeBE1FQQBsmwSPHTSbFdA8LRdsL27oRE0rnaEznc0a3KVnI26S1tV6RDpwve',
        'secret': '34OilaBhzySnhCoIY2gFmvuFzX8U5ZSnllxtOm9NfvTQXxCeheHIcnkyKJ4tvrd3',
        'adjustForTimeDifference': True,
    })
    await exchange.load_markets()
    print('exchage has already set up')
    await exchange.setLeverage(10, symbol)
    await daily_scheduler(symbol, exchange)

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
