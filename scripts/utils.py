import pandas as pd


def normalize_time(value):
    """
    HTMLから取得した時刻を HH:MM に変換する

    入力例
    ----------------
    600
    600.0
    "600"
    "0600"
    "06:00"
    "｜"
    ""

    出力
    ----------------
    "06:00"
    None
    """

    if pd.isna(value):
        return None

    text = str(value).strip()

    if text in ("", "｜", "-", "nan"):
        return None

    # 600.0 → 600
    if text.endswith(".0"):
        text = text[:-2]

    # 06:00 → 0600
    if ":" in text:
        hh, mm = text.split(":")
        text = hh.zfill(2) + mm.zfill(2)

    # 600 → 0600
    if len(text) == 3:
        text = "0" + text

    # 4桁以外は不正
    if len(text) != 4:
        return None

    return f"{text[:2]}:{text[2:]}"


def is_time(value):
    """
    時刻セルか判定
    """

    return normalize_time(value) is not None
