import backtrader as bt
from datetime import datetime

import pandas as pd
import quantstats as qs
from datetime import datetime
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os

class PyramidArb(bt.Strategy):
    params = dict(
        threshold=0.4,   # 每 0.4 的 spread 增量加一次仓
        base_size=1.0,   # 每次下单数量
    )

    def __init__(self):
        # 订单引用
        self.order0 = None
        self.order1 = None
        # 金字塔状态
        self.pyramid_count = 0
        self.side = 0  # +1 表示多价差，-1 表示空价差
        self.value_series = []
        self.datetime_series = []

    def next(self):

        # 至少两根 bar
        if len(self) < 2:
            return

        dt = self.datas[0].datetime.datetime(0)
        
        value = self.broker.getvalue()
        self.datetime_series.append(dt)
        self.value_series.append(value)
        # 只在订单仍在挂单或已提交但未完成时阻塞
        pending0 = self.order0 and self.order0.status in [bt.Order.Submitted, bt.Order.Accepted]
        pending1 = self.order1 and self.order1.status in [bt.Order.Submitted, bt.Order.Accepted]
        if pending0 or pending1:
            dt = self.datetime.datetime().strftime('%Y-%m-%d %H:%M:%S')
            status0 = self.order0.status if self.order0 else None
            status1 = self.order1.status if self.order1 else None
            print(f'[{dt}] Waiting for orders: order0_status={status0}, order1_status={status1}')
            return

        # 手工计算 spread
        px0_curr = self.datas[0].close[0]
        px1_curr = self.datas[1].close[0]
        px0_prev = self.datas[0].close[-1]
        px1_prev = self.datas[1].close[-1]

        last_spread    = (px0_prev - px1_prev) * 2.0 / (px0_prev + px1_prev)
        current_spread = (px0_curr - px1_curr) * 2.0 / (px0_curr + px1_curr)
        th = self.p.threshold
        dt = self.datetime.datetime().strftime('%Y-%m-%d %H:%M:%S')

        # 1) 跨零点平仓
        if self.pyramid_count and last_spread * current_spread < 0:
            print(f'[{dt}] Cross zero - closing: last_spread={last_spread:.4f}, current_spread={current_spread:.4f}')
            self.order0 = self.close(data=self.datas[0])
            self.order1 = self.close(data=self.datas[1])
            self.pyramid_count = 0
            self.side = 0
            return

        # 2) 首次进场
        if self.side == 0:
            if current_spread > th:
                print(f'[{dt}] Enter SHORT spread: spread={current_spread:.4f} > {th}')
                self.side = -1
                self.pyramid_count = 1
                self.order0 = self.sell(data=self.datas[0], size=self.p.base_size)
                self.order1 = self.buy (data=self.datas[1], size=self.p.base_size)
            elif current_spread < -th:
                print(f'[{dt}] Enter LONG spread: spread={current_spread:.4f} < {-th}')
                self.side = +1
                self.pyramid_count = 1
                self.order0 = self.buy (data=self.datas[0], size=self.p.base_size)
                self.order1 = self.sell(data=self.datas[1], size=self.p.base_size)
            return

        # 3) 金字塔加码
        next_level = th * (self.pyramid_count + 1)
        if self.side == -1 and current_spread > next_level:
            print(f'[{dt}] Pyramid ADD SHORT: spread={current_spread:.4f} > {next_level:.4f} (#{self.pyramid_count+1})')
            self.order0 = self.sell(data=self.datas[0], size=self.p.base_size)
            self.order1 = self.buy (data=self.datas[1], size=self.p.base_size)
            self.pyramid_count += 1
        elif self.side == +1 and current_spread < -next_level:
            print(f'[{dt}] Pyramid ADD LONG: spread={current_spread:.4f} < {-next_level:.4f} (#{self.pyramid_count+1})')
            self.order0 = self.buy (data=self.datas[0], size=self.p.base_size)
            self.order1 = self.sell(data=self.datas[1], size=self.p.base_size)
            self.pyramid_count += 1

    def notify_order(self, order):
        dt = self.datetime.datetime().strftime('%Y-%m-%d %H:%M:%S')
        # 提交/接受
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            side = 'BUY' if order.isbuy() else 'SELL'
            print(f'[{dt}] Order {order.getordername()} {side} pending...')
            return
        # 完成成交
        if order.status == bt.Order.Completed:
            side = 'BUY' if order.isbuy() else 'SELL'
            ep = order.executed.price
            sz = order.executed.size
            val = order.executed.value
            com = order.executed.comm
            print(f'[{dt}] {side} EXECUTED - {order.data._name}: price={ep:.4f}, size={sz}, value={val:.2f}, comm={com:.2f}')
        # 取消/拒单等
        elif order.status in [bt.Order.Canceled, bt.Order.Margin, bt.Order.Rejected]:
            side = 'BUY' if order.isbuy() else 'SELL'
            print(f'[{dt}] Order {order.getordername()} {side} {order.getstatusname()}')

        # 清除引用
        if order.data == self.datas[0]:
            self.order0 = None
        else:
            self.order1 = None

    def notify_trade(self, trade):
        if trade.isclosed:
            dt = self.datetime.datetime().strftime('%Y-%m-%d %H:%M:%S')
            print(f'[{dt}] TRADE CLOSED - {trade.data._name}: GrossPnL={trade.pnl:.2f}, NetPnL={trade.pnlcomm:.2f}')

