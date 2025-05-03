import backtrader as bt
import math
import pickle
from datetime import timedelta

class Basic_Function(bt.Strategy):
    def __init__(self):
        self.daily_records = {'cash': [], 'value': [], 'date': []}
        self.trade_records = []

    def log(self, txt, dt=None):
        ''' 記錄日誌 '''
        print(self.datas[0].datetime.datetime(0), txt)

    def record(self):
        self.daily_records['cash'].append(self.broker.getcash())
        self.daily_records['value'].append(self.broker.getvalue())
        self.daily_records['date'].append(self.datas[0].datetime.datetime(0))       
    
    def notify_order(self, order):
        ''' 訂單通知 '''
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            trade_type = order.info.get('trade_type') if order.info else 'unknown'
            if order.isbuy():
                self.log("BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm: %.2f" %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            elif order.issell():
                self.log("SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm: %.2f" %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            # 記錄交易資料
            self.trade_records.append({
                'date': self.datas[0].datetime.datetime(0),
                'trade_type': trade_type,
                'order_side': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
            })
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
        
        # 訂單處理完成後清空訂單追蹤
        self.order = None

class Hedger(Basic_Function):
    params = (
        ('macd_fast', 13),    # 快速 EMA 參數
        ('macd_slow', 26),    # 慢速 EMA 參數
        ('macd_signal', 9),   # 信號線 EMA 參數
    )
    
    def __init__(self):
        # 計算 MACD 指標
        super().__init__()
        self.macd = bt.ind.MACD(self.data,
                                period_me1=self.params.macd_fast,
                                period_me2=self.params.macd_slow,
                                period_signal=self.params.macd_signal)
        # 定義 MACD 與信號線的交叉
        self.macd_cross = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

        self.macd_record = {}
    
    def trade_logic(self):
        # 當沒有持倉時進行開倉判斷
        if not self.position:
            # 當 MACD 線向上穿越信號線，形成黃金交叉，進場做多
            if self.macd_cross > 0:
                self.macd_record[self.datas[0].datetime.datetime(0).date() + timedelta(days=1)] = 'buy'
                self.buy()
            # 當 MACD 線向下穿越信號線，形成死亡交叉，進場做空
            elif self.macd_cross < 0:
                self.macd_record[self.datas[0].datetime.datetime(0).date() + timedelta(days=1)] = 'sell'
                self.sell()  # 建立空單
        else:
            # 若已有持多單，且出現死亡交叉則平倉
            if self.position.size > 0 and self.macd_cross < 0:
                self.macd_record[self.datas[0].datetime.datetime(0).date() + timedelta(days=1)] = 'sell'
                self.close()
                self.sell()
            # 若已有持空單，且出現黃金交叉則平倉
            elif self.position.size < 0 and self.macd_cross > 0:
                self.macd_record[self.datas[0].datetime.datetime(0).date() + timedelta(days=1)] = 'buy'
                self.close()
                self.buy()
    
    def next(self):
        # 呼叫自定義的交易邏輯
        self.trade_logic()