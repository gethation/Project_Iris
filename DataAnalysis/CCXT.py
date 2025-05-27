import math
import ccxt
from tqdm import tqdm
import pandas as pd

# 初始化交易所
exchange = ccxt.binance()
# exchange = ccxt.okx({
#     'enableRateLimit': True,
# })
# import ccxt
# exchange = ccxt.mexc({
#     "enableRateLimit": True,
#     # 指定 defaultType = 'swap' → 走永續合約 (USDT-M 線性)
#     "options": {"defaultType": "swap"},
# })

# # 參數設定
# symbol    = 'XAUT/USDT:USDT'
symbol    = 'BTC/USDT'
timeframe = '1h'
since     = exchange.parse8601('2024-05-23T00:00:00Z')
limit     = 500

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
df = pd.DataFrame(all_ohlcv, columns=[
    'timestamp', 'open', 'high', 'low', 'close', 'volume'
])
# 1. 将 timestamp(毫秒) 解析为带时区的 UTC 时间
df.index = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
# 2. 转换到美东时间（考虑夏令时）
df.index = df.index.tz_convert('America/New_York')
# 3. （可选）去掉 tz 信息，变成普通的本地时间索引
df.index = df.index.tz_localize(None)
# 4. 删除冗余的 timestamp 列
df.drop(columns=['timestamp'], inplace=True)


# 存成 CSV
output_path = fr"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\{symbol.split('/')[0]}_{timeframe}.csv"
df.to_csv(output_path, index=True)
print(f'已將 {symbol} {timeframe} 歷史數據儲存到：{output_path}')