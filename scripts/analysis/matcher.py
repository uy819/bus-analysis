"""バス到着ログを GTFS stop_times の trip に対応付けるユーティリティ。

必要列
  arrival: 日付, ナンバー, バス停名, 到着時刻
  stop_times: trip_id, stop_name, scheduled_time, stop_order

時刻は ``HH:MM`` または ``HH:MM:SS`` を受け付け、GTFS の 24 時以降の
時刻（例: ``25:10:00``）にも対応します。
"""

from __future__ import annotations

import re

import pandas as pd


def time_to_sec(value: object) -> float | None:
    """時刻文字列を秒に変換する。無効値は ``None`` を返す。"""
    if pd.isna(value):
        return None

    match = re.fullmatch(r"\s*(\d+):(\d{1,2})(?::(\d{1,2}))?\s*", str(value))
    if not match:
        return None

    hour, minute, second = (int(part or 0) for part in match.groups())
    if minute >= 60 or second >= 60:
        return None
    return hour * 3600 + minute * 60 + second


def normalize_stop_name(name: object) -> str:
    """照合用に停留所名の軽微な表記揺れを吸収する。"""
    if pd.isna(name):
        return ""

    value = str(name).strip().replace("　", "")
    value = re.split(r"[（(]", value, maxsplit=1)[0]
    value = value.replace("・", "").replace("壷", "壺").strip()
    # 実績ログの乗り場・降り場表記は、時刻表上の2つのターミナル停車へ対応させる。
    if "旭橋" in value and "那覇バスターミナル" in value:
        return "那覇バスターミナルA"
    if "那覇バスターミナル" in value and "おりば" in value:
        return "那覇バスターミナルB"
    if "那覇バスターミナル" in value:
        return "那覇バスターミナル"
    return value


def prepare_arrival(df: pd.DataFrame) -> pd.DataFrame:
    """到着ログに照合用列を追加する。"""
    result = df.copy()
    result["vehicle_id"] = result["ナンバー"].astype(str).str.strip()
    result["stop_key"] = result["バス停名"].map(normalize_stop_name)
    result["arrival_sec"] = result["到着時刻"].map(time_to_sec)
    result["run_id"] = result["日付"].astype(str) + "_" + result["vehicle_id"]
    return result


def split_service_runs(arrival: pd.DataFrame, gap_sec: int = 30 * 60, route_column: str = "系統") -> pd.DataFrame:
    """車両・日付のログを、時間間隔または系統変更で便単位に分ける。"""
    result = arrival.copy()
    if "run_id" not in result or "arrival_sec" not in result:
        result = prepare_arrival(result)
    result["_source_order"] = range(len(result))
    result = result.sort_values(["run_id", "arrival_sec", "_source_order"], na_position="last").copy()
    previous = result.groupby("run_id", sort=False)["arrival_sec"].shift()
    is_new = previous.isna() | ((result["arrival_sec"] - previous) >= gap_sec)
    if route_column in result:
        route = result[route_column].fillna("").astype(str).str.strip()
        previous_route = route.groupby(result["run_id"], sort=False).shift()
        is_new |= route.ne(previous_route) & previous_route.notna()
    sequence = is_new.groupby(result["run_id"], sort=False).cumsum().astype(int)
    result["service_run_id"] = result["run_id"] + "_" + sequence.astype(str).str.zfill(2)
    return result.sort_values("_source_order").drop(columns="_source_order")


def prepare_stop_times(df: pd.DataFrame) -> pd.DataFrame:
    """時刻表に照合用列を追加する。"""
    result = df.copy()
    result["stop_key"] = result["stop_name"].map(normalize_stop_name)
    # 同一便に2回ある那覇バスターミナルを、経路順にA（1回目）/B（2回目）へ分ける。
    terminal = result["stop_key"].eq("那覇バスターミナル")
    occurrence = result.loc[terminal].groupby("trip_id").cumcount()
    result.loc[terminal & occurrence.eq(0), "stop_key"] = "那覇バスターミナルA"
    result.loc[terminal & occurrence.eq(1), "stop_key"] = "那覇バスターミナルB"
    result["scheduled_sec"] = result["scheduled_time"].map(time_to_sec)
    return result


