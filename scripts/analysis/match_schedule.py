"""実績到着ログを便単位で時刻表に突合する。"""
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from matcher import attach_schedule, attach_trip_result, mark_partial_run, match_runs


parser = ArgumentParser()
parser.add_argument("--route-id", default="89_up")
parser.add_argument("--gap-minutes", type=float, default=30, help="この分数以上の記録間隔を別便とする")
parser.add_argument("--max-diff-minutes", type=float, default=60, help="trip評価に使う最大時刻差")
args = parser.parse_args()

base_dir = Path(__file__).resolve().parents[2]
arrival_file = base_dir / "data" / "raw" / "bus_arrival_log.csv"
stop_times_file = base_dir / "data" / "routes" / args.route_id / "master" / "stop_times.csv"
output_file = base_dir / "data" / "processed" / f"{args.route_id}_arrival_with_schedule.csv"

arrival = pd.read_csv(arrival_file, encoding="utf-8-sig")
stop_times = pd.read_csv(stop_times_file, encoding="utf-8-sig")
required_arrival = {"日付", "到着時刻", "バス停名", "ナンバー"}
required_stop_times = {"trip_id", "route_id", "stop_name", "stop_order", "scheduled_time"}
if missing := required_arrival - set(arrival.columns):
    raise ValueError(f"到着ログに必要な列がありません: {sorted(missing)}")
if missing := required_stop_times - set(stop_times.columns):
    raise ValueError(f"stop_timesに必要な列がありません: {sorted(missing)}")

gap_sec = int(args.gap_minutes * 60)
max_diff_sec = int(args.max_diff_minutes * 60)
print("======================\ntrip推定開始\n======================")
trip_result = match_runs(arrival, stop_times, max_diff_sec=max_diff_sec, gap_sec=gap_sec)
matched = attach_trip_result(arrival, trip_result, gap_sec=gap_sec)
matched = mark_partial_run(attach_schedule(matched, stop_times))

matched = matched.sort_values(["日付", "vehicle_id", "arrival_sec"]).reset_index(drop=True)
output_file.parent.mkdir(parents=True, exist_ok=True)
matched.to_csv(output_file, index=False, encoding="utf-8-sig")

print(trip_result.head(20).to_string(index=False))
print(f"\n車両日数: {trip_result['run_id'].nunique()}\n推定便数: {len(trip_result)}\n時刻表便数: {trip_result['trip_id'].nunique()}")
print(f"時刻表一致率: {matched['scheduled_time'].notna().mean():.1%}")
print(f"保存: {output_file}")
