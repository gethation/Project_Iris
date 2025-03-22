import requests
import pandas as pd
import time
import math
from tqdm import tqdm

def interval_to_ms(interval):
    """
    將 Binance 的時間間隔轉換為毫秒
    支援的格式有: m (分鐘), h (小時), d (天)
    """
    if interval.endswith('m'):
        return int(interval[:-1]) * 60 * 1000
    elif interval.endswith('h'):
        return int(interval[:-1]) * 60 * 60 * 1000
    elif interval.endswith('d'):
        return int(interval[:-1]) * 24 * 60 * 60 * 1000
    else:
        raise ValueError("Unsupported interval format.")

def get_all_binance_klines(symbol, interval, start_time, end_time=None):
    """
    從 Binance API 取得從 start_time 到 end_time 之間的所有 K 線資料，
    並將所有批次數據拼接成一個 DataFrame。

    參數:
        symbol (str): 交易對，例如 "BTCUSDT"
        interval (str): 時間間隔，例如 "1m"
        start_time (int): 起始時間 (毫秒)
        end_time (int, optional): 結束時間 (毫秒)，若為 None 則抓取到目前為止的數據

    回傳:
        pd.DataFrame: 拼接後的所有 K 線資料
    """
    url = "https://api.binance.com/api/v3/klines"
    limit = 1000  # 單次最多取得 1000 筆資料
    all_data = []
    interval_ms = interval_to_ms(interval)
    
    # 若有結束時間，估算總批次數
    if end_time:
        total_data_points = (end_time - start_time) // interval_ms
        total_batches = math.ceil(total_data_points / limit)
        pbar = tqdm(total=total_batches, desc="Fetching Binance Klines")
    else:
        pbar = tqdm(desc="Fetching Binance Klines")
    
    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }
        if end_time:
            params["endTime"] = end_time
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data:
            break
        
        all_data.extend(data)
        pbar.update(1)
        
        # 當資料筆數小於 limit 時，代表已經抓取完畢
        if len(data) < limit:
            break
        
        # 更新下一次請求的起始時間：以最後一筆的 open_time 為基準，加 1 毫秒以避免重複
        last_time = data[-1][0]
        start_time = last_time + 1
        
        # 為避免 API 過於頻繁，稍作延遲
        time.sleep(0.5)
    
    pbar.close()
    
    # 定義回傳的欄位名稱（依據 Binance API 文件）
    columns = [
        'open_time', 'open', 'high', 'low', 'close', 'volume', 
        'close_time', 'quote_asset_volume', 'number_of_trades', 
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]
    df = pd.DataFrame(all_data, columns=columns)
    
    # 將時間戳記轉換成 datetime 格式
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    return df

# 設定起始時間，例如從 2021-01-01 開始（轉換為毫秒）
start_time = int(pd.Timestamp('2025-3-10').timestamp() * 1000)
# 如果需要限制結束時間，也可以設定，例如結束於 2021-01-02：
# end_time = int(pd.Timestamp('2021-01-02').timestamp() * 1000)
end_time = None  # 若為 None 則抓取到最新資料

# 取得所有 BTCUSDT 1 分鐘 K 線資料，並顯示進度條

df_all = get_all_binance_klines("BTCUSDT", "1m", start_time, end_time)

# 儲存拼接後的 DataFrame 成 CSV 檔案
df_all.to_csv("BTCUSDT_all_1m_data.csv", index=False, encoding="utf-8-sig")
print("所有資料已儲存至 BTCUSDT_all_1m_data.csv")
