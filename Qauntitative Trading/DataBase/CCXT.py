import math
import ccxt
from tqdm import tqdm
import pandas as pd

# 初始化交易所
exchange = ccxt.binance()

# 參數設定
symbol    = 'BTC/USDT'
timeframe = '5m'
since     = exchange.parse8601('2020-01-01T00:00:00Z')
limit     = 1000

# 計算每根 K 線對應的毫秒數
ms_per_candle = exchange.parse_timeframe(timeframe) * 1000

# 預估要跑幾輪
now           = exchange.milliseconds()
total_candles = (now - since) // ms_per_candle + 1
total_iters   = math.ceil(total_candles / limit)

# 建立進度條
pbar = tqdm(total=total_iters, desc=f'Fetching {symbol} {timeframe}')

all_ohlcv = []
while True:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    if not ohlcv:
        break
    all_ohlcv.extend(ohlcv)
    since = ohlcv[-1][0]        # 更新起點
    pbar.update(1)              # 更新進度
    if len(ohlcv) < limit:
        break

pbar.close()

# 轉成 DataFrame
df = pd.DataFrame(all_ohlcv, columns=['timestamp','open','high','low','close','volume'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('datetime', inplace=True)

# 存成 CSV
output_path = fr"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\BTC_{timeframe}.csv"
df.to_csv(output_path, index=True)
print(f'已將 {symbol} {timeframe} 歷史數據儲存到：{output_path}')