import pandas as pd
import numpy as np
from pathlib import Path

# =====================================
# パス設定
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "clean_bus_log.csv"
OUTPUT_FILE = BASE_DIR / "data" / "output" / "weekday_report.csv"

# =====================================
# 読み込み
# =====================================

df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

print("読込件数:", len(df))

# =====================================
# 遅延秒があるデータだけ
# =====================================

df = df.dropna(subset=["遅延秒"])

print("分析件数:", len(df))

# =====================================
# 曜日の順番
# =====================================

weekday_order = {
    "月": 0,
    "火": 1,
    "水": 2,
    "木": 3,
    "金": 4,
    "土": 5,
    "日": 6,
}

# =====================================
# 集計
# =====================================

report = (
    df.groupby("曜日")
    .agg(
        件数=("遅延秒", "count"),
        平均遅延秒=("遅延秒", "mean"),
        中央値=("遅延秒", "median"),
        標準偏差=("遅延秒", "std"),
        最速=("遅延秒", "min"),
        最遅=("遅延秒", "max"),
        p90=("遅延秒", lambda x: x.quantile(0.90)),
        p95=("遅延秒", lambda x: x.quantile(0.95)),
    )
    .reset_index()
)

# =====================================
# 割合
# =====================================

rate = (
    df.groupby("曜日")["遅延秒"]
    .agg(
        **{
            "30秒以内率": lambda x: (x <= 30).mean() * 100,
            "60秒以内率": lambda x: (x <= 60).mean() * 100,
            "120秒超率": lambda x: (x > 120).mean() * 100,
        }
    )
    .reset_index()
)

report = report.merge(rate, on="曜日")

# =====================================
# 丸め
# =====================================

num_cols = report.select_dtypes(include=np.number).columns
report[num_cols] = report[num_cols].round(1)

# =====================================
# 曜日順
# =====================================

report["sort"] = report["曜日"].map(weekday_order)

report = (
    report.sort_values("sort")
    .drop(columns="sort")
)

# =====================================
# 保存
# =====================================

report.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print()
print(report)
print()
print(f"保存しました：{OUTPUT_FILE}")
