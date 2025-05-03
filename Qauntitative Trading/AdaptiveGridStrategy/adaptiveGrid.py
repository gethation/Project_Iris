import backtrader as bt
import math

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

class GridByVolatility(bt.Indicator):
    """
    基於波動性的網格指標：
    參數:
      - volatilityType: 'Stdev' 或 'ATR'
      - volatilityLength: 計算波動性所用的周期
      - squeezeAdjustment: 調整係數，用於放大波動性計算結果
      - smoothingPeriod: 平滑網格數值的加權移動平均周期
      - VOLATILITY_ADJUSTMENT: 用於計算上中/下中網格（預設為2）
    """
    lines = ('upperRange2', 'upperRange1', 'midLineAvg', 'lowerRange1', 'lowerRange2',)
    params = (
        ('volatilityType', 'Stdev'),  # 'Stdev' 或 'ATR'
        ('volatilityLength', 200),
        ('squeezeAdjustment', 6),
        ('smoothingPeriod', 2),
        ('VOLATILITY_ADJUSTMENT', 2),
    )

    def __init__(self):
        # 緩存各網格原始值，用於平滑計算
        self.buffer_upperRange2 = []
        self.buffer_upperRange1 = []
        self.buffer_midLine = []
        self.buffer_lowerRange1 = []
        self.buffer_lowerRange2 = []
        # 保存中線和 fullVolatility 的狀態（跨 bar 持續更新）
        self.midLine = None
        self.fullVolatility = None

    def next(self):
        current_close = self.data.close[0]

        # 計算波動性
        if len(self.data) < self.p.volatilityLength:
            volatility = 0.0
        else:
            if self.p.volatilityType == "Stdev":
                period = self.p.volatilityLength
                # 收集最近 period 根 K 線的收盤價
                vals = [self.data.close[-i] for i in range(0, period)]
                mean_val = sum(vals) / period
                sum_sq = sum((x - mean_val) ** 2 for x in vals)
                # 注意：這裡將調整係數放在平方差的平均值內部，與原 Pine Script 相似
                volatility = math.sqrt((sum_sq / period) * self.p.squeezeAdjustment)
            else:
                # ATR 模式，使用內置 ATR 指標
                atr = bt.indicators.ATR(self.data, period=self.p.volatilityLength)[0]
                volatility = atr * self.p.squeezeAdjustment

        # 判斷趨勢方向：價格上漲返回 1，下跌返回 -1，否則返回 0
        if len(self.data) > 1:
            trendDirection = 1 if (current_close - self.data.close[-1]) > 0 else (-1 if (current_close - self.data.close[-1]) < 0 else 0)
        else:
            trendDirection = 0

        # 初始化中線（midLine）
        if self.midLine is None:
            self.midLine = current_close

        # 保存上一根 K 線的中線值
        old_midline = self.midLine

        # 根據價格變化更新中線：若當前價格與中線差距大於波動性，則根據趨勢方向調整中線
        if abs(current_close - old_midline) > volatility:
            self.midLine = old_midline + trendDirection * volatility
        else:
            self.midLine = old_midline

        # 更新 fullVolatility：若中線發生變化則更新為當前波動性，否則保持不變
        if self.fullVolatility is None:
            self.fullVolatility = volatility
        else:
            if self.midLine == old_midline:
                self.fullVolatility = self.fullVolatility
            else:
                self.fullVolatility = volatility

        # 計算原始網格值
        raw_upperRange2 = self.midLine + self.fullVolatility
        raw_upperRange1 = self.midLine + self.fullVolatility / self.p.VOLATILITY_ADJUSTMENT
        raw_midLine    = self.midLine
        raw_lowerRange1 = self.midLine - self.fullVolatility / self.p.VOLATILITY_ADJUSTMENT
        raw_lowerRange2 = self.midLine - self.fullVolatility

        # 添加到緩存中（用於後續平滑）
        self.buffer_upperRange2.append(raw_upperRange2)
        self.buffer_upperRange1.append(raw_upperRange1)
        self.buffer_midLine.append(raw_midLine)
        self.buffer_lowerRange1.append(raw_lowerRange1)
        self.buffer_lowerRange2.append(raw_lowerRange2)

        # 定義加權移動平均 (WMA) 函數：對最後 period 個值進行加權計算
        def wma(buffer, period):
            if len(buffer) < period:
                # 如果不足平滑周期，直接返回最新值
                return buffer[-1]
            else:
                relevant = buffer[-period:]
                # 權重從 1 到 period（最新值權重最大）
                weights = list(range(1, period + 1))
                weighted_sum = sum(w * v for w, v in zip(weights, relevant))
                return weighted_sum / sum(weights)

        # 使用 WMA 平滑各網格值，並將結果存入對應線條中
        self.lines.upperRange2[0] = wma(self.buffer_upperRange2, self.p.smoothingPeriod)
        self.lines.upperRange1[0] = wma(self.buffer_upperRange1, self.p.smoothingPeriod)
        self.lines.midLineAvg[0]  = wma(self.buffer_midLine, self.p.smoothingPeriod)
        self.lines.lowerRange1[0] = wma(self.buffer_lowerRange1, self.p.smoothingPeriod)
        self.lines.lowerRange2[0] = wma(self.buffer_lowerRange2, self.p.smoothingPeriod)