# 用法示例
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    data0 = bt.feeds.GenericCSVData(
        dataname=r"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\XAUT_1m.csv",       # CSV 文件路径
        dtformat=('%Y-%m-%d %H:%M:%S'),  # 日期时间格式
        datetime=0,    # 日期时间列索引（从 0 开始）
        open=1,        # 开盘价列索引
        high=2,        # 最高价列索引
        low=3,         # 最低价列索引
        close=4,       # 收盘价列索引
        volume=5,      # 成交量列索引
        openinterest=-1,  # 是否有持仓量列；-1 表示无此列
        timeframe=bt.TimeFrame.Minutes,  # 数据的周期
        compression=1,              # 每条数据合并多少周期（这里 1 分钟）
        fromdate=datetime(2025, 4, 25, 0, 0, 0),   # 起始时间（含），用 datetime 对象
        todate=datetime(2025, 5, 26, 0, 0, 0) # 结束时间（含），用 datetime 对象
    )

    data1 = bt.feeds.GenericCSVData(
        dataname=r"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\PAXG_1m.csv",       # CSV 文件路径
        dtformat=('%Y-%m-%d %H:%M:%S'),  # 日期时间格式
        datetime=0,    # 日期时间列索引（从 0 开始）
        open=1,        # 开盘价列索引
        high=2,        # 最高价列索引
        low=3,         # 最低价列索引
        close=4,       # 收盘价列索引
        volume=5,      # 成交量列索引
        openinterest=-1,  # 是否有持仓量列；-1 表示无此列
        timeframe=bt.TimeFrame.Minutes,  # 数据的周期
        compression=1,              # 每条数据合并多少周期（这里 1 分钟）
        fromdate=datetime(2025, 4, 25, 0, 0, 0),   # 起始时间（含），用 datetime 对象
        todate=datetime(2025, 5, 26, 0, 0, 0) # 结束时间（含），用 datetime 对象
    )

    cerebro.adddata(data0, name='XAUT')
    cerebro.adddata(data1, name='PAXG')

    cerebro.addstrategy(PyramidArb, threshold=0.2/100, base_size=1.0)
    cerebro.broker.setcash(1e4)
    cerebro.broker.setcommission(commission=0.02/100, mult = 1)

    print('start backtrading')

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]

    # Output performance metrics
    print("Sharpe Ratio:", strat.analyzers.sharpe.get_analysis())
    print("Returns:", strat.analyzers.returns.get_analysis())
    returns, positions, transactions, gross_lev = strat.analyzers.pyfolio.get_pf_items()

    # # Plot the results if needed
    qs.reports.html(returns, output=r"Cache\bench_mark.html")
    os.startfile(r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\Cache\bench_mark.html")
    cerebro.plot(style = 'candle')


    port = pd.Series(strat.value_series, index=strat.datetime_series)

    returns = port.pct_change().fillna(0)

    cum_returns = (1 + returns).cumprod() - 1

    plt.figure(figsize=(10, 6))
    plt.plot(cum_returns.index, cum_returns.values)
    plt.xlabel('Date')
    plt.ylabel('Cumulative Returns')
    plt.title('Strategy Cumulative Returns Over Time')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
