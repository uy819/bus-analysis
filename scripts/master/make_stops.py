"""時刻表行列から stops.csv を作成する。"""
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd


parser = ArgumentParser()
parser.add_argument("--route-id", default="89_up")
parser.add_argument("--route-no", default="89")
args = parser.parse_args()

base_dir = Path(__file__).resolve().parents[2]
matrix_file = base_dir / "data" / "processed" / f"{args.route_id}_timetable_matrix.csv"
output_file = base_dir / "data" / "routes" / args.route_id / "master" / "stops.csv"
matrix = pd.read_csv(matrix_file, encoding="utf-8-sig", dtype=str)
names = matrix["stop_name"].fillna("").str.strip()
if (names == "").any():
    raise ValueError("stop_name に空値があります。HTMLの時刻表行を確認してください。")
stops = pd.DataFrame({"stop_id": [f"{args.route_no}{i:03d}" for i in range(1, len(names) + 1)], "stop_order": range(1, len(names) + 1), "stop_name": names})
output_file.parent.mkdir(parents=True, exist_ok=True)
stops.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"停留所数: {len(stops)}\n保存: {output_file}")
