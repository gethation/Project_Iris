import asyncio
from datetime import datetime, date, time, timedelta
import pytz
import ccxt.pro as ccxtpro
from grid_trading import run_grid
from reduce_position import reduce_position, close_position

tz = pytz.timezone("America/New_York")

async def wait_until(dt: datetime):
    """带倒计时的等待，到达纽约时区 dt 时返回"""
    while True:
        now = datetime.now(tz)
        delta = (dt - now).total_seconds()
        if delta <= 0:
            print()  # 跳一行
            return
        total = int(delta)
        hrs, rem = divmod(total, 3600)
        mins, secs = divmod(rem, 60)
        print(f"\rCountdown to {dt.strftime('%Y-%m-%d %H:%M:%S')}: {hrs:02d}:{mins:02d}:{secs:02d}", end="")
        await asyncio.sleep(1)

async def weekly_scheduler(symbol, exchange, grid_ratio, order_size, levels_num):
    while True:
        now = datetime.now(tz)

        # 1) 计算下一个周五 17:00
        days_to_friday = (4 - now.weekday()) % 7
        friday_date = now.date() + timedelta(days=days_to_friday)
        t_start = tz.localize(datetime.combine(friday_date, time(17, 0)))
        if now >= t_start:
            t_start += timedelta(days=7)

        print(f"→ Next run_grid at: {t_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await wait_until(t_start)

        # 启动网格
        grid_task = asyncio.create_task(
            run_grid(
                symbol=symbol,
                exchange=exchange,
                grid_ratio=grid_ratio,
                order_size=order_size,
                levels_num=levels_num,
                base_price=None
            )
        )
        print("→ run_grid started")

        # 2) 计算对应的周日 18:00
        sunday_date = t_start.date() + timedelta(days=2)
        t_end = tz.localize(datetime.combine(sunday_date, time(18, 0)))

        print(f"→ Next close_position at: {t_end.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await wait_until(t_end)

        # 平仓并停止网格
        print("Executing close_position …")
        await close_position(symbol=symbol, exchange=exchange)
        print("→ close_position executed")
        grid_task.cancel()
        print("← run_grid stopped\n")

async def main():
    symbol = 'XAUT/USDT:USDT'
    exchange = ccxtpro.bybit({
        'apiKey': 'WvQdYKShPIMXVGDPvn',            
        'secret': 'Y3Nx62HzOgzmA02RicNimnWeJNh3gH5hZkkJ',
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        },
    })
    await exchange.load_markets()
    try:
        await exchange.set_leverage(20, symbol)
    except:
        print('same leverage')
    print('Exchange initialized')

    try:
        # 运行网格，直到抛出异常或被取消
        await weekly_scheduler(
            symbol=symbol,
            exchange=exchange,
            grid_ratio=0.1/100,
            order_size=0.03,
            levels_num=10,
            base_price=None
        )
    finally:
        # 不管是正常退出还是异常/中断，都确保调用 close()
        await exchange.close()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
