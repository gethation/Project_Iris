from FetchKline import Requester, Fetch_Account_info
from Excutioner import Excutioner
from DecisionMaker import SupportAndResistance
from datetime import datetime
import time
import json

from binance.client import Client
client = Client("cc0ca83dfe29326a123d6f6603f16261144a86c53ffac0212c8afe96400139e3", 
                "f8c2ae97a77fd609b28792064685b52bd197d12d293c2edadb032c5585daa749", testnet=True)

client_real = Client("k24V8PMxxO5ltXvSzEqMZTkcfxdjmiqeO5IAyuF5lneOz9eBNFWkK5NkbpuCPprA", 
                "FOblgmjtoZrdEiKpQRYpCHJGThOWWQYoOgsyT1R7ICkLgo6MUw5a3sUx3HOkV1Rm")

SYMBOL = "BTCUSDT"  # Trading pair
INTERVAL = Client.KLINE_INTERVAL_5MINUTE  # 5-minute K-line interval
levels_file = r'C:\Users\Huang\Work place\Project_Iris\TradingSystem\Cache\levels.json'
order_list_file = r'C:\Users\Huang\Work place\Project_Iris\TradingSystem\Cache\OrderList.json'

if __name__ == "__main__":
    SupRes_Trader = SupportAndResistance(levels_file=levels_file,
                                         base_percentage=0.45)
    
    previous_kline = Requester(client=client_real,
                                symbol=SYMBOL,
                                interval=INTERVAL)
    with open(order_list_file, "r", encoding="utf-8") as f:
        order_list = json.load(f)

    

    while True:
        
        current_kline = Requester(client=client_real,
                                  symbol=SYMBOL,
                                  interval=INTERVAL)
        
        
        if current_kline['open_time'] != previous_kline['open_time']:

            account_information = Fetch_Account_info(client=client,
                                                     symbol=SYMBOL)
    
            order = SupRes_Trader.next(current_kline=current_kline,
                                       account_information=account_information)
            
            previous_kline = current_kline
            print(current_kline)
            print(account_information)
            print(order)

        time.sleep(0.5)
        # Excutioner(spot_price=current_kline['dynamic_price'],
        #            order_list=order_list, 
        #            new_order=order, 
        #            client=client)

        
        time.sleep(0.5)

        with open(order_list_file, "w", encoding="utf-8") as f:
            json.dump(order_list, f, indent=4, ensure_ascii=False)