class VolatilityGrid(Basic_Function):
    params = (
        ('grid_levels', 2),     # 初始網格層級（0-4之間，這裡預設在中間層 index 2）
        ('base_quantity', 1),
        ('base_pct', 4/100)   # 每次交易的數量
    )
    def __init__(self):
        super().__init__()

        self.grids_status = {
            'grid': [],  
            'current_layer': self.p.grid_levels  # 預設從中間層開始
        }
        self.grid = GridByVolatility(self.data,
                                     volatilityType='Stdev', 
                                     volatilityLength=200,
                                     squeezeAdjustment=6,
                                     smoothingPeriod=2)
        
        self.grid.plotinfo.plot = True
        self.initialized = False
        self.current_hedgePosition = 0
        self.grid_switcher = 0

    def initialize_grid(self):
        """Init the grid"""

        self.grids_status['grid'] = [
            self.grid.lowerRange2[0],
            self.grid.lowerRange1[0],
            self.grid.midLineAvg[0],
            self.grid.upperRange1[0],
            self.grid.upperRange2[0]
        ]
        current_price = self.data.close[0]
        self.base_quantity = (self.broker.getvalue() * self.p.base_pct) // current_price
        # 根據當前價格所在區間確定網格層級
        for i in range(len(self.grids_status['grid']) - 1):
            lower = self.grids_status['grid'][i]
            upper = self.grids_status['grid'][i+1]
            if lower <= current_price < upper:
                self.grids_status['current_layer'] = i
                break
        else:
            # 如果找不到合適區間，默認設定為中間層（index 2）
            self.grids_status['current_layer'] = 2

        self.log(f"初始化網格層級: {self.grids_status['current_layer']}，網格價格: {self.grids_status['grid']}")
        self.grid_switcher = self.grid.midLineAvg[0]

    def next(self):
        if len(self.data) < 201:
            return
        current_price = self.data.close[0]

        # 第一次運行時初始化網格
        if not self.initialized:
            self.initialize_grid()
            self.initialized = True

        # 更新網格：每根K線根據指標動態更新
        # self.grids_status['grid'] = [
        #     self.grid.lowerRange2[0],

        #     (self.grid.lowerRange1[0]+self.grid.lowerRange2[0])/2,

        #     self.grid.lowerRange1[0],

        #     (self.grid.midLineAvg[0]+self.grid.lowerRange1[0])/2,

        #     self.grid.midLineAvg[0],

        #     (self.grid.midLineAvg[0]+self.grid.upperRange1[0])/2,

        #     self.grid.upperRange1[0],

        #     (self.grid.upperRange1[0]+self.grid.upperRange2[0])/2,
            
        #     self.grid.upperRange2[0]
        # ]
        self.grids_status['grid'] = [
            self.grid.lowerRange2[0],
            self.grid.lowerRange1[0],
            self.grid.midLineAvg[0],
            self.grid.upperRange1[0],
            self.grid.upperRange2[0]
        ]
        if self.grid_switcher != self.grid.midLineAvg[0]:
            self.grid_switcher = self.grid.midLineAvg[0]
            self.log(f"更新網格價格: {self.grids_status['grid']}")
            # self.close()
        self.check_grid_triggers(current_price)

    def check_grid_triggers(self, current_price):

        grid = self.grids_status['grid']
        current_layer = self.grids_status['current_layer']
        
        
        # 確定上下層價格（注意最上層或最下層情況）
        upper_layer_price = grid[current_layer + 1] if current_layer < len(grid) - 1 else current_price*2
        lower_layer_price = grid[current_layer - 1] if current_layer > 0 else 0

        if current_price >= upper_layer_price:
            self.sell(size=self.base_quantity,
                    exectype=bt.Order.Limit,
                    price=upper_layer_price)
            
            # print(current_layer)
            self.grids_status['current_layer'] += 1
            return

        if current_price <= lower_layer_price:
            self.buy(size=self.base_quantity,
                    exectype=bt.Order.Limit,
                    price=lower_layer_price)
            
            # print(current_layer)
            self.grids_status['current_layer'] -= 1
        
        
