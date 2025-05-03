import backtrader as bt
import pandas as pd
import quantstats as qs
import datetime
import plotly.graph_objects as go
import os
# from ../InteractiveWindow import plot_stock_chart
import pickle

data_path = r"C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\BTCUSDT_all_1h_data.csv"
start_time = datetime.datetime(2024, 11, 1, 13, 0, 0)
todate_time = datetime.datetime(2025, 3, 27, 11, 0, 0)

df = pd.read_csv(data_path, header=0)
df['datetime'] = pd.to_datetime(df['open_time'], format='%Y-%m-%d %H:%M:%S')
df = df[(df["datetime"] >= start_time) & (df["datetime"] < todate_time)]
df.set_index('datetime', inplace=True)
df_bt = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

hours_data = bt.feeds.PandasData(dataname=df_bt)


if __name__ == '__main__':
    from adaptiveGrid import VolatilityGrid
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1e9)  # 設定初始資金為 100,000
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(VolatilityGrid)
    
    # Add data source
    cerebro.adddata(hours_data)

    
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

    # Plot the results if needed
    qs.reports.html(returns, output=r"Cache\bench_mark.html")
    os.startfile(r"C:\Users\Huang\Work place\Project_Iris\Qauntitative Trading\Cache\bench_mark.html")
    cerebro.plot(style = 'candle')
