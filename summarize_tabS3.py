#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--politics-file", type=Path, default=DATA_DIR / "political-news_data.xlsx")
    parser.add_argument("--entertainment-file", type=Path, default=DATA_DIR / "entertainment_data.xlsx")
    parser.add_argument("--output-file", type=Path, default=SCRIPT_DIR / "tabS3.csv")
    return parser.parse_args()


def parse_json_tolerant(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, float) and np.isnan(value):
        return default
    text = str(value).strip()
    if not text:
        return default
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(text)
        except Exception:
            pass
    normalized = text.replace("'", '"').replace("True", "true").replace("False", "false").replace("None", "null")
    try:
        return json.loads(normalized)
    except Exception:
        return default


def parse_exposure_video_ids(value: Any) -> set[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    candidates: list[str] = []
    if text.startswith("[") and text.endswith("]"):
        candidates.append(text)
        inner = text
        while inner.startswith("[") and inner.endswith("]"):
            inner = inner[1:-1].strip()
        if inner:
            candidates.append("[" + inner + "]")
    else:
        candidates.extend(("[" + text + "]", text))
    parsed = None
    for candidate in candidates:
        parsed = parse_json_tolerant(candidate, None)
        if parsed is not None:
            break
    if parsed is None:
        return set()
    video_ids: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            video_id = node.get("id")
            if video_id:
                video_ids.add(str(video_id))
            for child in node.values():
                if isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(parsed)
    return video_ids


def extract_alpha(file_name: Any, group_name: Any) -> float:
    for value in (file_name, group_name):
        text = str(value)
        match = re.search(r"Test_(\d+\.?\d*)_", text)
        if match:
            return float(match.group(1))
        match = re.search(r"couplingRatio_(\d+\.?\d*)", text)
        if match:
            return float(match.group(1))
    return float("nan")


def load_data(path: Path) -> pd.DataFrame:
    columns = [
        "step",
        "master_exposure_last",
        "servant_exposure_last",
        "File Name",
        "Group Name",
    ]
    frame = pd.read_excel(path, sheet_name="data", usecols=columns)
    frame["alpha"] = [
        extract_alpha(file_name, group_name)
        for file_name, group_name in zip(frame["File Name"], frame["Group Name"])
    ]
    frame = frame.dropna(subset=["alpha"]).copy()
    frame["alpha"] = pd.to_numeric(frame["alpha"], errors="coerce")
    return frame


def count_bot_pairs(frame: pd.DataFrame) -> int:
    total = 0
    for _, bot_frame in frame.groupby("File Name", sort=False):
        steps = pd.to_numeric(bot_frame["step"], errors="coerce")
        total += max(1, int((steps == 0).sum()))
    return total


def count_unique_videos(frame: pd.DataFrame, column: str) -> int:
    video_ids: set[str] = set()
    for value in frame[column].dropna():
        video_ids.update(parse_exposure_video_ids(value))
    return len(video_ids)


def summarize(path: Path, preference: str, category_id: int) -> pd.DataFrame:
    frame = load_data(path)
    rows: list[dict[str, Any]] = []
    for alpha, group in frame.groupby("alpha", sort=True):
        rows.append(
            {
                "Preference condition": preference,
                "Preferred category ID": category_id,
                "Behavioral consistency, alpha": float(alpha),
                "Number of bot-pair records": count_bot_pairs(group),
                "Unique videos, Account A": count_unique_videos(group, "master_exposure_last"),
                "Unique videos, Account B": count_unique_videos(group, "servant_exposure_last"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    for path in (args.politics_file, args.entertainment_file):
        if not path.exists():
            raise FileNotFoundError(path)
    result = pd.concat(
        [
            summarize(args.politics_file, "Political news", 25),
            summarize(args.entertainment_file, "Entertainment", 24),
        ],
        ignore_index=True,
    )
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_file, index=False, encoding="utf-8-sig")
    print(args.output_file)


if __name__ == "__main__":
    main()
