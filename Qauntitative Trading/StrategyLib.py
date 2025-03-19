import backtrader as bt



class MACDStrategy(bt.Strategy):
    def __init__(self):
        # 添加 MACD 指標
        self.macd = bt.indicators.MACD(
            period_me1=12, period_me2=26, period_signal=9, plot=True
        )
        # 初始化訂單追蹤變數
        self.order = None
        self.daily_records = {'cash': [], 'value': [], 'date':[]}
        self.indicator = [{'MACD':[], 'Signal':[]}]
        self.trade_records = []

    def log(self, txt, dt=None):
        ''' 記錄日誌 '''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        ''' 訂單通知 '''
        # 尚未完成的訂單先略過
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            # 透過 order.info 區分是進場還是平倉
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
            # 記錄交易資料：下單日期、類型、價格、成交量、成交金額與手續費
            self.trade_records.append({
                'date': self.datas[0].datetime.date(0),
                'trade_type': trade_type,       # entry (進場) 或 exit (平倉)
                'order_side': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
            })
            # 紀錄進場時的 bar
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
        # 訂單處理完成後清空訂單追蹤
        self.order = None

    def next(self):
        # 若有掛單則暫不進行新下單
        if self.order:
            return

        cash = self.broker.getcash()
        size = int(cash / self.data.open[0] * 0.7)

        self.daily_records['cash'].append(self.broker.getcash())
        self.daily_records['value'].append(self.broker.getvalue())
        self.daily_records['date'].append(self.datas[0].datetime.date(0))
        self.indicator[0]['MACD'].append(self.macd.macd[0])
        self.indicator[0]['Signal'].append(self.macd.signal[0])


        
        # 記錄目前 MACD 與 Signal 值，方便追蹤
        self.log("MACD: %.2f, Signal: %.2f" % (self.macd.macd[0], self.macd.signal[0]))

        if not self.position:  
            if self.macd.macd[0] > self.macd.signal[0]:
                self.log("MACD 上穿信號線，發出買入指令")
                self.order = self.buy(size=size, price=self.data.open[0])

            # elif self.macd.macd[0] < self.macd.signal[0]:
            #     self.log("MACD 下穿信號線，發出賣出指令")
            #     self.order = self.sell(size=size, price=self.data.open[0])
        else:  
            if self.position.size > 0 and self.macd.macd[0] < self.macd.signal[0]:
                self.log("多單反轉，先平倉，再發出賣出指令")
                self.order = self.close()

                # self.order = self.sell(size=size, price=self.data.open[0])
            # elif self.position.size < 0 and self.macd.macd[0] > self.macd.signal[0]:
            #     self.log("空單反轉，先平倉，再發出買入指令")
            #     self.order = self.close()
            #     self.order = self.buy(size=size, price=self.data.open[0])

        


class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=5,  # period for the fast moving average
        pslow=20   # period for the slow moving average
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal

    def next(self):
        if not self.position:  # not in the market
            cash = self.broker.getcash()
            size = int(cash / self.data.open[0]*0.7)
            if self.crossover > 0:
                self.buy(size = size,
                         price = self.data.close[0])

        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position

class KDStrategy(bt.Strategy):
    params = (
        ('period', 10),            # KD 指標計算期間
        ('period_dfast', 3),       # %K 的平滑期間
        ('period_dslow', 3),       # %D 的平滑期間
        ('oversold', 50),          # 超賣區閥值
        ('overbought', 50),        # 超買區閥值
        ('order_percentage', 0.5), # 下單資金比例
        ('holding_period', 0)      # 持有固定時間（bar 數）
    )

    def __init__(self):
        # 初始化 KD 指標
        self.stoch = bt.indicators.Stochastic(
            self.data,
            period=self.p.period,
            period_dfast=self.p.period_dfast,
            period_dslow=self.p.period_dslow
        )
        # 建立 %K 與 %D 交叉的判斷（保留進場訊號用）
        self.crossover = bt.indicators.CrossOver(self.stoch.percK, self.stoch.percD)
        self.order = None      # 用來追蹤尚未完成的訂單
        self.bar_executed = None  # 記錄進場的 bar

    def log(self, txt, dt=None):
        ''' 記錄日誌 '''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
        
    def notify_order(self, order):
        ''' 訂單通知 '''
        # 如果訂單尚未完成，直接返回
        if order.status in [order.Submitted, order.Accepted]:
            return

        # 訂單完成
        if order.status in [order.Completed]:
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
            # 紀錄進場時的 bar
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
        # 訂單處理完成後清空訂單追蹤
        self.order = None

    def next(self):
        # 若有尚未完成的訂單則等待
        if self.order:
            return

        cash = self.broker.getcash()
        size = int(cash / self.data.open[0] * self.p.order_percentage)
        k_value = self.stoch.percK[0]
        d_value = self.stoch.percD[0]

        # 若無持倉，根據 KD 交叉訊號進場（仍保留原進場條件）
        if not self.position:
            # 進場做多：當 %K 與 %D 均處於超賣區，且發生黃金交叉
            if k_value < self.p.oversold and d_value < self.p.oversold and self.crossover > 0:
                self.log("Long Entry Signal: K: %.2f, D: %.2f" % (k_value, d_value))
                self.order = self.buy(size=size)
            # 進場做空：當 %K 與 %D 均處於超買區，且發生死亡交叉
            elif k_value > self.p.overbought and d_value > self.p.overbought and self.crossover < 0:
                self.log("Short Entry Signal: K: %.2f, D: %.2f" % (k_value, d_value))
                self.order = self.sell(size=size)
        else:
            # 若已持倉，判斷是否達到持有固定時間後平倉
            if self.bar_executed is not None and (len(self) - self.bar_executed) >= self.p.holding_period:
                self.log("Exiting position after holding for %d bars" % self.p.holding_period)
                self.order = self.close()