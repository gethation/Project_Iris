import pandas as pd
import numpy as np
import mplfinance as mpf

def load_data(csv_path):
    """
    载入 CSV，要求列名：timestamp, open, high, low, close, volume
    并将 timestamp 设为 DatetimeIndex
    """
    df = pd.read_csv(
        csv_path,
        parse_dates=['timestamp'],
        index_col='timestamp'
    )
    # 确保列都是小写
    df.columns = [c.lower() for c in df.columns]
    return df

def find_pivots(df, left=3, right=3):
    """
    找 swing highs/lows：
      left, right：左右各比多少根 K 线高/低才算 pivot。
    返回两个布尔 Series：is_high, is_low。
    """
    highs = df['high'].values
    lows  = df['low'].values
    n = len(df)
    is_high = np.zeros(n, dtype=bool)
    is_low  = np.zeros(n, dtype=bool)
    for i in range(left, n-right):
        window_h = highs[i-left : i+right+1]
        window_l = lows[i-left  : i+right+1]
        # 唯一最高/最低
        if highs[i] == window_h.max() and np.sum(window_h == window_h.max()) == 1:
            is_high[i] = True
        if lows[i]  == window_l.min() and np.sum(window_l == window_l.min()) == 1:
            is_low[i] = True
    return pd.Series(is_high, index=df.index), pd.Series(is_low, index=df.index)

def detect_structure(df, is_high, is_low):
    """
    检测 BOS、CHOCH、MSS：
    - 利用 pivot 时间点的集合，再用 ts in pivot_set 判断
    """
    # 先把所有 pivot highs/lows 的时间点摘出来
    pivot_highs = set(is_high[is_high].index)
    pivot_lows  = set(is_low [is_low ].index)

    bos   = []  # list of (timestamp, 'up'/'down')
    choch = []  # list of (timestamp, 'CHOCH up'/'CHOCH down')
    mss   = []  # list of (timestamp, 'MSS up'/'MSS down')

    last_high    = None
    last_low     = None
    last_bos_dir = None
    highest_up   = -np.inf
    lowest_dn    =  np.inf

    # 逐行遍历，用 iterrows() 拿到 ts 和这一行的数据
    for ts, row in df.iterrows():
        price = row['close']

        # 如果这个时点是 pivot high/low，就更新 last_high/last_low
        if ts in pivot_highs:
            last_high = row['high']
        if ts in pivot_lows:
            last_low  = row['low']

        # 向上突破上一个 pivot high -> BOS up
        if last_high is not None and price > last_high:
            bos.append((ts, 'up'))
            if last_bos_dir == 'down':
                choch.append((ts, 'CHOCH up'))
            if last_bos_dir == 'up' and price > highest_up:
                mss.append((ts, 'MSS up'))
            highest_up   = max(highest_up, price)
            last_bos_dir = 'up'
            last_high    = None  # 重置，等下个 pivot

        # 向下突破上一个 pivot low -> BOS down
        elif last_low is not None and price < last_low:
            bos.append((ts, 'down'))
            if last_bos_dir == 'up':
                choch.append((ts, 'CHOCH down'))
            if last_bos_dir == 'down' and price < lowest_dn:
                mss.append((ts, 'MSS down'))
            lowest_dn    = min(lowest_dn, price)
            last_bos_dir = 'down'
            last_low     = None

    return bos, choch, mss

def plot_smc(df, bos, choch, mss):
    apds = []
    # 预先准备一个全 NaN 的空 Series 模板
    template = pd.Series(index=df.index, data=np.nan)

    # BOS 标记：向上 ↑ 绿，向下 ↓ 红
    for ts, direction in bos:
        y = df.at[ts, 'low'] * 0.995 if direction == 'up' else df.at[ts, 'high'] * 1.005
        s = template.copy()
        s.loc[ts] = y
        apds.append(
            mpf.make_addplot(
                s,
                type='scatter',
                markersize=100,
                marker='^' if direction=='up' else 'v',
                color='g' if direction=='up' else 'r',
                panel=0, secondary_y=False
            )
        )

    # CHOCH 标记：蓝◯
    for ts, _ in choch:
        y = df['high'].max() * 1.02
        s = template.copy()
        s.loc[ts] = y
        apds.append(
            mpf.make_addplot(
                s,
                type='scatter',
                markersize=60,
                marker='o',
                color='b',
                panel=0, secondary_y=False
            )
        )

    # MSS 标记：紫♦
    for ts, _ in mss:
        y = df['low'].min() * 0.98
        s = template.copy()
        s.loc[ts] = y
        apds.append(
            mpf.make_addplot(
                s,
                type='scatter',
                markersize=60,
                marker='D',
                color='m',
                panel=0, secondary_y=False
            )
        )

    mpf.plot(
        df,
        type='candle',
        style='yahoo',
        addplot=apds,
        title='SMC structure:BOS ↑/↓ CHOCH (Blue) MSS (purple)',
        volume=True,
        figsize=(12, 8),
        warn_too_much_data=len(df) + 1
    )

if __name__ == '__main__':
    # 1. 读取你的 data.csv
    df = load_data(r'DataBase\BTC_15m.csv')

    # 2. 找 pivots
    is_high, is_low = find_pivots(df, left=3, right=3)

    # 3. 检测 BOS/CHOCH/MSS
    bos, choch, mss = detect_structure(df, is_high, is_low)

    # 4. 绘图
    plot_smc(df, bos, choch, mss)
