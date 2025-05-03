import pandas as pd
import random
import matplotlib.pyplot as plt
from tqdm import tqdm
import numpy as np

# 1. 讀取並排序資料
df = pd.read_csv(r'C:\Users\Huang\Work place\Project_Iris\DataAnalysis\DataBase\BTC_5m.csv', parse_dates=["datetime"])
df = df.sort_values("datetime").reset_index(drop=True)

initial_stake       = 10      # 初始下注 USD
stake               = initial_stake
equity              = 10    # 帳戶總資金

# 停利／停損參數
tp_ratio            = 1.03       # +1% 停利
sl_ratio            = 0.97       # −1% 停損

# Martingale 最多連敗次數上限
max_doubles_limit  =  30        # 最多連續虧損 5 次

# 追蹤連敗與最高連敗
current_doubles     = 0
max_doubles         = 0

equity_curve = []
times        = []

# random.seed(2)
open_trade   = False
entry_price  = None
direction    = None  # 1=多，-1=空

for idx, row in tqdm(df.iterrows(), total=len(df), desc="回測進度"):
    price = row["close"]
    hi    = row["high"]
    lo    = row["low"]

    # 無持倉就開新倉
    if not open_trade:
        entry_price = price
        direction   = random.choice([1, -1])
        open_trade  = True

    pnl = None
    # 檢查 TP/SL
    if direction == 1:
        if hi >= entry_price * tp_ratio:
            pnl = stake * (tp_ratio - 1)
        elif lo <= entry_price * sl_ratio:
            pnl = stake * (sl_ratio - 1)
    else:
        if lo <= entry_price * sl_ratio:
            pnl = stake * (tp_ratio - 1)
        elif hi >= entry_price * tp_ratio:
            pnl = stake * (sl_ratio - 1)

    # 若觸及 TP/SL，平倉並更新 Martingale
    if pnl is not None:
        equity += pnl

        if pnl < 0:
            # 虧損 → 先計算若翻倍後是否超過上限
            current_doubles += 1
            max_doubles = max(max_doubles, current_doubles)

            if current_doubles < max_doubles_limit:
                stake *= 2
            else:
                # 已達上限，直接重設
                stake = initial_stake
                current_doubles = 0
        else:
            # 獲利 → 重設
            stake = initial_stake
            current_doubles = 0

        open_trade = False

    # 無論是否平倉，都記錄資金與時間
    equity_curve.append(equity)
    times.append(row["datetime"])

# 畫出資產曲線
print("歷史最高連敗次數：", max_doubles)
df_eq = pd.DataFrame({
    "datetime": times,
    "equity": equity_curve
})
df_eq.set_index("datetime", inplace=True)

# 2. 計算滾動最高與回撤
df_eq["rolling_max"] = df_eq["equity"].cummax()
df_eq["drawdown"]    = df_eq["equity"] / df_eq["rolling_max"] - 1

# 3. 計算 Max Drawdown
max_dd = df_eq["drawdown"].min()            # 負值

# 4. 計算年化報酬率（CAGR）
start_equity = df_eq["equity"].iloc[0]
end_equity   = df_eq["equity"].iloc[-1]
# 以日為單位計算回測天數
period_days  = (df_eq.index[-1] - df_eq.index[0]).total_seconds() / (3600 * 24)
cagr = (end_equity / start_equity) ** (365.0 / period_days) - 1

# 5. Calmar Ratio
calmar_ratio = cagr / abs(max_dd)
df_daily = df_eq["equity"].resample("D").last()

# 2. 計算每日報酬率
daily_ret = df_daily.pct_change().dropna()

# 3. 計算 Sharpe Ratio
#    Sharpe = mean(daily_ret - rf) / std(daily_ret) * sqrt(年化因子)
#    這裡 rf = 0，年化因子 = 365
sharpe_ratio = daily_ret.mean() / daily_ret.std() * np.sqrt(365)

print(f"Sharpe Ratio: {sharpe_ratio:.2f}")

# 6. 輸出結果
print(f"CAGR:         {cagr:.2%}")
print(f"Max Drawdown: {max_dd:.2%}")
print(f"Calmar Ratio: {calmar_ratio:.2f}")



plt.figure(figsize=(10,4))
plt.plot(times, equity_curve)
plt.xlabel("Time")
plt.ylabel("Equity (USD)")
plt.title(f"Martingale (Max Doublings={max_doubles}, Limit={max_doubles_limit})")
plt.tight_layout()
plt.show()


