#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
LABEL_ORDER = ["left", "center-left", "center", "center-right", "right"]
LABEL_PALETTE = ["#34558B", "#7BAEBC", "#B8B4AE", "#DFA45B", "#B85C5A"]
LABEL_PALETTE_MAP = dict(zip(LABEL_ORDER, LABEL_PALETTE))
BOUNDARIES = [-0.8, -0.1, 0.1, 0.8]
STANCE_REGIONS = [
    (-1.0, -0.8, "left"),
    (-0.8, -0.1, "center-left"),
    (-0.1, 0.1, "center"),
    (0.1, 0.8, "center-right"),
    (0.8, 1.0, "right"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--politics-file",
        type=Path,
        default=ROOT / "stance_score" / "political-news_stance_score.json",
    )
    parser.add_argument(
        "--entertainment-file",
        type=Path,
        default=ROOT / "stance_score" / "entertainment_stance_score.json",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    return parser.parse_args()


def apply_nature_style() -> None:
    sns.set_theme(style="ticks")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7.8,
            "axes.labelsize": 8.2,
            "axes.titlesize": 8.8,
            "xtick.labelsize": 7.2,
            "ytick.labelsize": 7.2,
            "legend.fontsize": 7.1,
            "axes.linewidth": 0.82,
            "axes.edgecolor": "#272727",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.unicode_minus": False,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "legend.frameon": False,
        }
    )


def load_data(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(path)
    rows: list[dict[str, object]] = []
    for video_id, record in data.items():
        if not isinstance(record, dict):
            continue
        rows.append(
            {
                "video_id": str(video_id),
                "stance_label": str(record.get("stance_label", "")).strip(),
                "stance_score": pd.to_numeric(record.get("stance_score"), errors="coerce"),
                "confidence": pd.to_numeric(record.get("confidence"), errors="coerce"),
            }
        )
    frame = pd.DataFrame(rows)
    frame = frame[frame["stance_label"].isin(LABEL_ORDER)].copy()
    frame = frame.drop_duplicates(subset=["video_id"], keep="last").reset_index(drop=True)
    return frame


def style_axis(ax: plt.Axes, grid_axis: str | None = "y") -> None:
    ax.grid(False)
    if grid_axis:
        ax.grid(True, axis=grid_axis, color="#E6E6E6", linewidth=0.55, alpha=0.78)
    ax.set_axisbelow(True)
    ax.tick_params(direction="out", width=0.72, length=2.8, color="#272727", pad=2)
    for side in ["left", "bottom"]:
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color("#272727")
        ax.spines[side].set_linewidth(0.82)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.105,
        1.035,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.5,
        fontweight="bold",
        color="#272727",
    )


def draw_stance_boundaries(ax: plt.Axes) -> None:
    for boundary in BOUNDARIES:
        ax.axvline(boundary, ls="--", lw=0.68, color="#6B6B6B", alpha=0.72, zorder=1)


def shade_stance_regions(ax: plt.Axes) -> None:
    for left, right, label in STANCE_REGIONS:
        ax.axvspan(left, right, color=LABEL_PALETTE_MAP[label], alpha=0.08, lw=0, zorder=0)


def format_legend(ax: plt.Axes) -> None:
    legend = ax.legend(title="Label", fontsize=7.3, title_fontsize=8.1, loc="lower right", frameon=True)
    if legend is None:
        return
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_alpha(0.82)
    legend.get_frame().set_edgecolor("#D8D8D8")
    legend.get_frame().set_linewidth(0.65)


def annotate_bars(ax: plt.Axes, values: pd.Series, total: int) -> None:
    maximum = max(values.max(), 1)
    ax.set_xlim(0, maximum * 1.28)
    for index, value in enumerate(values):
        percentage = 100 * value / total if total else 0
        ax.text(
            value + maximum * 0.025,
            index,
            f"{value:,} ({percentage:.1f}%)",
            ha="left",
            va="center",
            fontsize=7.0,
        )


def plot_label_distribution(ax: plt.Axes, frame: pd.DataFrame) -> None:
    counts = frame["stance_label"].value_counts().reindex(LABEL_ORDER, fill_value=0)
    positions = np.arange(len(LABEL_ORDER))
    ax.barh(
        positions,
        counts.values,
        color=[LABEL_PALETTE_MAP[label] for label in LABEL_ORDER],
        edgecolor="#272727",
        linewidth=0.45,
        height=0.62,
    )
    ax.set_yticks(positions)
    ax.set_yticklabels(LABEL_ORDER)
    ax.invert_yaxis()
    annotate_bars(ax, counts, len(frame))
    ax.set_xlabel("Number of videos")
    ax.set_ylabel("")
    ax.set_title("Stance-label composition")
    add_panel_label(ax, "(a)")
    style_axis(ax, grid_axis="x")


