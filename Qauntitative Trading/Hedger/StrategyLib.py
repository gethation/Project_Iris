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

class PercentageGridStrategy(Basic_Function):
    params = (
        ('price_pct', 0.025),      # 网格间距百分比（1%）
        ('base_pct', 0.01),         # 基础交易量
        ('grid_levels', 50),        # 单边网格层数
        ('max_position', 100),    # 最大持仓绝对值
        ('price_precision', 2),# 价格精度
        ('sma_period', 20)
    ) 

    def __init__(self):
        # 数据引用
        super().__init__()
        
        # 策略状态
        self.grid_initialized = False
        self.grids_status = {'grid' : [],'current_layer':self.p.grid_levels}

        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period)

        with open(r"DataBase\trading_period.pkl", "rb") as file:
            self.trading_period = pickle.load(file)
        with open(r"DataBase\macd_record.pkl", "rb") as file:
            self.macd_record = pickle.load(file)

        self.current_hedgePosition = 0
        
    def initialize_grid(self):
        """Init the grid"""

        self.base_price = round(self.sma[0], self.p.price_precision)
        self.base_quantity = (self.broker.getvalue() * self.p.base_pct) // self.sma[0]

        print(f'\n=== LAYOUT ===')
        print(f'baseline: {self.base_price:.2f}',f'basequantity{self.base_quantity}')
        
        # 计算动态间距
        effective_pct = self.p.price_pct

        # 生成网格价格

        grid_price = [self.base_price]
        for i in range(1, self.p.grid_levels + 1):
            grid_price.append(self.calc_price(self.base_price, -effective_pct, i))
            grid_price.append(self.calc_price(self.base_price, effective_pct, i))
        
        self.grids_status['grid'] = sorted(grid_price)

        for i in range(0, len(self.grids_status['grid'])-2):
            if self.data.close[0] >= self.grids_status['grid'][i] and self.data.close[0] < self.grids_status['grid'][i+1]:
                self.grids_status['current_layer'] = i
                break

    def calc_price(self, base, pct_change, level):
        # 计算等差级数：固定差值 = base * pct_change
        delta = base * pct_change
        price = base + delta * level
        return round(price, self.p.price_precision)

    def print_grid_layout(self):
        """打印网格布局"""
        print("\GRID：", self.grids_status['current_layer'])
        for i, price in enumerate(self.grids_status['grid']):
            print(f'layer:{i:2d}-{price:.2f}')

    def is_trading(self, current_date, events) -> bool:
        sorted_dates = sorted(events.keys())
        last_event_date = None

        # 找出在 current_date 之前（或等於 current_date）的最後一個事件
        for date in sorted_dates:
            if date <= current_date:
                last_event_date = date
            else:
                break

        # 如果沒有事件，則無法判斷，回傳 False
        if last_event_date is None:
            return False

        last_event = events[last_event_date]

        # 如果最後一個事件是 breakout，則不在 track 區間
        if last_event['type'] == 'breakout':
            return False

        # 找出 last_event_date 之後的下一個 breakout 事件
        next_breakout_date = None
        for date in sorted_dates:
            if date > last_event_date and events[date]['type'] == 'breakout':
                next_breakout_date = date
                break

        # 若找不到下一個 breakout 事件，則可視為 track 持續中
        if next_breakout_date is None:
            return True

        # 若 current_date 在 track 事件與下一個 breakout 事件之間，則回傳 True
        return current_date < next_breakout_date
    
    def get_track_prices(self, input_date, events):
        """
        傳入一個日期，返回所有在該日期之前且位於最近一次 breakout 訊號之後的
        track（upperTrack 或 lowerTrack）事件的資料（包含 type 與 price），
        並依日期從最新到最舊排序。如果找不到符合條件的事件，返回空列表。
        """
        # 將事件日期排序
        sorted_dates = sorted(events.keys())
        
        # 找出在 input_date 之前的最後一筆 breakout 事件（如果有的話）
        last_breakout_date = None
        for d in sorted_dates:
            if d < input_date and events[d]['type'] == 'breakout':
                last_breakout_date = d

        # 選取所有在 input_date 之前且(如果有 breakout 則在 breakout 之後)的 track 事件
        results = []
        for d in sorted_dates:
            if d < input_date and events[d]['type'] in ['upperTrack', 'lowerTrack']:
                # 若存在 breakout 訊號，則必須大於該 breakout 日期；否則全部皆算
                if last_breakout_date is None or d > last_breakout_date:
                    results.append((d, events[d]))
                    
        # 依照日期從最新到最舊排序（降冪排序）
        results.sort(key=lambda x: x[0], reverse=True)
        # 只返回事件資料，不包含日期
        return [event for _, event in results]

    def next(self):
        if self.is_trading(self.datas[0].datetime.datetime(0).date(), self.trading_period):
            if not self.grid_initialized:
                self.initialize_grid()
                self.print_grid_layout()
                self.grid_initialized = True
                return
            
            current_price = self.data.close[0]
            self.check_grid_triggers(current_price)


            # current_date = self.datas[0].datetime.datetime(0).date()
            # previous_date = self.datas[0].datetime.datetime(-1).date()
            # if current_date != previous_date:
            #     self.Hedger(current_date, current_price)

        elif self.position.size != 0:
            self.close()
            self.grid_initialized = False

        self.record()

    def check_grid_triggers(self, current_price):

        current_layer = self.grids_status['current_layer']
        grid = self.grids_status['grid']
        upper_layer_price = grid[current_layer + 1]
        lower_layer_price = grid[current_layer - 1]

        if current_price >= upper_layer_price:
            self.sell(size=self.base_quantity,
                    exectype=bt.Order.Limit,
                    price=upper_layer_price)
            
            self.grids_status['current_layer'] += 1

        if current_price <= lower_layer_price:
            self.buy(size=self.base_quantity,
                    exectype=bt.Order.Limit,
                    price=lower_layer_price)
            
            self.grids_status['current_layer'] -= 1
    
    def Hedger(self, current_date, current_price):
        if current_date in self.macd_record:
            signal = self.macd_record[current_date]
        else:
            signal = None

        
        result = self.get_track_prices(current_date, self.trading_period)
        upperTrack = None
        lowerTrack = None
        for track in result:
            if track['type'] == 'upperTrack':
                upperTrack = track['price']
            elif track['type'] == 'lowerTrack':
                lowerTrack = track['price']

        
        if signal == 'buy':
            if upperTrack != None:
                risk_exposure = upperTrack - current_price
                spread = self.base_price*self.p.price_pct
                quantity = ((current_price + risk_exposure/2) * risk_exposure/spread)*self.base_quantity*0.3 / current_price
            else:
                quantity = (self.position.size*self.position.price) / current_price
            print("hedgeBuy", quantity, current_price)
            self.close()
            self.buy(size=quantity)

        elif signal == 'sell':
            if lowerTrack != None:
                risk_exposure = current_price - lowerTrack
                spread = self.base_price*self.p.price_pct
                quantity = ((current_price - risk_exposure/2) * risk_exposure/spread)*self.base_quantity*0.3 / current_price
            else:
                quantity = (self.position.size*self.position.price) / current_price
                
            print("hedgeSell",quantity, current_price)
            self.close()
            self.sell(size=quantity)

