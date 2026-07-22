from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

YOUTUBE_CATEGORY_NAMES = {
    1: "Film & Animation",
    2: "Autos & Vehicles",
    10: "Music",
    15: "Pets & Animals",
    17: "Sports",
    19: "Travel & Events",
    20: "Gaming",
    22: "People & Blogs",
    23: "Comedy",
    24: "Entertainment",
    25: "News & Politics",
    26: "Howto & Style",
    27: "Education",
    28: "Science & Technology",
    29: "Nonprofits & Activism",
}

CATEGORY_COLORS = {
    25: "#4E79A7",
    24: "#E15759",
    22: "#F28E2B",
    27: "#59A14F",
    28: "#EDC948",
    17: "#B07AA1",
    1: "#FF9DA7",
    10: "#9C755F",
    23: "#BAB0AC",
    19: "#86BCB6",
    2: "#A0CBE8",
    26: "#FFBE7D",
    29: "#8CD17D",
    15: "#D4A6C8",
    20: "#B6992D",
    "Other": "#8A8A8A",
}

GROUP_SPECS = [
    ("Politics", "Account A", "Politics\nAccount A"),
    ("Politics", "Account B", "Politics\nAccount B"),
    ("Entertainment", "Account A", "Entertainment\nAccount A"),
    ("Entertainment", "Account B", "Entertainment\nAccount B"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--politics-file", type=Path, default=ROOT / "data" / "political-news_data.xlsx")
    parser.add_argument("--entertainment-file", type=Path, default=ROOT / "data" / "entertainment_data.xlsx")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    parser.add_argument("--prefix", type=str, default="figureS2")
    parser.add_argument("--min-plot-proportion", type=float, default=0.025)
    parser.add_argument("--fig-width", type=float, default=7.25)
    parser.add_argument("--fig-height", type=float, default=3.35)
    return parser.parse_args()


def set_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.linewidth": 0.9,
            "axes.edgecolor": "#202020",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "figure.dpi": 320,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


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


def parse_exposure_ids(value: Any) -> set[str]:
    parsed = parse_json_like(value, [])
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return set()
    return {
        str(item["id"]).strip()
        for item in parsed
        if isinstance(item, dict) and item.get("id") and str(item["id"]).strip()
    }


def parse_category_map(value: Any) -> dict[str, int]:
    parsed = parse_json_like(value, {})
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, int] = {}
    for key, category in parsed.items():
        try:
            result[str(key)] = int(float(category))
        except Exception:
            continue
    return result


def build_shared_category_map(tables: list[pd.DataFrame]) -> dict[str, int]:
    category_map: dict[str, int] = {}
    for table in tables:
        if "[CATEGORY]" not in table.columns:
            raise ValueError("Input data lack [CATEGORY].")
        for value in table["[CATEGORY]"]:
            for video_id, category in parse_category_map(value).items():
                category_map.setdefault(video_id, category)
    return category_map


def category_label(category_id: Any) -> str:
    if category_id == "Other":
        return "Other"
    category = int(category_id)
    return f"{category} {YOUTUBE_CATEGORY_NAMES.get(category, 'Unknown category')}"


def calculate_domain_distributions(
    table: pd.DataFrame,
    dataset: str,
    shared_category_map: dict[str, int],
) -> dict[str, pd.DataFrame]:
    required = ["master_exposure_last", "servant_exposure_last", "[CATEGORY]"]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ValueError(f"{dataset} missing required columns: {missing}")
    side_ids: dict[str, set[str]] = defaultdict(set)
    for _, row in table.iterrows():
        side_ids["Account A"].update(parse_exposure_ids(row["master_exposure_last"]))
        side_ids["Account B"].update(parse_exposure_ids(row["servant_exposure_last"]))
    distributions: dict[str, pd.DataFrame] = {}
    for side in ("Account A", "Account B"):
        known_ids = [video_id for video_id in side_ids[side] if video_id in shared_category_map]
        counts = Counter(shared_category_map[video_id] for video_id in known_ids)
        total = sum(counts.values())
        distributions[side] = pd.DataFrame(
            [
                {
                    "dataset": dataset,
                    "side": side,
                    "category_id": category_id,
                    "category_label": category_label(category_id),
                    "unique_video_count": count,
                    "proportion": count / total if total else 0.0,
                }
                for category_id, count in counts.items()
            ]
        )
    return distributions


def collapse_small_categories(data: pd.DataFrame, threshold: float) -> pd.DataFrame:
    retained = data[data["proportion"] >= threshold].copy()
    small = data[data["proportion"] < threshold]
    if not small.empty:
        retained = pd.concat(
            [
                retained,
                pd.DataFrame(
                    [
                        {
                            "category_id": "Other",
                            "category_label": "Other",
                            "unique_video_count": int(small["unique_video_count"].sum()),
                            "proportion": float(small["proportion"].sum()),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    return retained.sort_values("unique_video_count", ascending=False)


def calculate_figure_data(args: argparse.Namespace) -> tuple[pd.DataFrame, list[Any]]:
    politics = pd.read_excel(
        args.politics_file,
        usecols=["master_exposure_last", "servant_exposure_last", "[CATEGORY]"],
    )
    entertainment = pd.read_excel(
        args.entertainment_file,
        usecols=["master_exposure_last", "servant_exposure_last", "[CATEGORY]"],
    )
    shared_category_map = build_shared_category_map([politics, entertainment])
    domain_data = {
        "Politics": calculate_domain_distributions(politics, "Politics", shared_category_map),
        "Entertainment": calculate_domain_distributions(entertainment, "Entertainment", shared_category_map),
    }
    rows: list[dict[str, Any]] = []
    totals: Counter[Any] = Counter()
    for dataset, side, panel_label in GROUP_SPECS:
        collapsed = collapse_small_categories(domain_data[dataset][side], args.min_plot_proportion)
        for _, row in collapsed.iterrows():
            category_id = row["category_id"]
            proportion = float(row["proportion"])
            rows.append(
                {
                    "dataset": dataset,
                    "side": side,
                    "panel_label": panel_label,
                    "category_id": category_id,
                    "category_label": row["category_label"],
                    "proportion": proportion,
                }
            )
            totals[category_id] += proportion
    category_order = [
        category_id
        for category_id, _ in sorted(
            totals.items(),
            key=lambda item: (item[0] == "Other", -item[1], str(item[0])),
        )
    ]
    return pd.DataFrame(rows), category_order


def text_color(fill: str) -> str:
    red, green, blue = mpl.colors.to_rgb(fill)
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "white" if luminance < 0.48 else "#202020"


def plot_figure(
    plot_data: pd.DataFrame,
    category_order: list[Any],
    args: argparse.Namespace,
) -> tuple[Path, Path, Path]:
    set_style()
    group_labels = [spec[2] for spec in GROUP_SPECS]
    y_positions = np.arange(len(group_labels))[::-1]
    y_lookup = dict(zip(group_labels, y_positions))
    label_lookup = plot_data.drop_duplicates("category_id").set_index("category_id")["category_label"].to_dict()
    fig, ax = plt.subplots(figsize=(args.fig_width, args.fig_height), dpi=320)
    left_by_group = {label: 0.0 for label in group_labels}
    for category_id in category_order:
        color = CATEGORY_COLORS.get(category_id, "#B8B8B8")
        for _, row in plot_data[plot_data["category_id"] == category_id].iterrows():
            label = row["panel_label"]
            width = float(row["proportion"]) * 100.0
            left = left_by_group[label]
            ax.barh(
                y_lookup[label],
                width,
                left=left,
                height=0.62,
                color=color,
                edgecolor="white",
                linewidth=0.55,
            )
            if width >= 7.0:
                ax.text(
                    left + width / 2,
                    y_lookup[label],
                    f"{width:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=7.2,
                    fontweight="bold",
                    color=text_color(color),
                )
            left_by_group[label] += width
    handles = [
        Patch(
            facecolor=CATEGORY_COLORS.get(category_id, "#B8B8B8"),
            edgecolor="none",
            label=label_lookup.get(category_id, str(category_id)),
        )
        for category_id in category_order
    ]
    ax.set_yticks(y_positions)
    ax.set_yticklabels(group_labels, fontsize=9.2, fontweight="bold")
    ax.set_xlim(0, 100)
    ax.set_xticks(np.arange(0, 101, 20))
    ax.set_xticklabels([f"{value}%" for value in range(0, 101, 20)])
    ax.set_xlabel("Category composition", fontsize=9.5, labelpad=5)
    ax.set_title("Video category composition", fontsize=10.5, fontweight="bold", pad=7)
    ax.grid(axis="x", color="#E3E3E3", linewidth=0.65)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=8.5, width=0.8, length=3.2)
    ax.tick_params(axis="y", width=0.8, length=0)
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=min(4, max(1, len(handles))),
        frameon=False,
        bbox_to_anchor=(0.5, 0.0),
        fontsize=7.6,
        handlelength=1.0,
        columnspacing=0.95,
        labelspacing=0.45,
    )
    fig.tight_layout(rect=[0.005, 0.23, 0.995, 0.995], pad=0.25)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / args.prefix
    png_path = output.with_suffix(".png")
    pdf_path = output.with_suffix(".pdf")
    tiff_path = output.with_suffix(".tiff")
    fig.savefig(png_path, dpi=600, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(pdf_path, dpi=600, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(
        tiff_path,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.02,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)
    return png_path, pdf_path, tiff_path


def main() -> None:
    args = parse_args()
    plot_data, category_order = calculate_figure_data(args)
    png_path, pdf_path, tiff_path = plot_figure(plot_data, category_order, args)
    print(f"[OK] PNG: {png_path}")
    print(f"[OK] PDF: {pdf_path}")
    print(f"[OK] TIFF: {tiff_path}")


if __name__ == "__main__":
    main()