def build_trip_index(stop_times: pd.DataFrame) -> dict[object, pd.DataFrame]:
    return {
        trip_id: group.sort_values("stop_order").reset_index(drop=True)
        for trip_id, group in stop_times.groupby("trip_id", sort=False)
    }


def _clock_diff(arrival_sec: float, scheduled_sec: float) -> float:
    """日跨ぎを含め、もっとも近い到着・予定時刻の差（絶対秒）を返す。"""
    return min(abs(arrival_sec - scheduled_sec + offset) for offset in (-86400, 0, 86400))


def _forward_delay(arrival_sec: float, scheduled_sec: float) -> float:
    """予定時刻以後の到着として扱える最小の遅延秒を返す。"""
    delays = [arrival_sec - scheduled_sec + offset for offset in (-86400, 0, 86400)]
    return min(delay for delay in delays if delay >= 0)


def align_run_to_schedule(
    run: pd.DataFrame,
    schedule: pd.DataFrame,
    max_diff_sec: int = 3600,
) -> dict[int, int]:
    """便内で1対1に対応付け、時刻差が最小の組合せを優先する。

    実績ログは停留所単位で重複し得るため、同一 ``stop_order`` には
    もっとも予定時刻に近い観測だけを割り当てる。
    """
    observed = run.sort_values("arrival_sec", na_position="last").reset_index(drop=True)
    planned = schedule.sort_values("stop_order").reset_index(drop=True)
    candidates: list[tuple[float, int, int]] = []
    for i, actual in observed.iterrows():
        if pd.isna(actual["arrival_sec"]):
            continue
        for j, scheduled in planned.loc[planned["stop_key"] == actual["stop_key"]].iterrows():
            if pd.isna(scheduled["scheduled_sec"]):
                continue
            diff = _clock_diff(float(actual["arrival_sec"]), float(scheduled["scheduled_sec"]))
            if diff <= max_diff_sec:
                candidates.append((diff, i, j))

    matches: dict[int, int] = {}
    used_schedule: set[int] = set()
    for _, observed_pos, planned_pos in sorted(candidates):
        if observed_pos not in matches and planned_pos not in used_schedule:
            matches[observed_pos] = planned_pos
            used_schedule.add(planned_pos)
    return matches


def score_trip(run: pd.DataFrame, schedule: pd.DataFrame, max_diff_sec: int = 3600) -> dict[str, float | int]:
    """一致停留所数と時刻差から trip の適合度を算出する。"""
    observed = run.sort_values("arrival_sec", na_position="last").reset_index(drop=True)
    planned = schedule.sort_values("stop_order").reset_index(drop=True)
    matches = align_run_to_schedule(observed, planned, max_diff_sec)
    diffs = [
        _clock_diff(float(observed.at[i, "arrival_sec"]), float(planned.at[j, "scheduled_sec"]))
        for i, j in matches.items()
    ]

    if not diffs:
        return {"score": float("-inf"), "match_count": 0, "mean_diff": float("inf")}

    mean_diff = sum(diffs) / len(diffs)
    return {
        "score": len(diffs) * 100 - mean_diff / 30,
        "match_count": len(diffs),
        "mean_diff": mean_diff,
    }


def find_best_trip(run: pd.DataFrame, trip_index: dict[object, pd.DataFrame], max_diff_sec: int = 3600, route_column: str = "系統") -> dict[str, object]:
    """便ログに最も適合する trip を返す。"""
    observed = set(run["stop_key"]) - {""}
    candidates = {trip_id: schedule for trip_id, schedule in trip_index.items() if observed & set(schedule["stop_key"])} or trip_index
    if route_column in run.columns:
        routes = set(run[route_column].dropna().astype(str).str.strip()) - {""}
        route_keys = {route.split("_", 1)[0] for route in routes}
        route_candidates = {trip_id: schedule for trip_id, schedule in candidates.items()
                            if "route_id" in schedule
                            and route_keys & {route.split("_", 1)[0] for route in schedule["route_id"].dropna().astype(str).str.strip()}}
        if route_candidates:
            candidates = route_candidates
    best: dict[str, object] = {"trip_id": None, "score": float("-inf"), "match_count": 0, "mean_diff": float("inf")}
    for trip_id, schedule in candidates.items():
        result = score_trip(run, schedule, max_diff_sec)
        if result["score"] > best["score"]:
            best = {"trip_id": trip_id, **result}
    return best


