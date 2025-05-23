import pandas as pd
import plotly.express as px

# 1. 读取数据并合并（同前）  
df_x = pd.read_csv(r'DataBase\XAUT1m.csv', parse_dates=['timestamp'], index_col='timestamp')
df_p = pd.read_csv(r'DataBase\PAXG1m.csv', parse_dates=['timestamp'], index_col='timestamp')
df_x = df_x.rename(columns={'close': 'xaut_close'})
df_p = df_p.rename(columns={'close': 'paxg_close'})
df = pd.merge(df_x[['xaut_close']], df_p[['paxg_close']], left_index=True, right_index=True, how='inner')
df_plot = df.reset_index()

# 2. 画两条折线
fig = px.line(
    df_plot,
    x='timestamp',
    y=['paxg_close', 'xaut_close'],
    labels={
        'timestamp': 'time',
        'value': 'price',
        'variable': 'asset'
    },
    title='PAXG vs XAUT 1m close',
    template='plotly_white'
)

# 3. x 轴按分钟显示刻度，保留滑块
# fig.update_xaxes(
#     tickformat='%H:%M',
#     dtick=60 * 1000,
#     rangeslider=dict(visible=True)
# )

# fig.update_layout(
#     margin=dict(l=40, r=40, t=60, b=40),
#     legend=dict(title='asset', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
# )

fig.show()
