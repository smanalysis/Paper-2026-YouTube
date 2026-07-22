#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_DIR = SCRIPT_DIR / "figures"

ALPHA_PATTERNS = [
    re.compile(r"couplingRatio[_-]?([0-9]*\.?[0-9]+)", re.IGNORECASE),
    re.compile(r"Dual_Test_([0-9]*\.?[0-9]+)", re.IGNORECASE),
    re.compile(r"Test_([0-9]*\.?[0-9]+)", re.IGNORECASE),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--politics-file", type=Path, default=DATA_DIR / "political-news_data.xlsx")
    parser.add_argument("--entertainment-file", type=Path, default=DATA_DIR / "entertainment_data.xlsx")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--band", choices=["std", "sem"], default="std")
    return parser.parse_args()


def load_table(path: Path) -> pd.DataFrame:
    columns = [
        "step",
        "master_exposure_last",
        "servant_exposure_last",
        "[CATEGORY]",
        "File Name",
        "Group Name",
        "Bot Name",
    ]
    return pd.read_excel(path, sheet_name="data", usecols=columns)


def parse_json_like(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
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


def parse_exposure_items(value: Any) -> list[dict[str, Any]]:
    parsed = parse_json_like(value, [])
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def parse_category_map(value: Any) -> dict[str, int]:
    parsed = parse_json_like(value, {})
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, int] = {}
    for key, category in parsed.items():
        video_id = str(key).strip()
        if not video_id:
            continue
        try:
            result[video_id] = int(category)
        except Exception:
            pass
    return result


def item_video_id(item: dict[str, Any]) -> str | None:
    value = item.get("id")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_alpha(row: pd.Series) -> float | None:
    for column in ("Group Name", "File Name", "Bot Name"):
        text = str(row.get(column, "") or "")
        for pattern in ALPHA_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            try:
                alpha = float(match.group(1))
            except Exception:
                continue
            if 0.0 <= alpha <= 1.0:
                return round(alpha, 6)
    return None


def compute_preference_metrics(df: pd.DataFrame, dataset: str, preferred_category: int) -> pd.DataFrame:
    work = df.copy().reset_index(drop=True)
    work["row_id"] = np.arange(len(work))
    work["step"] = pd.to_numeric(work["step"], errors="coerce")
    work["alpha"] = work.apply(extract_alpha, axis=1)
    work = work.dropna(subset=["step", "alpha"]).copy()
    work["step"] = work["step"].astype(int)
    work["alpha"] = work["alpha"].astype(float)
    work["Bot Name"] = work["Bot Name"].astype(str)
    work = work.sort_values(["alpha", "Bot Name", "row_id"]).copy()
    work["run_index"] = work.groupby(["alpha", "Bot Name"], sort=False)["step"].transform(
        lambda values: (values == 0).astype(int).cumsum()
    )
    work["bot_run"] = work["Bot Name"] + "#run" + work["run_index"].astype(str)
    rows: list[dict[str, Any]] = []
    for _, row in work.iterrows():
        master_items = parse_exposure_items(row["master_exposure_last"])
        servant_items = parse_exposure_items(row["servant_exposure_last"])
        category_map = parse_category_map(row["[CATEGORY]"])
        master_videos = {video_id for item in master_items if (video_id := item_video_id(item))}
        servant_videos = {video_id for item in servant_items if (video_id := item_video_id(item))}
        master_preferred = {
            video_id
            for item in master_items
            if (video_id := item_video_id(item)) and category_map.get(video_id) == preferred_category
        }
        servant_preferred = {
            video_id
            for item in servant_items
            if (video_id := item_video_id(item)) and category_map.get(video_id) == preferred_category
        }
        rows.append(
            {
                "dataset": dataset,
                "alpha": row["alpha"],
                "step": row["step"],
                "bot_run": row["bot_run"],
                "account_a_pref_share": len(master_preferred) / len(master_videos) if master_videos else np.nan,
                "account_b_pref_share": len(servant_preferred) / len(servant_videos) if servant_videos else np.nan,
            }
        )
    return pd.DataFrame(rows)


def aggregate_metrics(metrics: pd.DataFrame, band: str) -> pd.DataFrame:
    value_columns = ["account_a_pref_share", "account_b_pref_share"]
    grouped = metrics.groupby(["dataset", "alpha", "step"], as_index=False)
    aggregated = grouped.agg(
        n_bot_runs=("bot_run", "nunique"),
        **{f"{column}_mean": (column, "mean") for column in value_columns},
        **{f"{column}_std": (column, "std") for column in value_columns},
        **{f"{column}_count": (column, "count") for column in value_columns},
    )
    for column in value_columns:
        standard_deviation = aggregated[f"{column}_std"].fillna(0.0)
        count = aggregated[f"{column}_count"].clip(lower=1)
        aggregated[f"{column}_band"] = (
            standard_deviation / np.sqrt(count) if band == "sem" else standard_deviation
        )
    return aggregated.sort_values(["dataset", "alpha", "step"]).reset_index(drop=True)


def set_nature_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "custom",
            "mathtext.rm": "Times New Roman",
            "mathtext.it": "Times New Roman:italic",
            "mathtext.bf": "Times New Roman:bold",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#202020",
            "axes.linewidth": 1.05,
            "axes.labelsize": 9.5,
            "axes.titlesize": 10.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.5,
            "axes.unicode_minus": False,
        }
    )


