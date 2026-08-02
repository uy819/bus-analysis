import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# =====================================
# パス設定
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "data" / "output"
FIG_DIR = OUTPUT_DIR / "figures"

analysis = pd.read_csv(
    OUTPUT_DIR / "analysis_report.csv",
    encoding="utf-8-sig"
)

weekday = pd.read_csv(
    OUTPUT_DIR / "weekday_report.csv",
    encoding="utf-8-sig"
)

hourly = pd.read_csv(
    OUTPUT_DIR / "hourly_report.csv",
    encoding="utf-8-sig"
)

stop_hour = pd.read_csv(
    OUTPUT_DIR / "stop_hour_report.csv",
    encoding="utf-8-sig"
)

# 日本語フォント（Mac）
plt.rcParams["font.family"] = "Hiragino Sans"

# =====================================
# 1. バス停別平均遅延
# =====================================

top = analysis.sort_values(
    "平均差秒",
    ascending=False
)

plt.figure(figsize=(10,8))

plt.barh(
    top["バス停名"],
    top["平均差秒"]
)

plt.xlabel("Average delay (sec)")
plt.title("Average delay by bus stop")

plt.tight_layout()

plt.savefig(
    FIG_DIR / "bus_stop_average_delay.png",
    dpi=200
)

plt.close()

# =====================================
# 2. 曜日別平均遅延
# =====================================

plt.figure(figsize=(6,4))

plt.bar(
    weekday["曜日"],
    weekday["平均遅延秒"]
)

plt.ylabel("Seconds")
plt.title("Average delay by weekday")

plt.tight_layout()

plt.savefig(
    FIG_DIR / "weekday_average_delay.png",
    dpi=200
)

plt.close()

# =====================================
# 3. 時間帯別平均遅延
# =====================================

plt.figure(figsize=(6,4))

plt.bar(
    hourly["時間"].astype(str),
    hourly["平均遅延秒"]
)

plt.xlabel("Hour")
plt.ylabel("Seconds")

plt.title("Average delay by hour")

plt.tight_layout()

plt.savefig(
    FIG_DIR / "hourly_average_delay.png",
    dpi=200
)

plt.close()

# =====================================
# 4. 曜日別30秒以内率
# =====================================

plt.figure(figsize=(6,4))

plt.plot(
    weekday["曜日"],
    weekday["30秒以内率"],
    marker="o"
)

plt.ylim(0,100)

plt.ylabel("%")

plt.title("Arrival within 30 seconds")

plt.tight_layout()

plt.savefig(
    FIG_DIR / "weekday_30sec_rate.png",
    dpi=200
)

plt.close()

# =====================================
# 5. 時間帯別30秒以内率
# =====================================

plt.figure(figsize=(6,4))

plt.plot(
    hourly["時間"].astype(str),
    hourly["30秒以内率"],
    marker="o"
)

plt.ylim(0,100)

plt.xlabel("Hour")
plt.ylabel("%")

plt.title("Arrival within 30 seconds")

plt.tight_layout()

plt.savefig(
    FIG_DIR / "hourly_30sec_rate.png",
    dpi=200
)

plt.close()

print("グラフを保存しました")

print(FIG_DIR)

pivot = stop_hour.pivot_table(
    index="バス停名",
    columns="時間",
    values="平均遅延秒"
)

plt.figure(figsize=(8,10))

sns.heatmap(
    pivot,
    cmap="YlOrRd",
    annot=True,
    fmt=".0f",
    linewidths=0.3
)

plt.title("Average Delay Heatmap")

plt.xlabel("Hour")

plt.ylabel("Bus Stop")

plt.tight_layout()

plt.savefig(
    FIG_DIR / "stop_hour_heatmap.png",
    dpi=300
)

plt.close()

print("グラフを保存しました")
print(FIG_DIR)