class Hedger(Basic_Function):
    params = (
        ('macd_fast', 6),    # 快速 EMA 參數
        ('macd_slow', 13),    # 慢速 EMA 參數
        ('macd_signal', 5),   # 信號線 EMA 參數
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

class Locater(bt.Strategy):

    def __init__(self):
        super().__init__()
        self.tracks = {'lowerTrack':-1 , 'upperTrack':-1}
        self.grid_switch = False
        self.week_counter = 2
        self.weekly_data = self.datas[1]
        self.days_data = self.datas[0]
        self.trading_period = {}
        self.switch_recorder = False

    def TrackAnnunciator(self, weekly_data):
        low = weekly_data.low

        if min(low[0], low[-1], low[-2]) == low[-1] and self.tracks['lowerTrack'] == -1:
            self.tracks['lowerTrack'] = weekly_data.low[-1]


            self.trading_period[self.datas[0].datetime.datetime(0).date() + timedelta(days=1)] = {"type":'lowerTrack', "price":self.tracks['lowerTrack']}
            print(f"date:{self.datas[0].datetime.datetime(0)} lower:{self.tracks['lowerTrack']:5.2f} upper:{self.tracks['upperTrack']:5.2f}")

        high = weekly_data.high

        if max(high[0],high[-1],high[-2])==high[-1] and self.tracks['upperTrack'] == -1:
            self.tracks['upperTrack'] = weekly_data.high[-1]

            self.trading_period[self.datas[0].datetime.datetime(0).date() + timedelta(days=1)] = {"type":'upperTrack', "price":self.tracks['upperTrack']}
            print(f"date:{self.datas[0].datetime.datetime(0)} lower:{self.tracks['lowerTrack']:5.2f} upper:{self.tracks['upperTrack']:5.2f}")

    def BreakoutDetector(self, weekly_data, days_data):

        if days_data.close[0] > self.tracks['upperTrack'] and self.tracks['upperTrack']!=-1:
            print(f"breakout:{self.datas[0].datetime.datetime(0)} upper:{self.tracks['upperTrack']:5.2f}")
            self.trading_period[self.datas[0].datetime.datetime(0).date()] = {"type":'breakout', "price":self.tracks['upperTrack']}


            self.grid_switch = False
            self.tracks['lowerTrack'] = -1
            self.tracks['upperTrack'] = -1
        elif days_data.close[0] < self.tracks['lowerTrack'] and self.tracks['lowerTrack']!=-1:
            print(f"breakout:{self.datas[0].datetime.datetime(0)} lower:{self.tracks['lowerTrack']:5.2f}")
            self.trading_period[self.datas[0].datetime.datetime(0).date()] = {"type":'breakout', "price":self.tracks['lowerTrack']}


            self.grid_switch = False
            self.tracks['lowerTrack'] = -1
            self.tracks['upperTrack'] = -1

    def next(self):
        if len(self.weekly_data) >= 3 and len(self.weekly_data) > self.week_counter:
            self.TrackAnnunciator(self.weekly_data)
            if self.tracks['lowerTrack'] != -1 or self.tracks['upperTrack'] != -1:
                self.grid_switch = True
            
            # if self.grid_switch:
            self.week_counter = len(self.weekly_data)

        self.BreakoutDetector(self.weekly_data, self.days_data)

