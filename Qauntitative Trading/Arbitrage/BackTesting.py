import backtrader as bt
import pandas as pd
import quantstats as qs
from datetime import datetime
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import os
# from ../InteractiveWindow import plot_stock_chart
import pickle

data_path = r"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\XAUT_1m.csv"

data = bt.feeds.GenericCSVData(
    dataname=data_path,       # CSV 文件路径
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
    fromdate=datetime(2025, 5, 9, 17, 0, 0),   # 起始时间（含），用 datetime 对象
    todate=datetime(2025, 5, 11, 19, 0, 0) # 结束时间（含），用 datetime 对象
)



if __name__ == '__main__':
    # from Arbitrage import TimeBoundGridStrategy
    from Combination import CombinedGridStrategy
    cerebro = bt.Cerebro()
    cerebro.broker.setcommission(commission=0.02/100, mult = 10)  # 設定手續費
    cerebro.broker.setcash(1e4)  # 設定初始資金為 100,000
    cerebro.addstrategy(CombinedGridStrategy)
    
    # Add data source
    cerebro.adddata(data)

    
    # Add analyzers: Sharpe Ratio, Drawdown, Trade Statistics, and Returns
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
    # print("Drawdown:", strat.analyzers.drawdown.get_analysis())
    # print("Trade Statistics:", strat.analyzers.trades.get_analysis())
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

