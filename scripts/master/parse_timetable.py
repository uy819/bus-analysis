"""路線HTMLの時刻表を、便列を保った行列CSVへ変換する。"""
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd


parser = ArgumentParser()
parser.add_argument("--route-id", default="89_up")
parser.add_argument("--table-index", type=int, default=1, help="HTML内の時刻表tableの0始まり番号")
args = parser.parse_args()

base_dir = Path(__file__).resolve().parents[2]
route_dir = base_dir / "data" / "routes" / args.route_id
html_file = route_dir / "html" / f"{args.route_id}.html"
output_file = base_dir / "data" / "processed" / f"{args.route_id}_timetable_matrix.csv"

tables = pd.read_html(html_file, encoding="utf-8")
if args.table_index >= len(tables):
    raise ValueError(f"時刻表tableが見つかりません: index={args.table_index}, tables={len(tables)}")

raw = tables[args.table_index]
if raw.shape[1] < 3:
    raise ValueError("時刻表tableに必要な列がありません")
matrix = raw.copy().fillna("").astype(str)
matrix = matrix.loc[matrix.iloc[:, 2].str.strip().ne("")].reset_index(drop=True)
matrix = matrix.replace({"｜": "", "-": ""})
width = matrix.shape[1]
matrix.columns = ["fare_symbol", "fare", "stop_name", *[f"col_{i}" for i in range(3, width)]]
output_file.parent.mkdir(parents=True, exist_ok=True)
matrix.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"停留所数: {len(matrix)}\n便数: {width - 3}\n保存: {output_file}")
