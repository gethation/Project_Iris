import plotly.graph_objects as go
import plotly.subplots as sp
import pandas as pd
from typing import List, Dict
import datetime

def plot_stock_chart(df,
                     start_date, 
                     end_date,
                     cash_value_list,
                     indicator_list,
                     trade_information_list: List[Dict]) -> None:
    
    df['date'] = pd.to_datetime(df['date'])
    # cash_value_list=  cash_value_list+1
    # 如果你傳入的 start_date 與 end_date 是 datetime 物件，也可用 pd.to_datetime 轉換：
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    # 讀取資料
    # df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv')
    # df = pd.read_csv(r'C:\Users\Huang\Work place\Qauntitative Trading\Data_base\ALL_stock_DATE_OHLC_dict\2330.csv')
    # start_date = '2009-01-01'
    # end_date = '2009-12-31'
    # df['date'] = pd.to_datetime(df['date'])

    # 控制資料的日期範圍，例如：從 2009-01-01 到 2009-12-31
    # start_date = '2009-01-01'
    # end_date = '2009-12-31'
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    # print(len(cash_value_list['value']) , len(df))
    # if len(cash_value_list['value']) == len(df):
    #     x_custom = df['Date']
    # else:
    #     x_custom = df['Date'].iloc[:len(cash_value_list['value'])]

    df['Up'] = df['close'] > df['open']

    # 分成上漲與下跌兩個子集
    df_up = df[df['Up']]
    df_down = df[~df['Up']]
    print(df.head())
    # 建立包含兩個子圖的圖形：上方為K線圖，下方為成交量圖
    fig = sp.make_subplots(rows=4, cols=1, shared_xaxes=True,
                            vertical_spacing=0,
                            row_heights=[0.3, 1, 0.2, 0.4],
                            subplot_titles=("2330 Stock Price", "", ""))

    # 添加 K 線圖，並修改上升與下降的顏色
    fig.add_trace(
        go.Scatter(
            x=cash_value_list['date'],
            y=cash_value_list['value'],
            mode='lines',
            name='value',
            hovertemplate='%{x|%Y-%m-%d}<br>value: %{y}<extra></extra>'
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=cash_value_list['date'],
            y=cash_value_list['cash'],
            mode='lines',
            name='cash',
            hovertemplate='cash: %{y}<extra></extra>'
        ),
        row=1, col=1
    )
    hover_text = []
    for i in range(len(df)):
        text = (
            f"Date: {df['date'].iloc[i].strftime('%Y-%m-%d')}<br>"
            f"Open: {df['open'].iloc[i]}<br>"
            f"High: {df['high'].iloc[i]}<br>"
            f"Low: {df['low'].iloc[i]}<br>"
            f"Close: {df['close'].iloc[i]}"
        )
        hover_text.append(text)
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='green',  # 上升顏色
            decreasing_line_color='red',
            hovertext=hover_text,
            hoverinfo='text'),     # 下降顏色
        row=2, col=1
    )
    buy_dates, buy_prices = [], []
    sell_dates, sell_prices = [], []
    for trade in trade_information_list:
        # 將 trade['date']（datetime.date 型別）轉換為 Timestamp
        t_date = pd.to_datetime(trade['date'])
        # 若該筆交易日期不在指定範圍內則跳過
        if t_date < pd.to_datetime(start_date) or t_date > pd.to_datetime(end_date):
            continue
        if trade['order_side'] == 'buy':
            buy_dates.append(t_date)
            buy_prices.append(trade['price'])
        elif trade['order_side'] == 'sell':
            sell_dates.append(t_date)
            sell_prices.append(trade['price'])
    
    # 若有買入紀錄則加入正三角形標記
    if buy_dates:
        fig.add_trace(
            go.Scatter(
                x=buy_dates,
                y=buy_prices,
                mode='markers',
                marker=dict(symbol='triangle-up', size=20, color='lightgreen'),
                name='Buy',
                hovertemplate='%{x|%Y-%m-%d}<br>Price: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
    
    # 若有賣出紀錄則加入倒三角形標記
    if sell_dates:
        fig.add_trace(
            go.Scatter(
                x=sell_dates,
                y=sell_prices,
                mode='markers',
                marker=dict(symbol='triangle-down', size=20, color='red'),
                name='Sell',
                hovertemplate='Buy Date: %{x|%Y-%m-%d}<br>Price: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
    # 添加成交量柱狀圖
    fig.add_trace(
        go.Bar(x=df_up['date'], y=df_up['volume'], name='Volume Up', marker_color='lightgreen',
               hovertemplate='%{x|%Y-%m-%d}<br> : %{y}<extra></extra>'),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(x=df_down['date'], y=df_down['volume'], name='Volume Down', marker_color='red',
               hovertemplate='%{x|%Y-%m-%d}<br> : %{y}<extra></extra>'),
        row=3, col=1
    )
        
    fig.add_trace(
        go.Scatter(
            x=cash_value_list['date'],
            y=indicator_list[0]['MACD'],
            mode='lines',
            name='MACD',
            hovertemplate='MACD: %{y:.2f}<extra></extra>'
        ),
        row=4, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=cash_value_list['date'],
            y=indicator_list[0]['Signal'],
            mode='lines',
            name='Signal',
            hovertemplate='Signal: %{y:.2f}<extra></extra>'
        ),
        row=4, col=1
    )

    fig.update_xaxes(rangeslider_visible=False, row=2, col=1)

    # 更新佈局設定
    fig.update_layout(
        title="Apple Stock Price and Volume",
        xaxis_rangeslider_visible=False,
        plot_bgcolor='white',  # 圖表背景色
        paper_bgcolor='white',  # 整個畫布背景色
        hovermode='x unified',
        height = 1500
    )

    fig.update_xaxes(tickformat='%Y-%m-%d', showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridcolor='lightgray')

    fig.show()
