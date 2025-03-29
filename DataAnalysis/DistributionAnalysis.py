import pandas as pd
import plotly.express as px
time_interval = "5m"

# 假設你的 BTC 資料存放在 'btc_daily.csv' 中，且包含 Date, Open, High, Low, Close 這幾個欄位
df = pd.read_csv(rf'DataBase\BTCUSDT_all_{time_interval}_data.csv')

# 將日期欄位轉換為 datetime 格式，並依日期排序
df['open_time'] = pd.to_datetime(df['open_time'])
df.sort_values('open_time', inplace=True)

# 取得前一天的 Close 價格
df['prev_close'] = df['close'].shift(1)

# 根據公式計算波動率: (High - Low) / 前一個 Bar 的 Close
df['volatility'] = (df['high'] - df['low']) / df['prev_close'] *100

# 移除因無前一筆資料而產生的 NaN
df = df.dropna(subset=['volatility'])

# 使用 Plotly 繪製波動率分布直方圖
fig = px.histogram(
    df,
    x='volatility',
    nbins=500,
    title=f'BTC {time_interval} volatility distribution',
    labels={'volatility': 'volatility (%)'},
    histnorm='percent'  # 此處將直方圖數值正規化為每個bin所占的比例
)
fig.update_layout(template="plotly_white")

fig.update_yaxes(tickformat=",.2f", ticksuffix="%")


fig.show()
