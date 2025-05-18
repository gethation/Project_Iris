import backtrader as bt
import math
import pickle
from datetime import timedelta
from datetime import datetime
import json
import pandas as pd

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

class SupportAndResistance(Basic_Function):
    params = (
        ("base_percentage", 10/100),   # 基础手数
    )
    def __init__(self):
        super().__init__()

        self.level_file = r'C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\S&R_Trding\levels.json'
        with open(self.level_file, 'r') as f:
            self.levels = json.load(f)
    
    def init_SupRes(self):
        for interval in self.levels:
            if (datetime.fromisoformat(interval['start']) <= self.datas[0].datetime.datetime(0) < datetime.fromisoformat(interval['end'])):

                self.SupRes_Areas = interval['area']
                break
        
        upper_expandArea = [[self.SupRes_Areas[0][0] * (1 + 0.8/100*(i+1)+ 0.2), 
                             self.SupRes_Areas[0][0] * (1 + 0.8/100*(i+1))] for i in range(2)]
        

        lower_expandArea = [[self.SupRes_Areas[-1][1] * (1- 0.8/100*(i+1)), 
                             self.SupRes_Areas[-1][1] * (1- 0.8/100*(i+1) - 0.2)] for i in range(2)]
        
        self.SupRes_Areas = upper_expandArea + self.SupRes_Areas + lower_expandArea
            

    def lock_levels(self):
        self.sup_low = None
        self.mid = None
        self.base_size = None

        for i in range(len(self.SupRes_Areas)-1):
            if self.SupRes_Areas[i][1] >= self.data.close[0] and self.data.close[0] >= self.SupRes_Areas[i+1][0]:
                self.sup_low, self.sup_high = self.SupRes_Areas[i+1][1], self.SupRes_Areas[i+1][0]
                self.res_low, self.res_high = self.SupRes_Areas[i][1], self.SupRes_Areas[i][0]
                break

        if self.sup_low != None:
            # 中线
            self.mid = (self.sup_high + self.res_low) // 2
            self.base_size = math.floor(self.broker.getcash() * self.params.base_percentage / self.data.close[0])
    
    def decision_making(self):

        if self.sup_low == None:
            return
        
        ClosePrice = self.data.close[0]
        OpenPrice = self.data.open[0]
        stage = abs(self.position.size)

        if OpenPrice < self.sup_high and ClosePrice > self.sup_high:
            if stage == 0:
                self.buy_bracket(
                    size=self.base_size,
                    price=ClosePrice,       # 触价进场
                    limitprice=self.mid,       # 止盈
                    stopprice=self.sup_low     # 止损
                )
                self.buy_bracket(
                    size=self.base_size,
                    price=ClosePrice,
                    limitprice=self.res_low,
                    stopprice=self.sup_low
                )
            elif stage == self.base_size:
                self.buy_bracket(
                    size=self.base_size,
                    price=ClosePrice,       # 触价进场
                    limitprice=self.mid,       # 止盈
                    stopprice=self.sup_low     # 止损
                )

        if OpenPrice > self.res_low and ClosePrice < self.res_low:
            if stage == 0:
                self.sell_bracket(
                    size=self.base_size,
                    price=ClosePrice,       # 觸價進場
                    limitprice=self.mid,
                    stopprice=self.res_high
                )
                self.sell_bracket(
                    size=self.base_size,
                    price=ClosePrice,
                    limitprice=self.sup_high,
                    stopprice=self.res_high
                )
            elif stage == self.base_size:
                self.sell_bracket(
                    size=self.base_size,
                    price=ClosePrice,       # 觸價進場
                    limitprice=self.mid,
                    stopprice=self.res_high
                )

        
    def next(self):
        self.init_SupRes()
        self.lock_levels()
        # 呼叫自定義的交易邏輯
        self.decision_making()