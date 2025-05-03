import backtrader as bt
import pandas as pd
import quantstats as qs
import datetime
import plotly.graph_objects as go
import os
import pickle

data_path = r"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\BTCUSDT_all_1d_data.csv"
start_time = datetime.datetime(2024, 2, 10, 0, 0, 0)
todate_time = datetime.datetime(2024, 11, 6, 0, 0, 0)

days_data = bt.feeds.GenericCSVData(
    dataname=data_path,            # CSV檔案路徑
    dtformat=('%Y-%m-%d'),            # 日期時間格式
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
    from StrategyLib import Hedger
    cerebro = bt.Cerebro()
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.setcash(1e5)  # 設定初始資金為 100,000
    cerebro.addstrategy(Hedger)
    
    # Add data source
    cerebro.adddata(days_data)

    
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]

    # Output performance metrics
    # print("Sharpe Ratio:", strat.analyzers.sharpe.get_analysis())
    # print("Drawdown:", strat.analyzers.drawdown.get_analysis())
    # print("Trade Statistics:", strat.analyzers.trades.get_analysis())
    # print("Returns:", strat.analyzers.returns.get_analysis())
    returns, positions, transactions, gross_lev = strat.analyzers.pyfolio.get_pf_items()

    # Plot the results if needed
    with open(r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\Cache\macd_record.pkl", "wb") as file:
        pickle.dump(strat.macd_record, file)
    qs.reports.html(returns, output=r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\Cache\bench_mark.html")
    os.startfile(r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\Cache\bench_mark.html")
    cerebro.plot()
