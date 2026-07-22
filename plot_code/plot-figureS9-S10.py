#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--politics-data",
        type=Path,
        default=ROOT / "data" / "political-news_data.xlsx",
    )
    parser.add_argument(
        "--entertainment-data",
        type=Path,
        default=ROOT / "data" / "entertainment_data.xlsx",
    )
    parser.add_argument(
        "--politics-stance",
        type=Path,
        default=ROOT / "stance_score" / "political-news_stance_score.json",
    )
    parser.add_argument(
        "--entertainment-stance",
        type=Path,
        default=ROOT / "stance_score" / "entertainment_stance_score.json",
    )
    parser.add_argument("--alphas", default="0.0,0.3,0.7,1.0")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    return parser.parse_args()


def parse_json(value: Any, default: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    if isinstance(value, (list, dict)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        try:
            return ast.literal_eval(text)
        except Exception:
            return default


def parse_exposure_ids(value: Any) -> list[str]:
    data = parse_json(value, [])
    if isinstance(data, dict):
        data = list(data.values())
    if not isinstance(data, list):
        return []
    return [str(item["id"]) for item in data if isinstance(item, dict) and item.get("id")]


def alpha_from_row(row: pd.Series) -> float:
    for column in ("Group Name", "File Name", "Bot Name"):
        text = str(row.get(column, ""))
        match = re.search(r"couplingRatio_([0-9.]+)", text)
        if match:
            return float(match.group(1))
        match = re.search(r"Dual_Test_([0-9.]+)_Bot", text)
        if match:
            return float(match.group(1))
    return float("nan")


def load_score_map(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(path)
    scores: dict[str, float] = {}
    for video_id, record in data.items():
        if not isinstance(record, dict):
            continue
        try:
            scores[str(video_id)] = float(record["stance_score"])
        except Exception:
            pass
    return scores


def mean_score(video_ids: list[str], score_map: dict[str, float]) -> float:
    values = [score_map[video_id] for video_id in video_ids if video_id in score_map]
    return float(np.mean(values)) if values else float("nan")


def calculate_step_scores(data_path: Path, stance_path: Path) -> pd.DataFrame:
    frame = pd.read_excel(
        data_path,
        sheet_name="data",
        usecols=[
            "Group Name",
            "File Name",
            "Bot Name",
            "step",
            "master_exposure_last",
            "servant_exposure_last",
        ],
    )
    score_map = load_score_map(stance_path)
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "Group Name": row.get("Group Name", ""),
                "Bot Name": row.get("Bot Name", ""),
                "step": pd.to_numeric(row.get("step"), errors="coerce"),
                "alpha": alpha_from_row(row),
                "master_mean_score": mean_score(
                    parse_exposure_ids(row.get("master_exposure_last")), score_map
                ),
                "servant_mean_score": mean_score(
                    parse_exposure_ids(row.get("servant_exposure_last")), score_map
                ),
            }
        )
    return pd.DataFrame(rows).dropna(subset=["step", "alpha"]).reset_index(drop=True)


def aggregate_step_scores(step_scores: pd.DataFrame, alphas: list[float]) -> pd.DataFrame:
    alpha_values = step_scores["alpha"].to_numpy(dtype=float)
    selected = np.isclose(alpha_values[:, None], np.asarray(alphas)[None, :], atol=1e-9).any(axis=1)
    long_frame = step_scores.loc[selected].melt(
        id_vars=["alpha", "step", "Group Name", "Bot Name"],
        value_vars=["master_mean_score", "servant_mean_score"],
        var_name="side",
        value_name="score",
    )
    long_frame["side"] = long_frame["side"].map(
        {"master_mean_score": "Account A", "servant_mean_score": "Account B"}
    )
    aggregate = (
        long_frame.dropna(subset=["score"])
        .groupby(["alpha", "step", "side"], as_index=False)["score"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    aggregate["sem"] = aggregate["std"] / np.sqrt(aggregate["count"].clip(lower=1))
    return aggregate


def calculate_dataset(data_path: Path, stance_path: Path, alphas: list[float]) -> pd.DataFrame:
    return aggregate_step_scores(calculate_step_scores(data_path, stance_path), alphas)


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 9,
            "axes.labelsize": 10.5,
            "axes.titlesize": 10.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.linewidth": 0.9,
            "axes.edgecolor": "#222222",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "xtick.major.width": 0.85,
            "ytick.major.width": 0.85,
            "xtick.major.size": 3.5,
            "ytick.major.size": 3.5,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": "tight",
        }
    )


def save_figure(figure: plt.Figure, output_stem: Path) -> None:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    figure.savefig(output_stem.with_suffix(".pdf"), dpi=600, bbox_inches="tight")
    figure.savefig(
        output_stem.with_suffix(".tiff"),
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(figure)


def plot_gemini_curves(aggregate: pd.DataFrame, alphas: list[float], output_stem: Path) -> None:
    set_plot_style()
    figure, axes = plt.subplots(
        2,
        2,
        figsize=(8.2, 5.6),
        dpi=320,
        sharex=False,
        sharey=True,
        squeeze=False,
    )
    color_map = {"Account A": "#4F6FA8", "Account B": "#D99A2B"}
    marker_map = {"Account A": "o", "Account B": "s"}
    panel_labels = ["(a)", "(b)", "(c)", "(d)"]
    y_values = aggregate["mean"].to_numpy(dtype=float)
    y_values = y_values[~np.isnan(y_values)]
    if len(y_values):
        lower = float(np.quantile(y_values, 0.02))
        upper = float(np.quantile(y_values, 0.98))
        padding = max(0.05, (upper - lower) * 0.2)
        y_minimum, y_maximum = lower - padding, upper + padding
    else:
        y_minimum, y_maximum = -1.0, 1.0
    for panel_index, axis in enumerate(axes.flatten()):
        alpha = alphas[panel_index]
        subset = aggregate[np.isclose(aggregate["alpha"], alpha)]
        for side in ("Account A", "Account B"):
            side_data = subset[subset["side"] == side].sort_values("step")
            if side_data.empty:
                continue
            x = side_data["step"].to_numpy(dtype=float)
            mean = side_data["mean"].to_numpy(dtype=float)
            sem = side_data["sem"].fillna(0.0).to_numpy(dtype=float)
            axis.plot(
                x,
                mean,
                color=color_map[side],
                linewidth=1.65,
                marker=marker_map[side],
                markersize=3.2,
                markeredgewidth=0.0,
                markeredgecolor=color_map[side],
                alpha=0.95,
                label=side,
                zorder=3,
            )
            axis.fill_between(
                x,
                mean - sem,
                mean + sem,
                color=color_map[side],
                alpha=0.12,
                linewidth=0,
                zorder=2,
            )
        axis.set_title(rf"$\alpha={alpha:.1f}$", pad=8)
        axis.set_xlabel("Step")
        axis.grid(True, color="#D8D8D8", linewidth=0.55, alpha=0.72)
        axis.set_axisbelow(True)
        axis.tick_params(direction="out")
        axis.text(
            0.02,
            0.98,
            panel_labels[panel_index],
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=11,
            fontweight="bold",
        )
        for spine in axis.spines.values():
            spine.set_visible(True)
            spine.set_color("#222222")
            spine.set_linewidth(0.9)
        if panel_index in (0, 2):
            axis.set_ylabel("Mean stance score")
        if panel_index == 0:
            legend = axis.legend(
                title="Mean ± SEM",
                loc="upper right",
                frameon=True,
                handlelength=1.8,
                borderpad=0.35,
                labelspacing=0.35,
            )
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_alpha(0.82)
            legend.get_frame().set_edgecolor("#D6D6D6")
            legend.get_frame().set_linewidth(0.7)
        axis.set_ylim(y_minimum, y_maximum)
    figure.tight_layout(rect=[0.0, 0.0, 1.0, 0.96], w_pad=1.1, h_pad=1.3)
    figure.text(0.012, 0.985, "Gemini", ha="left", va="top", fontsize=12.5, fontweight="bold")
    save_figure(figure, output_stem)


def main() -> None:
    args = parse_args()
    inputs = (
        args.politics_data,
        args.entertainment_data,
        args.politics_stance,
        args.entertainment_stance,
    )
    for path in inputs:
        if not path.exists():
            raise FileNotFoundError(path)
    alphas = [float(value.strip()) for value in args.alphas.split(",") if value.strip()]
    if len(alphas) != 4:
        raise ValueError("Exactly four alpha values are required")
    politics = calculate_dataset(args.politics_data, args.politics_stance, alphas)
    entertainment = calculate_dataset(args.entertainment_data, args.entertainment_stance, alphas)
    plot_gemini_curves(politics, alphas, args.output_dir / "figureS9")
    plot_gemini_curves(entertainment, alphas, args.output_dir / "figureS10")
    print(f"figureS9 aggregate rows: {len(politics)}")
    print(f"figureS10 aggregate rows: {len(entertainment)}")
    print(args.output_dir / "figureS9")
    print(args.output_dir / "figureS10")


if __name__ == "__main__":
    main()
