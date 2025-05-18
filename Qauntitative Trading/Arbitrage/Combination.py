import backtrader as bt
from datetime import datetime, time

class CombinedGridStrategy(bt.Strategy):
    params = dict(
        # —— 周一～周四 (Weekday) 网格参数 —— 
        weekday_grid_ratio=0.1/100,
        weekday_order_size=4.0,

        # —— 周五 17:00～周日 17:00 (Weekend) 网格参数 —— 
        weekend_grid_ratio=0.1/100,
        weekend_order_size=0.1,
    )

    def __init__(self):
        # 状态机：IDLE, WEEKDAY_GRID, WEEKDAY_REDUCE, WEEKEND_GRID
        self.state = 'IDLE'

        # 通用字段
        self.grid_center  = None
        self.buy_order    = None
        self.sell_order   = None

        # 用来确保每天/每周期只启动一次
        self.last_weekday_date = None
        self.last_weekend_date = None
        self.value_series = []
        self.datetime_series = []

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f"{dt.isoformat()}  {txt}")

    # —— 两种网格下单辅助函数 —— #
    def place_weekday_grid(self):
        pu = self.grid_center * (1 + self.p.weekday_grid_ratio)
        pd = self.grid_center * (1 - self.p.weekday_grid_ratio)
        self.sell_order = self.sell(size=self.p.weekday_order_size,
                                    exectype=bt.Order.Limit,
                                    price=pu)
        self.buy_order  = self.buy (size=self.p.weekday_order_size,
                                    exectype=bt.Order.Limit,
                                    price=pd)
        self.log(f"WEEKDAY GRID ↕ BUY@{pd:.2f}  SELL@{pu:.2f}")

    def place_weekend_grid(self):
        pu = self.grid_center * (1 + self.p.weekend_grid_ratio)
        pd = self.grid_center * (1 - self.p.weekend_grid_ratio)
        self.sell_order = self.sell(size=self.p.weekend_order_size,
                                    exectype=bt.Order.Limit,
                                    price=pu)
        self.buy_order  = self.buy (size=self.p.weekend_order_size,
                                    exectype=bt.Order.Limit,
                                    price=pd)
        self.log(f"WEEKEND GRID ↕ BUY@{pd:.2f}  SELL@{pu:.2f}")

    def next(self):
        dt    = self.datas[0].datetime.datetime(0)
        today = dt.date()
        wd    = dt.weekday()  # Mon=0, Sun=6
        
        value = self.broker.getvalue()
        self.datetime_series.append(dt)
        self.value_series.append(value)


        # —— 1) 周一～周四 17:00 启动分批网格 —— #
        if wd < 4:
            # 1a) 17:00 整点新一天启动
            if dt.time() == time(17,0) and self.last_weekday_date != today:
                self.last_weekday_date = today
                self.state = 'WEEKDAY_GRID'
                self.grid_center = self.data.open[0]
                self.log(f"=== WEEKDAY GRID START @{self.grid_center:.2f} ===")

                # 撤掉可能残留的单
                for od in (self.buy_order, self.sell_order):
                    if od and od.status in (bt.Order.Accepted, bt.Order.Submitted):
                        self.cancel(od)
                self.buy_order = self.sell_order = None

                # 挂第一笔网格单
                self.place_weekday_grid()
                return

            # 1b) 18:00 切入 REDUCE
            if self.state == 'WEEKDAY_GRID' and (dt.time() >= time(18,0)):
                self.state = 'WEEKDAY_REDUCE'
                self.log("=== WEEKDAY REDUCE START ===")
                # 撤网格单
                for od in (self.buy_order, self.sell_order):
                    if od and od.status in (bt.Order.Accepted, bt.Order.Submitted):
                        self.cancel(od)
                self.buy_order = self.sell_order = None

                # 分批平第一笔
                if self.position.size > 0:
                    px = self.grid_center * (1 + self.p.weekday_grid_ratio)
                    self.sell_order = self.sell(size=self.p.weekday_order_size,
                                                exectype=bt.Order.Limit,
                                                price=px)
                    self.log(f"WEEKDAY EXIT LONG PIECE @{px:.2f}")
                elif self.position.size < 0:
                    px = self.grid_center * (1 - self.p.weekday_grid_ratio)
                    self.buy_order = self.buy(size=self.p.weekday_order_size,
                                              exectype=bt.Order.Limit,
                                              price=px)
                    self.log(f"WEEKDAY EXIT SHORT PIECE @{px:.2f}")
                else:
                    self.state = 'IDLE'
                return

            # 1c) 18:05 强制平仓
            if self.state == 'WEEKDAY_REDUCE' and dt.time() >= time(18,2):
                self.log("=== WEEKDAY FORCE FLAT ===")
                # 先撤单，再市价平仓
                for od in (self.buy_order, self.sell_order):
                    if od and od.status in (bt.Order.Accepted, bt.Order.Submitted):
                        self.cancel(od)
                self.buy_order = self.sell_order = None
                self.close()
                self.state = 'IDLE'
                return

        # —— 2) 周五17:00～周日17:00 执行基础网格 —— #
        is_weekend_period = (
            (wd == 4 and dt.time() >= time(17,0)) or
            (wd in [5]) or
            (wd == 6 and dt.time() < time(17,0))
        )
        if is_weekend_period:
            # 2a) 周五17:00 新一周末启动
            if wd == 4 and dt.time() == time(17,0) and self.last_weekend_date != today:
                self.last_weekend_date = today
                self.state = 'WEEKEND_GRID'
                self.grid_center = self.data.open[0]
                self.log(f"=== WEEKEND GRID START @{self.grid_center:.2f} ===")

                # 撤单
                for od in (self.buy_order, self.sell_order):
                    if od and od.status in (bt.Order.Accepted, bt.Order.Submitted):
                        self.cancel(od)
                self.buy_order = self.sell_order = None

                # 挂初始双向网格
                self.place_weekend_grid()
                return

            # 2b) 基础网格：如果无挂单，就补一次
            if self.state == 'WEEKEND_GRID' and not self.buy_order and not self.sell_order:
                self.place_weekend_grid()
                return

        # —— 3) 其它时间点 —— 什么都不做 —— #
        # （可选：在非网格窗口撤单并清状态）
        if self.state in ['WEEKDAY_GRID','WEEKDAY_REDUCE','WEEKEND_GRID']:
            # 不在合法区间时，先撤单
            valid_wd = (wd<4 and time(17,0)<=dt.time()<time(18,2)) or is_weekend_period
            if not valid_wd:
                self.log("=== OUTSIDE WINDOW: CANCEL ALL & FLAT ===")
                # 1) 撤掉所有限价单
                for od in (self.buy_order, self.sell_order):
                    if od and od.status in (bt.Order.Accepted, bt.Order.Submitted):
                        self.cancel(od)
                self.buy_order = self.sell_order = None

                # 2) 市价平掉所有持仓
                self.close()

                # 3) 重置状态
                self.state = 'IDLE'

    def notify_order(self, order):
        if order.status in (order.Canceled, order.Margin, order.Rejected):
            if order is self.buy_order:  self.buy_order  = None
            if order is self.sell_order: self.sell_order = None
            return

        if order.status != order.Completed:
            return
        

        dt_full = self.datas[0].datetime.datetime(0)
        tnow = dt_full.time()

        price = order.executed.price
        self.log(f"ORDER COMPLETED: {'BUY' if order.isbuy() else 'SELL'} @{price:.2f}")


        # —— 周一～周四：分批网格或减仓逻辑 —— #
        if self.state in ['WEEKDAY_GRID', 'WEEKDAY_REDUCE']:

            # 只在 GRID 且 17:00 ≤ t < 18:00 时挂网格
            if self.state == 'WEEKDAY_GRID' and order.status == order.Completed:
                # 新增时间判断
                if time(17,0) <= tnow < time(18,0):
                    other = self.sell_order if order.isbuy() else self.buy_order
                    if other and other.status in (bt.Order.Submitted, bt.Order.Accepted):
                        self.cancel(other)
                    self.grid_center = price
                    self.buy_order = self.sell_order = None
                    self.place_weekday_grid()
                else:
                    # 如果已经到 18:00 及以后，就不要再挂 GRID 单
                    self.log(f"Skipped GRID re-placement at {tnow}")
                return

            # REDUCE 成交后分批继续减仓
            if self.state == 'WEEKDAY_REDUCE':
                self.grid_center = price
                self.buy_order = self.sell_order = None
                rem = abs(self.position.size)
                if rem > 0:
                    nxt = min(self.p.weekday_order_size, rem)
                    if order.issell():
                        px = self.grid_center * (1 + self.p.weekday_grid_ratio)
                        self.sell_order = self.sell(size=nxt,
                                                    exectype=bt.Order.Limit,
                                                    price=px)
                        self.log(f"WEEKDAY KEEP EXIT LONG @{px:.2f}")
                    else:
                        px = self.grid_center * (1 - self.p.weekday_grid_ratio)
                        self.buy_order = self.buy(size=nxt,
                                                  exectype=bt.Order.Limit,
                                                  price=px)
                        self.log(f"WEEKDAY KEEP EXIT SHORT @{px:.2f}")
                else:
                    self.log("WEEKDAY ALL FLAT")
                    self.state = 'IDLE'
                return

        # —— 周五～周日：基础网格成交后更新中心 —— #
        if self.state == 'WEEKEND_GRID':
            # 成交后撤对边，更新中心，挂新双边
            other = self.sell_order if order.isbuy() else self.buy_order
            if other and other.status in (bt.Order.Submitted, bt.Order.Accepted):
                self.cancel(other)
            self.grid_center = price
            self.buy_order = self.sell_order = None
            self.place_weekend_grid()
            return