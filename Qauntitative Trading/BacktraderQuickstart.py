import datetime
import backtrader as bt

# 定義策略類別
class Strategy(bt.Strategy):

    def log(self, txt, dt=None):
        '''日誌函數，用於輸出訊息'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        self.sma_short = bt.indicators.SimpleMovingAverage(self.datas[0], period=5)
        self.sma_long = bt.indicators.SimpleMovingAverage(self.datas[0], period=20)
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.buy()
        elif self.position:
            if self.crossover < 0:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.sell()

if __name__ == '__main__':
    # 創建 Cerebro 引擎
    cerebro = bt.Cerebro()
    # 添加策略
    cerebro.addstrategy(Strategy)

    # 加載數據
    
    data = bt.feeds.GenericCSVData(
        dataname='Data_base/ALL_stock_DATE_OHLC_dict/2330.csv',          # CSV 檔案路徑
        fromdate=datetime.datetime(2023, 10, 1),
        todate=datetime.datetime(2025, 1, 1),
        dtformat=('%Y-%m-%d'),             # 日期格式
        datetime=0,                       # 日期所在欄位（索引從 0 開始）
        open=1,                           # 開盤價所在欄位
        high=2,                           # 最高價所在欄位
        low=3,                            # 最低價所在欄位
        close=4,                          # 收盤價所在欄位
        volume=5,                         # 成交量所在欄位
        openinterest=-1                   # 如果沒有持倉量欄位，設為 -1
    )

    cerebro.adddata(data)

    # 運行回測
    cerebro.run()
    cerebro.plot()
