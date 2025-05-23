import pandas as pd
import numpy as np
import plotly.express as px

# 读取数据
df_x = pd.read_csv(r'DataBase\XAUT1m.csv',
                   parse_dates=['timestamp'],
                   index_col='timestamp')
df_p = pd.read_csv(r'DataBase\PAXG1m.csv',
                   parse_dates=['timestamp'],
                   index_col='timestamp')

# 重命名收盘价列
df_x = df_x.rename(columns={'close': 'xaut_close'})
df_p = df_p.rename(columns={'close': 'paxg_close'})

# 合并
df = pd.merge(df_x[['xaut_close']],
              df_p[['paxg_close']],
              left_index=True, right_index=True,
              how='inner')

# 计算指标： (paxg - xaut) * 2 / (paxg + xaut)
df['spread_ratio'] = (df['paxg_close'] - df['xaut_close']) * 2 / (df['paxg_close'] + df['xaut_close'])

df_plot = df.reset_index()

fig = px.bar(
    df_plot,
    x='timestamp',
    y='spread_ratio',
    title='PAXG & XAUT CLOSE SPREAD（(P−X)*2/(P+X)）',
    labels={
        'timestamp': 'time',
        'spread_ratio': 'SPREAD'
    }
)
fig.update_layout(
    plot_bgcolor='white',      # 绘图区背景
    paper_bgcolor='white',     # 整体画布背景
)

# # 5. 设置 x 轴刻度与滑块
# fig.update_xaxes(
#     tickformat='%H:%M',
#     dtick=60 * 1000,
#     rangeslider=dict(visible=True)
# )

fig.update_yaxes(
    tickformat='.2%'   # 两位小数的百分比；改为 '.0%' 只显示整数百分比
)

fig.update_layout(margin=dict(l=40, r=40, t=60, b=40))

fig.show()
