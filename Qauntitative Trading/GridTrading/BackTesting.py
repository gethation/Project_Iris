import backtrader as bt
import pandas as pd
import quantstats as qs
import datetime
import plotly.graph_objects as go
import os
from InteractiveWindow import plot_stock_chart
import pickle

data_path = r'C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\DataBase\BTCUSDT_all_1m_data.csv'
start_time = datetime.datetime(2024, 1, 1, 0, 0, 0)
todate_time = datetime.datetime(2025, 3, 24, 0, 0, 0)

minute_data = bt.feeds.GenericCSVData(
    dataname=data_path,            # CSV檔案路徑
    dtformat=('%Y-%m-%d %H:%M:%S'),            # 日期時間格式
    fromdate=start_time,   # 開始日期
    todate=todate_time,   # 結束日期
    timeframe=bt.TimeFrame.Minutes,           # 設定為秒級別
    compression=1,                            # 每筆資料代表 1 秒
    datetime=0,                               # 日期時間欄位在第 0 列
    time=-1,                                  # 如果時間已包含在 datetime 裡就設為 -1
    open=1,                                   # 開盤價欄位在 CSV 中的索引（依據你的檔案格式調整）
    high=2,                                   # 最高價欄位索引
    low=3,                                    # 最低價欄位索引
    close=4,                                  # 收盤價欄位索引
    volume=5,                                 # 成交量欄位索引
    openinterest=-1                         # 沒有持倉量資料則設為 -1
)

if __name__ == '__main__':
    from GridTrading.StrategyLib import PercentageGridStrategy, Locater
    cerebro = bt.Cerebro()
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.setcash(1e8)  # 設定初始資金為 100,000
    cerebro.addstrategy(PercentageGridStrategy)
    
    # Add data source
    cerebro.adddata(minute_data)
    # cerebro.resampledata(minute_data, timeframe=bt.TimeFrame.Days, compression=1)

    
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
    # print("Returns:", strat.analyzers.returns.get_analysis())
    returns, positions, transactions, gross_lev = strat.analyzers.pyfolio.get_pf_items()
    # plot_stock_chart(df = pd.read_csv(data_path),
    #                  start_date = start_time, 
    #                  end_date = todate_time,
    #                  cash_value_list = strat.daily_records,
    #                  indicator_list = None,
    #                  trade_information_list = strat.trade_records)

    # qs.reports.metrics(returns, mode='full')
    # Plot the results if needed
    qs.reports.html(returns, output=r"DataBase\bench_mark.html")
    os.startfile(r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\Database\bench_mark.html")
