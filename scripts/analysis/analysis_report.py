import pandas as pd
import numpy as np

# ===================================
# 読み込み
# ===================================
df = pd.read_csv(
    "../data/processed/clean_bus_log.csv",
    encoding="utf-8-sig"
)

print("読込件数:", len(df))

# ===================================
# 分析対象
# ===================================
df = df.dropna(subset=["遅延秒"])

print("分析件数:", len(df))

# ===================================
# 集計
# ===================================

report = (
    df.groupby("バス停名")
      .agg(
          件数=("遅延秒","count"),
          平均差秒=("遅延秒","mean"),
          中央値=("遅延秒","median"),
          標準偏差=("遅延秒","std"),
          最速=("遅延秒","min"),
          最遅=("遅延秒","max"),
          p90=("遅延秒",lambda x:x.quantile(.90)),
          p95=("遅延秒",lambda x:x.quantile(.95))
      )
      .reset_index()
)

# ===================================
# 割合
# ===================================

rate = (
    df.groupby("バス停名")["遅延秒"]
      .agg(
          **{
              "30秒以内率":lambda x:(x<=30).mean()*100,
              "60秒以内率":lambda x:(x<=60).mean()*100,
              "120秒超率":lambda x:(x>120).mean()*100
          }
      )
      .reset_index()
)

report = report.merge(
    rate,
    on="バス停名"
)

# ===================================
# 小数整理
# ===================================

num_cols = report.select_dtypes(include=np.number).columns

report[num_cols] = report[num_cols].round(1)

# ===================================
# 遅れが大きい順
# ===================================

report = report.sort_values(
    "平均差秒",
    ascending=False
)

# ===================================
# 保存
# ===================================

report.to_csv(
    "../data/output/analysis_report.csv",
    index=False,
    encoding="utf-8-sig"
)

print(report.head(20))

print()
print("analysis_report.csv を作成しました。")
