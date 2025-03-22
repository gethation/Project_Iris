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

class PercentageGridStrategy(Basic_Function):
    params = (
        ('base_price', 82826),
        ('price_pct', 0.01),      # 网格间距百分比（1%）
        ('base_qty', 1),         # 基础交易量
        ('grid_levels', 25),        # 单边网格层数
        ('max_position', 100),    # 最大持仓绝对值
        ('price_precision', 2),    # 价格精度
        ('use_atr', False),         # 是否使用ATR调整间距
        ('atr_period', 14),        # ATR计算周期
    )

    def __init__(self):
        # 数据引用
        super().__init__()
        self.dataclose = self.datas[0].close
        
        # 初始化指标
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        
        # 策略状态
        self.grid_initialized = False
        self.grids_status = {'grid' : [],'current_layer':self.p.grid_levels}

    def initialize_grid(self):
        """Init the grid"""
        if self.p.price_precision == None:
            self.base_price = round(self.dataclose[0], self.p.price_precision)
        else:
            self.base_price = self.p.base_price

        print(f'\n=== LAYOUT ===')
        print(f'baseline: {self.base_price:.2f}')
        print(f'ATR: {self.atr[0]:.2f}')
        
        # 计算动态间距
        effective_pct = self.p.price_pct
        if self.p.use_atr:
            atr_pct = self.atr[0] / self.base_price
            effective_pct = max(min(atr_pct, 0.05), 0.005)  # 限制在0.5%-5%
            print(f'根据ATR调整间距至: {effective_pct*100:.2f}%')

        # 生成网格价格

        grid_price = [self.base_price]
        for i in range(1, self.p.grid_levels + 1):
            grid_price.append(self.calc_price(self.base_price, -effective_pct, i))
            grid_price.append(self.calc_price(self.base_price, effective_pct, i))
        
        self.grids_status['grid'] = sorted(grid_price)

        self.print_grid_layout()

    def calc_price(self, base, pct_change, level):
        price = base * (1 + pct_change) ** level
        return round(price, self.p.price_precision)

    def print_grid_layout(self):
        """打印网格布局"""
        print("\GRID：")
        for i, price in enumerate(self.grids_status['grid']):
            print(f'layer:{i:2d}-{price:.2f}')

    def check_grid_triggers(self, current_price):
        """检查并触发网格订单"""
        for price in self.sorted_prices:
            grid = self.grids[price]
                
            if (grid['type'] == 'long' and current_price <= price) or \
               (grid['type'] == 'short' and current_price >= price):
                
                self._place_grid_order(price, grid['type'])
                grid['triggered'] = True   

    def next(self):
        if not self.grid_initialized:
            self.initialize_grid()
            self.grid_initialized = True
            self.buy(size=self.p.base_qty,
                      exectype=bt.Order.Limit,
                      price=self.base_price)
            return
            
        current_price = self.data.close[0]
        self.check_grid_triggers(current_price)

        self.record()

    def check_grid_triggers(self, current_price):

        current_layer = self.grids_status['current_layer']
        grid = self.grids_status['grid']
        upper_layer_price = grid[current_layer + 1]
        lower_layer_price = grid[current_layer - 1]

        if current_price >= upper_layer_price:
            self.sell(size=self.p.base_qty,
                      exectype=bt.Order.Limit,
                      price=upper_layer_price)
            
            self.grids_status['current_layer'] += 1

        if current_price <= lower_layer_price:
            self.buy(size=self.p.base_qty,
                      exectype=bt.Order.Limit,
                      price=lower_layer_price)
            
            self.grids_status['current_layer'] -= 1