def plot_distribution(ax: plt.Axes, frame: pd.DataFrame) -> None:
    sns.histplot(
        frame["stance_score"].dropna(),
        bins=44,
        kde=True,
        ax=ax,
        color="#34558B",
        edgecolor="white",
        linewidth=0.18,
        alpha=0.70,
    )
    shade_stance_regions(ax)
    draw_stance_boundaries(ax)
    ax.set_xlim(-1.05, 1.05)
    ax.set_xlabel("Stance score")
    ax.set_ylabel("Frequency")
    ax.set_title("Stance score distribution")
    add_panel_label(ax, "(b)")
    style_axis(ax)


def plot_confidence_ecdf(ax: plt.Axes, frame: pd.DataFrame) -> None:
    for label in LABEL_ORDER:
        values = frame.loc[frame["stance_label"] == label, "confidence"].dropna().sort_values().to_numpy()
        if values.size == 0:
            continue
        cumulative = np.arange(1, values.size + 1) / values.size
        ax.plot(values, cumulative, color=LABEL_PALETTE_MAP[label], lw=1.35, alpha=0.95, label=label)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Confidence")
    ax.set_ylabel("Cumulative fraction")
    ax.set_title("Confidence by stance label")
    add_panel_label(ax, "(c)")
    style_axis(ax)
    format_legend(ax)


def plot_score_confidence_scatter(ax: plt.Axes, frame: pd.DataFrame) -> None:
    scatter_data = frame.sample(n=min(len(frame), 16000), random_state=7) if len(frame) > 16000 else frame
    sns.scatterplot(
        data=scatter_data,
        x="stance_score",
        y="confidence",
        hue="stance_label",
        hue_order=LABEL_ORDER,
        s=8,
        alpha=0.20,
        linewidth=0,
        edgecolor=None,
        palette=LABEL_PALETTE_MAP,
        ax=ax,
        rasterized=True,
    )
    shade_stance_regions(ax)
    draw_stance_boundaries(ax)
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Stance score")
    ax.set_ylabel("Confidence")
    ax.set_title("Score vs confidence")
    add_panel_label(ax, "(d)")
    style_axis(ax, grid_axis=None)
    legend = ax.get_legend()
    if legend is not None:
        legend.remove()


def save_figure(figure: plt.Figure, output_stem: Path) -> None:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".png"), dpi=600, bbox_inches="tight", pad_inches=0.035)
    figure.savefig(output_stem.with_suffix(".pdf"), dpi=600, bbox_inches="tight", pad_inches=0.035)
    figure.savefig(
        output_stem.with_suffix(".tiff"),
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.035,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(figure)


def plot_overview(frame: pd.DataFrame, output_stem: Path) -> None:
    figure = plt.figure(figsize=(7.25, 5.55), dpi=300, constrained_layout=False)
    grid = figure.add_gridspec(
        2,
        3,
        width_ratios=[1.12, 1.25, 1.0],
        height_ratios=[1.0, 1.0],
        wspace=0.55,
        hspace=0.55,
    )
    label_axis = figure.add_subplot(grid[:, 0])
    score_axis = figure.add_subplot(grid[0, 1:])
    confidence_axis = figure.add_subplot(grid[1, 1])
    scatter_axis = figure.add_subplot(grid[1, 2])
    plot_label_distribution(label_axis, frame)
    plot_distribution(score_axis, frame)
    plot_confidence_ecdf(confidence_axis, frame)
    plot_score_confidence_scatter(scatter_axis, frame)
    figure.subplots_adjust(left=0.08, right=0.985, top=0.94, bottom=0.11)
    save_figure(figure, output_stem)


def main() -> None:
    args = parse_args()
    for path in (args.politics_file, args.entertainment_file):
        if not path.exists():
            raise FileNotFoundError(path)
    politics = load_data(args.politics_file)
    entertainment = load_data(args.entertainment_file)
    apply_nature_style()
    plot_overview(politics, args.output_dir / "figureS7")
    plot_overview(entertainment, args.output_dir / "figureS8")
    print(f"figureS7 records: {len(politics)}")
    print(f"figureS8 records: {len(entertainment)}")
    print(args.output_dir / "figureS7")
    print(args.output_dir / "figureS8")


if __name__ == "__main__":
    main()