def alpha_label(alpha: float) -> str:
    return rf"$\alpha={alpha:.1f}$"


def style_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#E1E1E1", linewidth=0.62, alpha=0.82)
    ax.tick_params(direction="out", length=3.0, width=0.9, color="#202020", pad=2)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#202020")
        spine.set_linewidth(1.05)


def panel_ylim(panel_data: list[np.ndarray]) -> tuple[float, float]:
    if not panel_data:
        return -0.02, 0.5
    values = np.concatenate(panel_data)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return -0.02, 0.5
    minimum = float(np.nanmin(values))
    maximum = float(np.nanmax(values))
    span = max(1e-6, maximum - minimum)
    lower = max(-0.02, minimum - 0.08 * span)
    upper = min(1.0, maximum + 0.18 * span)
    if upper - lower < 0.08:
        midpoint = (upper + lower) / 2
        lower = max(-0.02, midpoint - 0.04)
        upper = min(1.0, midpoint + 0.04)
    return lower, upper


def plot_preference_share(
    aggregated: pd.DataFrame,
    dataset: str,
    metric: str,
    title: str,
    output_stem: Path,
    band: str,
) -> None:
    set_nature_style()
    alphas = sorted(aggregated.loc[aggregated["dataset"] == dataset, "alpha"].dropna().unique().tolist())
    if not alphas:
        raise ValueError(dataset)
    n_alpha = len(alphas)
    ncols = 4 if n_alpha >= 8 else (3 if n_alpha >= 5 else 2)
    nrows = math.ceil(n_alpha / ncols)
    figure_width = 9.4 if ncols == 4 else 7.2
    figure_height = max(2.35 * nrows + 0.65, 3.8)
    figure, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(figure_width, figure_height),
        dpi=320,
        squeeze=False,
        sharex=False,
        sharey=False,
    )
    flat_axes = axes.flatten()
    all_values: list[np.ndarray] = []
    for alpha in alphas:
        data = aggregated[
            (aggregated["dataset"] == dataset) & np.isclose(aggregated["alpha"], alpha)
        ].sort_values("step")
        mean = data[f"{metric}_mean"].to_numpy(dtype=float)
        error = data[f"{metric}_band"].fillna(0.0).to_numpy(dtype=float)
        all_values.append(np.concatenate([mean - error, mean + error]))
    shared_limits = panel_ylim(all_values)
    for index, alpha in enumerate(alphas):
        ax = flat_axes[index]
        data = aggregated[
            (aggregated["dataset"] == dataset) & np.isclose(aggregated["alpha"], alpha)
        ].sort_values("step")
        x = data["step"].to_numpy(dtype=float)
        mean = data[f"{metric}_mean"].to_numpy(dtype=float)
        error = data[f"{metric}_band"].fillna(0.0).to_numpy(dtype=float)
        band_handle = ax.fill_between(
            x,
            mean - error,
            mean + error,
            color="#2E7194",
            alpha=0.16,
            linewidth=0.0,
            zorder=1,
        )
        line_handle = ax.plot(
            x,
            mean,
            color="#2E7194",
            linewidth=1.55,
            solid_capstyle="round",
            zorder=2,
        )[0]
        ax.set_title(alpha_label(alpha), pad=3.5, fontsize=8.6, fontweight="bold")
        ax.set_xlabel(r"Step, $t$", fontsize=7.8, labelpad=1.5)
        ax.set_ylabel("Preference share", fontsize=7.8, labelpad=2.0)
        ax.set_ylim(*shared_limits)
        style_axis(ax)
        ax.tick_params(labelsize=7.1, length=2.8, width=0.75)
        for spine in ax.spines.values():
            spine.set_linewidth(0.85)
        if index == 0:
            legend = ax.legend(
                [line_handle, band_handle],
                ["Mean", f"±1 {band.upper()}"],
                loc="upper right",
                frameon=True,
                fontsize=6.8,
                handlelength=1.5,
                borderpad=0.25,
            )
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_alpha(0.72)
            legend.get_frame().set_edgecolor("#D6D6D6")
            legend.get_frame().set_linewidth(0.6)
    for index in range(n_alpha, len(flat_axes)):
        flat_axes[index].axis("off")
    all_steps = aggregated.loc[aggregated["dataset"] == dataset, "step"].dropna().to_numpy(dtype=float)
    if all_steps.size:
        minimum_step = math.floor(float(np.nanmin(all_steps)))
        maximum_step = math.ceil(float(np.nanmax(all_steps)))
        for ax in flat_axes[:n_alpha]:
            ax.set_xlim(minimum_step - 2, maximum_step + 2)
            if maximum_step >= 100:
                ax.set_xticks([0, 50, 100, 150])
            else:
                ax.set_xticks(np.linspace(max(0, minimum_step), maximum_step, 4).round().astype(int))
    figure.suptitle(title, fontsize=11.2, fontweight="bold", y=0.995)
    figure.tight_layout(rect=[0.0, 0.0, 1.0, 0.955], pad=0.35, w_pad=0.45, h_pad=0.60)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".png"), dpi=600, bbox_inches="tight", pad_inches=0.03)
    figure.savefig(output_stem.with_suffix(".pdf"), dpi=600, bbox_inches="tight", pad_inches=0.03)
    figure.savefig(
        output_stem.with_suffix(".tiff"),
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.03,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(figure)


def main() -> None:
    args = parse_args()
    for path in (args.politics_file, args.entertainment_file):
        if not path.exists():
            raise FileNotFoundError(path)
    politics = compute_preference_metrics(load_table(args.politics_file), "Politics", 25)
    entertainment = compute_preference_metrics(load_table(args.entertainment_file), "Entertainment", 24)
    metrics = pd.concat([politics, entertainment], ignore_index=True)
    aggregated = aggregate_metrics(metrics, args.band)
    specifications = [
        ("Politics", "account_a_pref_share", "Politics preference evolution, Account A", "figureS3"),
        ("Politics", "account_b_pref_share", "Politics preference evolution, Account B", "figureS4"),
        (
            "Entertainment",
            "account_a_pref_share",
            "Entertainment preference evolution, Account A",
            "figureS5",
        ),
        (
            "Entertainment",
            "account_b_pref_share",
            "Entertainment preference evolution, Account B",
            "figureS6",
        ),
    ]
    for dataset, metric, title, file_name in specifications:
        plot_preference_share(aggregated, dataset, metric, title, args.output_dir / file_name, args.band)
    for _, _, _, file_name in specifications:
        print(args.output_dir / file_name)


if __name__ == "__main__":
    main()
