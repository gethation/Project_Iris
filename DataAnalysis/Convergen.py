import ccxt
import plotly.express as px
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime


# 1. 参数
exchange     = ccxt.binance()
symbols      = ['BTC/USDT','ETH/USDT','DOGE/USDT','XRP/USDT']
reset_min    = 15
lookback_h   = 12

# 2. 拉 1m 收盘价（同前）
now_ms   = exchange.milliseconds()
since_ms = now_ms - lookback_h*3600*1000
dfs = {}
for s in symbols:
    ohlcv = exchange.fetch_ohlcv(s, '1m', since=since_ms, limit=lookback_h*60)
    df     = pd.DataFrame(ohlcv, columns=['ts','o','h','l','c','v'])
    df['dt']= pd.to_datetime(df['ts'], unit='ms')
    df.set_index('dt', inplace=True)
    dfs[s]  = df['c']
price = pd.DataFrame(dfs)

# 3. 计算 %∆ 并打上窗口标签（同前）
def compute_spaghetti(df, interval):
    df2 = df.copy()
    df2['win'] = ((df2.index.view("int64") // 1_000_000_000) // 60 // interval).astype(int)
    out = []
    for win, grp in df2.groupby('win', sort=True):
        base = grp.iloc[0, :-1]
        pct  = (grp.iloc[:, :-1] / base - 1) * 100
        pct['win'] = win
        pct['dt']  = grp.index
        out.append(pct.set_index('dt'))
    return pd.concat(out).sort_index()

spag = compute_spaghetti(price, reset_min)

# 4. 选两条要比较的 symbol
sym_a, sym_b = 'XRP/USDT', 'BTC/USDT'
diff_series  = spag[sym_a] - spag[sym_b]

# 5. 用 make_subplots 建两行图，第一行画 Spaghetti，第二行画 Bar
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.7, 0.3],
    vertical_spacing=0.05,
    specs=[[{"type":"scatter"}],
           [{"type":"bar"}]]
)

# 6. 第一行：逐窗口、逐 symbol 断线
colors = px.colors.qualitative.Plotly
windows = sorted(spag['win'].unique())
for i, sym in enumerate(symbols):
    for w in windows:
        grp = spag[spag['win']==w]
        fig.add_trace(
            go.Scatter(
                x=grp.index,
                y=grp[sym],
                mode='lines',
                name=sym if w==windows[0] else None,
                legendgroup=sym,
                showlegend=bool(w==windows[0]),
                line=dict(color=colors[i % len(colors)], width=2)
            ),
            row=1, col=1
        )
# 分隔线
for w in windows:
    t0 = spag[spag['win']==w].index[0]
    fig.add_vline(x=t0, line_dash="dash", line_color="gray", row=1, col=1)

# 7. 第二行：%∆ 差值 Bar
fig.add_trace(
    go.Bar(
        x=diff_series.index,
        y=diff_series.values,
        name=f"{sym_a} - {sym_b}",
        marker_color='gray',
    ),
    row=2, col=1
)

# 8. 布局调整
fig.update_xaxes(rangeslider_visible=False)
fig.update_layout(
    plot_bgcolor='white',
    paper_bgcolor='white',
    title=f"Spaghetti Chart + {sym_a} vs {sym_b} 差值直方圖",
    yaxis_title="% 变化",
    yaxis2_title=f"{sym_a} - {sym_b} (%∆)",
    legend=dict(orientation="h", y=-0.2)
)

fig.show()
