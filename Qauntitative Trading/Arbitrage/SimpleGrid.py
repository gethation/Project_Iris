import backtrader as bt

class GridStrategy(bt.Strategy):
    params = dict(
        grid_ratio=0.15/100,      # 网格间距比例，比如 0.01 = 1%
        order_size=2.0,       # 每笔订单规模（手数或数量）
    )

    def __init__(self):
        self.buy_order  = None  # 当前挂的买单
        self.sell_order = None  # 当前挂的卖单
        self.grid_center = None # 网格中心价格
        self.value_series = []
        self.datetime_series = []

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        value = self.broker.getvalue()
        self.datetime_series.append(dt)
        self.value_series.append(value)


        # 初始化网格中心
        if self.grid_center is None:
            self.grid_center = self.data.open[0]

        # 如果当前没有挂单，就放出上下两个限价单
        if not self.buy_order and not self.sell_order:
            price_up   = self.grid_center * (1 + self.params.grid_ratio)
            price_down = self.grid_center * (1 - self.params.grid_ratio)

            self.sell_order = self.sell(
                size=self.params.order_size,
                exectype=bt.Order.Limit,
                price=price_up
            )
            self.buy_order = self.buy(
                size=self.params.order_size,
                exectype=bt.Order.Limit,
                price=price_down
            )

    def notify_order(self, order):
        # 只处理完全成交的单
        if order.status == order.Completed:
            executed_price = order.executed.price
            if order.isbuy():
                self.log(f"BUY executed at {executed_price:.2f}")
                # 买单成交后，撤销旧卖单
                if self.sell_order and self.sell_order.status in (bt.Order.Submitted, bt.Order.Accepted):
                    self.cancel(self.sell_order)
            else:  # sell
                self.log(f"SELL executed at {executed_price:.2f}")
                # 卖单成交后，撤销旧买单
                if self.buy_order and self.buy_order.status in (bt.Order.Submitted, bt.Order.Accepted):
                    self.cancel(self.buy_order)

            # 以成交价作为新的网格中心，挂新的买卖单
            self.grid_center = executed_price
            price_up   = self.grid_center * (1 + self.params.grid_ratio)
            price_down = self.grid_center * (1 - self.params.grid_ratio)

            self.sell_order = self.sell(
                size=self.params.order_size,
                exectype=bt.Order.Limit,
                price=price_up
            )
            self.buy_order = self.buy(
                size=self.params.order_size,
                exectype=bt.Order.Limit,
                price=price_down
            )

        # 如果有撤单/拒单，清理对应引用，方便 next 重新下单
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            if order == self.buy_order:
                self.buy_order = None
            elif order == self.sell_order:
                self.sell_order = None

    def log(self, txt, dt=None):
        '''简单的日志函数'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f"{dt.isoformat()}  {txt}")
