import backtrader as bt
from datetime import datetime

class TimeBoundGridStrategy(bt.Strategy):
    params = dict(
        grid_ratio=0.08/100,    # 网格比例
        order_size=1.0      # 每笔手数
    )

    def __init__(self):
        self.state = 'WAIT'       # WAIT, GRID, REDUCE, FINAL
        self.grid_center = None
        self.buy_order = None
        self.sell_order = None
        self.last_grid_date = None  # 记录上一次启动网格的日期
        self.value_series = []
        self.datetime_series = []

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f"{dt.isoformat()}  {txt}")

    def place_grid(self):
        """正常网格：中心上下各挂一单"""
        pu = self.grid_center * (1 + self.p.grid_ratio)
        pd = self.grid_center * (1 - self.p.grid_ratio)
        self.sell_order = self.sell(size=self.p.order_size,
                                    exectype=bt.Order.Limit,
                                    price=pu)
        self.buy_order  = self.buy (size=self.p.order_size,
                                    exectype=bt.Order.Limit,
                                    price=pd)
        self.log(f"GRID ↕ BUY@{pd:.2f}  SELL@{pu:.2f}")

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        today = dt.date()
        value = self.broker.getvalue()
        self.datetime_series.append(dt)
        self.value_series.append(value)

        
        # —— 新增：每天 17:00，只要是新的一天，就重置到 GRID 阶段 —— 
        if dt.hour == 17 and dt.minute == 0 and self.last_grid_date != today:
            self.last_grid_date = today        # 标记今天已启动
            self.state = 'GRID'
            self.grid_center = self.data.open[0]
            self.log(f"=== DAILY GRID START @{self.grid_center:.2f} ===")
            # 先撤掉可能残留的订单（保险起见）
            for od in (self.buy_order, self.sell_order):
                if od and od.status in (bt.Order.Submitted, bt.Order.Accepted):
                    self.cancel(od)
            self.buy_order = self.sell_order = None
            # 然后挂初始双向网格
            self.place_grid()
            return

        # 2) 18:00 切入 REDUCE（分批减仓）
        if self.state=='GRID' and (dt.hour>18 or (dt.hour==18 and dt.minute>=0)):
            self.state = 'REDUCE'
            self.log("=== REDUCE START: piecewise exit ===")
            # 撤掉网格挂单
            for od in (self.buy_order, self.sell_order):
                if od and od.status in (bt.Order.Submitted, bt.Order.Accepted):
                    self.cancel(od)
            self.buy_order = self.sell_order = None

            # 分批挂第一笔退出单
            if self.position.size > 0:
                # 多头：以 last center*(1+ratio) 卖出一手
                price = self.grid_center * (1 + self.p.grid_ratio)
                self.sell_order = self.sell(size=self.p.order_size,
                                            exectype=bt.Order.Limit,
                                            price=price)
                self.log(f"EXIT LONG PIECE @{price:.2f}")
            elif self.position.size < 0:
                # 空头：以 last center*(1−ratio) 买入一手
                price = self.grid_center * (1 - self.p.grid_ratio)
                self.buy_order = self.buy(size=self.p.order_size,
                                          exectype=bt.Order.Limit,
                                          price=price)
                self.log(f"EXIT SHORT PIECE @{price:.2f}")
            else:
                self.state = 'FINAL'
            return

        # 3) 18:05 强制市价平仓
        if self.state == 'REDUCE' and dt.hour == 18 and dt.minute >= 5:
            self.log("=== FORCE FLAT MARKET ===")

            # 1) 先撤掉所有未成交的限价单
            for od in (self.buy_order, self.sell_order):
                if od and od.status in (bt.Order.Submitted, bt.Order.Accepted):
                    self.cancel(od)
            self.buy_order = self.sell_order = None

            # 2) 再市价平仓（关闭所有剩余仓位）
            self.close()

            # 3) 标记结束
            self.state = 'FINAL'
            return

    def notify_order(self, order):
        # 只关注成交和撤单/拒单
        if order.status in (order.Canceled, order.Margin, order.Rejected):
            if order is self.buy_order:  self.buy_order  = None
            if order is self.sell_order: self.sell_order = None
            return

        if order.status != order.Completed:
            return

        price = order.executed.price
        self.log(f"ORDER COMPLETED: {'BUY' if order.isbuy() else 'SELL'} @{price:.2f}")

        if self.state == 'GRID':
            # —— 保持原网格逻辑 —— 
            other = self.sell_order if order.isbuy() else self.buy_order
            if other and other.status in (bt.Order.Submitted, bt.Order.Accepted):
                self.cancel(other)
            self.grid_center = price
            self.buy_order = self.sell_order = None
            self.place_grid()

        elif self.state == 'REDUCE':
            # —— 分批减仓逻辑 —— 
            # 1) 更新中心
            self.grid_center = price
            # 2) 清引用
            self.buy_order = self.sell_order = None
            # 3) 计算剩余仓位
            rem = abs(self.position.size)
            if rem > 0:
                nxt = min(self.p.order_size, rem)
                if order.issell():
                    # 卖出一手(减多头)后，继续挂下一笔卖单
                    px = self.grid_center * (1 + self.p.grid_ratio)
                    self.sell_order = self.sell(size=nxt,
                                                exectype=bt.Order.Limit,
                                                price=px)
                    self.log(f"KEEP EXIT LONG PIECE @{px:.2f}")
                else:
                    # 买入一手(平空头)后，继续挂下一笔买单
                    px = self.grid_center * (1 - self.p.grid_ratio)
                    self.buy_order = self.buy(size=nxt,
                                              exectype=bt.Order.Limit,
                                              price=px)
                    self.log(f"KEEP EXIT SHORT PIECE @{px:.2f}")
            else:
                self.log("All flat, strategy finished")
                self.state = 'FINAL'