def match_runs(arrival: pd.DataFrame, stop_times: pd.DataFrame, max_diff_sec: int = 3600, gap_sec: int = 30 * 60, route_column: str = "系統") -> pd.DataFrame:
    """到着ログを便単位に分け、それぞれのtripを推定する。"""
    arrivals = split_service_runs(prepare_arrival(arrival), gap_sec, route_column)
    trip_index = build_trip_index(prepare_stop_times(stop_times))
    records = []
    for service_run_id, run in arrivals.groupby("service_run_id", sort=False):
        best = find_best_trip(run.sort_values("arrival_sec"), trip_index, max_diff_sec, route_column)
        records.append({"service_run_id": service_run_id, "run_id": run["run_id"].iloc[0], **best})
    return pd.DataFrame(records)


def attach_trip_result(arrival: pd.DataFrame, trip_result: pd.DataFrame, gap_sec: int = 30 * 60, route_column: str = "系統") -> pd.DataFrame:
    """到着ログに便IDと推定結果を付与する。"""
    arrivals = split_service_runs(prepare_arrival(arrival), gap_sec, route_column)
    return arrivals.merge(trip_result.drop(columns="run_id", errors="ignore"), on="service_run_id", how="left")


def attach_schedule(arrival: pd.DataFrame, stop_times: pd.DataFrame) -> pd.DataFrame:
    """同名停留所・周回路線を考慮し予定時刻を付与する。"""
    arrivals = arrival.copy()
    if "service_run_id" not in arrivals:
        arrivals = split_service_runs(prepare_arrival(arrivals))
    arrivals["stop_key"] = arrivals["バス停名"].map(normalize_stop_name)
    arrivals["schedule_match_status"] = "unmatched"
    schedules = prepare_stop_times(stop_times)
    output = []
    for _, run in arrivals.groupby("service_run_id", sort=False):
        trip_id = run["trip_id"].iloc[0]
        schedule = schedules.loc[schedules["trip_id"] == trip_id]
        observed = run.sort_values("arrival_sec", na_position="last").reset_index(drop=True)
        planned = schedule.sort_values("stop_order").reset_index(drop=True)
        matches = align_run_to_schedule(observed, planned)
        rows = []
        for position, (_, row) in enumerate(observed.iterrows()):
            if position not in matches:
                matching_stops = planned.loc[planned["stop_key"] == row["stop_key"]]
                row["scheduled_time"] = None
                row["scheduled_sec"] = None
                row["stop_order"] = None
                row["schedule_match_status"] = "stop_not_in_timetable" if matching_stops.empty else "duplicate_stop_observation"
            else:
                target = planned.iloc[matches[position]]
                row["scheduled_time"] = target["scheduled_time"]
                row["scheduled_sec"] = target["scheduled_sec"]
                row["stop_order"] = target["stop_order"]
                row["schedule_match_status"] = "matched"
            rows.append(row)
        output.append(pd.DataFrame(rows))
    result = pd.concat(output, ignore_index=True) if output else arrivals.copy()
    # 生の時刻差は早着なら負値。遅延指標には早着を含めず0秒とする。
    result["schedule_offset_sec"] = result["arrival_sec"] - result["scheduled_sec"]
    result["early_sec"] = (-result["schedule_offset_sec"]).clip(lower=0)
    result["delay_sec"] = result["schedule_offset_sec"].clip(lower=0)
    return result


def mark_partial_run(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    key = "service_run_id" if "service_run_id" in result else "run_id"
    result["途中参加"] = result.groupby(key)["stop_order"].transform("min") > 1
    return result
