from binance.client import Client
from datetime import datetime
import time
import pandas as pd


client = Client("k24V8PMxxO5ltXvSzEqMZTkcfxdjmiqeO5IAyuF5lneOz9eBNFWkK5NkbpuCPprA", 
                "FOblgmjtoZrdEiKpQRYpCHJGThOWWQYoOgsyT1R7ICkLgo6MUw5a3sUx3HOkV1Rm")

SYMBOL = "BTCUSDT"  # Trading pair
INTERVAL = Client.KLINE_INTERVAL_1MINUTE  # 5-minute K-line interval
LIMIT = 2  # Fetch only the most recent bar

def Requester(client, symbol=SYMBOL, interval=INTERVAL, limit=2):
    """
    Fetch the most recent K-line for the given symbol and interval.
    Returns a dict with open_time (ms), open, high, low, close, volume, close_time (ms).
    """
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    ticker = client.get_symbol_ticker(symbol="BTCUSDT")
    k = klines[0]
    return {
        "dynamic_price": ticker['price'],
        "open_time": int(k[0]),
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
        "volume": float(k[5]),
        "close_time": int(k[6])
    }

def Fetch_Account_info(client, symbol):
    account_information = {}

    fut = client.futures_account_balance()
    usdt = next(x for x in fut if x['asset']=='USDT')
    account_information['balance'] = float(usdt['balance'])

    positions = client.futures_position_information()
    for pos in positions:
        account_information['size'] = pos['positionAmt']

    
    return account_information

if __name__ == "__main__":
    Previous_Kline = Requester(client = client)
    while True:
        Current_Kline = Requester(client=client)

        if Current_Kline['open_time'] != Previous_Kline['open_time']:
            Previous_Kline = Current_Kline
            print('update')

        dt = datetime.fromtimestamp(Current_Kline['open_time'] / 1000)
        print(dt, Current_Kline['dynamic_price'])
        time.sleep(1)