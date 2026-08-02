"""時刻表行列の各便列から trips.csv を作成する。"""
from argparse import ArgumentParser
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(base_dir / "scripts"))
from utils import normalize_time


parser = ArgumentParser()
parser.add_argument("--route-id", default="89_up")
parser.add_argument("--direction", default="up")
args = parser.parse_args()

matrix_file = base_dir / "data" / "processed" / f"{args.route_id}_timetable_matrix.csv"
output_file = base_dir / "data" / "routes" / args.route_id / "master" / "trips.csv"
matrix = pd.read_csv(matrix_file, encoding="utf-8-sig")
first_stop = matrix.iloc[0]
rows = []
for column_index, column_name in enumerate(matrix.columns[3:], start=3):
    start_time = normalize_time(first_stop[column_name])
    if start_time is not None:
        trip_no = len(rows) + 1
        rows.append({"column_index": column_index, "column_name": column_name, "trip_no": trip_no,
                     "trip_id": f"{args.route_id}_{trip_no:03d}", "route_id": args.route_id,
                     "direction": args.direction, "start_time": start_time})
trips = pd.DataFrame(rows)
if trips.empty:
    raise ValueError("始発停留所から有効な便時刻を取得できませんでした")
output_file.parent.mkdir(parents=True, exist_ok=True)
trips.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"便数: {len(trips)}\n保存: {output_file}")
