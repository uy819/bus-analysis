"""routes.csv を作成する。"""
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd


parser = ArgumentParser()
parser.add_argument("--route-id", default="89_up")
parser.add_argument("--route-no", default="89")
parser.add_argument("--route-name", default="糸満線")
parser.add_argument("--direction", default="up")
args = parser.parse_args()

base_dir = Path(__file__).resolve().parents[2]
output_file = base_dir / "data" / "routes" / args.route_id / "master" / "routes.csv"
output_file.parent.mkdir(parents=True, exist_ok=True)
routes = pd.DataFrame([vars(args)])
routes.columns = ["route_id", "route_no", "route_name", "direction"]
routes.to_csv(output_file, index=False, encoding="utf-8-sig")
print(routes.to_string(index=False))
print(f"保存: {output_file}")
