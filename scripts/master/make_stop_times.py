"""時刻表行列とマスタから stop_times.csv を作成する。"""
from argparse import ArgumentParser
from pathlib import Path
import sys

import pandas as pd

base_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(base_dir / "scripts"))
from utils import normalize_time


parser = ArgumentParser()
parser.add_argument("--route-id", default="89_up")
args = parser.parse_args()

matrix_file = base_dir / "data" / "processed" / f"{args.route_id}_timetable_matrix.csv"
master_dir = base_dir / "data" / "routes" / args.route_id / "master"
matrix = pd.read_csv(matrix_file, encoding="utf-8-sig")
trips = pd.read_csv(master_dir / "trips.csv", encoding="utf-8-sig")
stops = pd.read_csv(master_dir / "stops.csv", encoding="utf-8-sig", dtype={"stop_id": str})

rows = []
for trip in trips.itertuples(index=False):
    column_name = getattr(trip, "column_name", f"col_{trip.column_index}")
    if column_name not in matrix.columns:
        raise ValueError(f"時刻表の便列が見つかりません: {column_name}")
    for stop_order, item in enumerate(matrix[["stop_name", column_name]].itertuples(index=False), start=1):
        stop_name, value = item
        scheduled_time = normalize_time(value)
        if scheduled_time is None:
            continue
        stop = stops.loc[stops["stop_order"] == stop_order]
        if len(stop) != 1 or stop.iloc[0]["stop_name"] != stop_name:
            raise ValueError(f"stops.csv の順序または停留所名が一致しません: {stop_order}, {stop_name}")
        rows.append({"trip_id": trip.trip_id, "trip_no": trip.trip_no, "column_index": trip.column_index,
                     "route_id": trip.route_id, "direction": trip.direction,
                     "stop_id": stop.iloc[0]["stop_id"], "stop_name": stop_name,
                     "stop_order": stop_order, "scheduled_time": scheduled_time})

stop_times = pd.DataFrame(rows).sort_values(["trip_no", "stop_order"])
if stop_times.empty:
    raise ValueError("stop_times を生成できませんでした")
stop_times.to_csv(master_dir / "stop_times.csv", index=False, encoding="utf-8-sig")
print(f"stop_times数: {len(stop_times)}\n便数: {stop_times['trip_id'].nunique()}\n保存: {master_dir / 'stop_times.csv'}")
