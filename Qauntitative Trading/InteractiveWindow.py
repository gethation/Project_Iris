import plotly.graph_objects as go
import plotly.subplots as sp
import pandas as pd
from typing import List, Dict

def plot_cash_value(fig, cash_value_list):
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
    return fig

def plot_candel_stick(fig, df):
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

    return fig

def plot_trade_information(fig, trade_information_list, start_date, end_date):
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
        return fig

def plot_volume(fig, df):

    df_up = df[df['Up']]
    df_down = df[~df['Up']]

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

    return fig
def plot_indicator(fig, indicator_list, cash_value_list):
    for indicator in indicator_list:
        for key, value in indicator.items():
            fig.add_trace(
                go.Scatter(
                    x = cash_value_list['date'],
                    y = value ,
                    mode='lines',
                    name = key,
                    hovertemplate='Signal: %{y:.2f}<extra></extra>'
                ),
                row=4, col=1
            )
    return fig

def plot_stock_chart(df,
                     start_date, 
                     end_date,
                     cash_value_list,
                     indicator_list,
                     trade_information_list: List[Dict]) -> None:
    
    df['date'] = pd.to_datetime(df['date'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    df = df.copy()
    df.loc[:, 'Up'] = df['close'] > df['open']

    # 建立包含兩個子圖的圖形：上方為K線圖，下方為成交量圖
    fig = sp.make_subplots(rows=4, cols=1, shared_xaxes=True,
                            vertical_spacing=0,
                            row_heights=[0.3, 1, 0.2, 0.4],
                            subplot_titles=("2330 Stock Price", "", ""))
    
    fig = plot_cash_value(fig=fig, cash_value_list=cash_value_list)
    fig = plot_candel_stick(fig=fig, df=df)
    fig = plot_trade_information(fig=fig, 
                                 trade_information_list=trade_information_list, 
                                 start_date=start_date,
                                 end_date=end_date)
    fig = plot_volume(fig=fig, df=df)
    fig = plot_indicator(fig=fig,
                         indicator_list=indicator_list,
                         cash_value_list=cash_value_list)

    fig.update_xaxes(rangeslider_visible=False, row=2, col=1)

    # 更新佈局設定
    fig.update_layout(
        title="Apple Stock Price and Volume",
        xaxis_rangeslider_visible=False,
        plot_bgcolor='white',  # 圖表背景色
        paper_bgcolor='white',  # 整個畫布背景色
        hovermode='x unified'
    )

    fig.update_xaxes(tickformat='%Y-%m-%d', showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridcolor='lightgray')

    fig.show()
