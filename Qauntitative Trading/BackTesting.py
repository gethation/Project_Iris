import backtrader as bt
import pandas as pd
import quantstats as qs
import datetime
import plotly.graph_objects as go
from interactive_window import plot_stock_chart

data_path = 'Data_base/ALL_stock_DATE_OHLC_dict/2330.csv'
start_time = datetime.datetime(2022, 9, 1)
todate_time = datetime.datetime(2024, 1, 1)


data = bt.feeds.GenericCSVData(
    dataname=data_path,          # CSV 檔案路徑
    fromdate=start_time,
    todate=todate_time,
    dtformat=('%Y-%m-%d'),             # 日期格式
    datetime=0,                       # 日期所在欄位（索引從 0 開始）
    open=1,                           # 開盤價所在欄位
    high=2,                           # 最高價所在欄位
    low=3,                            # 最低價所在欄位
    close=4,                          # 收盤價所在欄位
    volume=5,                         # 成交量所在欄位
    openinterest=-1                   # 如果沒有持倉量欄位，設為 -1
)

if __name__ == '__main__':
    from StrategyLib import MACDStrategy, SmaCross, KDStrategy
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MACDStrategy)
    
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
    print("Drawdown:", strat.analyzers.drawdown.get_analysis())
    print("Trade Statistics:", strat.analyzers.trades.get_analysis())
    print("Returns:", strat.analyzers.returns.get_analysis())
    returns, positions, transactions, gross_lev = strat.analyzers.pyfolio.get_pf_items()

    qs.reports.metrics(returns, "SPY", mode='full')
    print(strat.daily_records)
    # Plot the results if needed
    cerebro.plot()
    plot_stock_chart(df = pd.read_csv(r'C:\Users\Huang\Work place\Qauntitative Trading\Data_base\ALL_stock_DATE_OHLC_dict\2330.csv'),
                     start_date = start_time, 
                     end_date = todate_time,
                     cash_value_list = strat.daily_records,
                     indicator_list = strat.indicator,
                     trade_information_list = strat.trade_records)
