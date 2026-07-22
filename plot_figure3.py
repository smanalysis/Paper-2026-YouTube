from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
LABEL_ORDER = ["left", "center-left", "center", "center-right", "right"]
REQUIRED_COLUMNS = [
    "Group Name",
    "Bot Name",
    "step",
    "master_exposure_last",
    "servant_exposure_last",
    "[CATEGORY]",
]

PALETTE = {
    "time_politics": "#2F6F9F",
    "time_entertainment": "#D06A2C",
    "time_politics_band": "#DDEAF3",
    "time_entertainment_band": "#F6E2D3",
    "semantic_politics": "#5368B1",
    "semantic_entertainment": "#B45A84",
    "semantic_politics_band": "#E1E6F4",
    "semantic_entertainment_band": "#F1DCE6",
    "stance_politics": "#208A8A",
    "stance_entertainment": "#A85F3B",
    "stance_politics_band": "#DCEFEF",
    "stance_entertainment_band": "#F1E0D8",
    "ink": "#111111",
    "grid": "#E9ECEF",
}

PANEL_PALETTES = {
    "time": {
        "politics": PALETTE["time_politics"],
        "entertainment": PALETTE["time_entertainment"],
        "politics_band": PALETTE["time_politics_band"],
        "entertainment_band": PALETTE["time_entertainment_band"],
    },
    "semantic": {
        "politics": PALETTE["semantic_politics"],
        "entertainment": PALETTE["semantic_entertainment"],
        "politics_band": PALETTE["semantic_politics_band"],
        "entertainment_band": PALETTE["semantic_entertainment_band"],
    },
    "stance": {
        "politics": PALETTE["stance_politics"],
        "entertainment": PALETTE["stance_entertainment"],
        "politics_band": PALETTE["stance_politics_band"],
        "entertainment_band": PALETTE["stance_entertainment_band"],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--politics-input", type=Path, default=ROOT / "data" / "political-news_data.xlsx")
    parser.add_argument("--entertainment-input", type=Path, default=ROOT / "data" / "entertainment_data.xlsx")
    parser.add_argument("--politics-vectors", type=Path, default=ROOT / "vector_similarity" / "political-news_video_vectors_bge_m3.json")
    parser.add_argument("--entertainment-vectors", type=Path, default=ROOT / "vector_similarity" / "entertainment_video_vectors_bge_m3.json")
    parser.add_argument("--politics-stance", type=Path, default=ROOT / "stance_score" / "political-news_stance_score.json")
    parser.add_argument("--entertainment-stance", type=Path, default=ROOT / "stance_score" / "entertainment_stance_score.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    parser.add_argument("--prefix", type=str, default="figure3")
    parser.add_argument("--last-m", type=int, default=50)
    parser.add_argument("--fig-width", type=float, default=6.90)
    parser.add_argument("--fig-height", type=float, default=5.95)
    return parser.parse_args()


def set_figure_style() -> None:
    mpl.rcParams.update(
        {
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.family": "sans-serif",
            "mathtext.fontset": "dejavusans",
            "font.size": 8.8,
            "axes.labelsize": 10.4,
            "axes.titlesize": 10.0,
            "xtick.labelsize": 8.8,
            "ytick.labelsize": 8.8,
            "legend.fontsize": 8.2,
            "axes.linewidth": 1.05,
            "axes.edgecolor": PALETTE["ink"],
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.major.width": 1.0,
            "ytick.major.width": 1.0,
            "xtick.major.size": 3.6,
            "ytick.major.size": 3.6,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def parse_json(value: Any, default: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value).strip())
    except Exception:
        return default


def exposure_items(value: Any) -> list[dict[str, Any]]:
    data = parse_json(value, [])
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def exposure_ids(value: Any) -> list[str]:
    return [str(item["id"]) for item in exposure_items(value) if item.get("id")]


def category_map(value: Any) -> dict[str, int]:
    data = parse_json(value, {})
    if not isinstance(data, dict):
        return {}
    out: dict[str, int] = {}
    for key, val in data.items():
        try:
            out[str(key)] = int(val)
        except Exception:
            continue
    return out


def alpha_from_row(row: pd.Series) -> float:
    for key in ("Group Name", "File Name"):
        match = re.search(r"couplingRatio_([0-9.]+)", str(row.get(key, "")))
        if match:
            return float(match.group(1))
    return float("nan")


def min_gap(left: list[float], right: list[float]) -> float:
    i = j = 0
    best = float("inf")
    while i < len(left) and j < len(right):
        best = min(best, abs(left[i] - right[j]))
        if left[i] < right[j]:
            i += 1
        else:
            j += 1
    return best


def gap_table(df: pd.DataFrame, domain: str, entity: str) -> pd.DataFrame:
    work = df[["Group Name", "Bot Name", "step", "master_exposure_last", "servant_exposure_last"]].copy()
    work["alpha"] = work.apply(alpha_from_row, axis=1)
    work["step_num"] = pd.to_numeric(work["step"], errors="coerce")
    work["row_id"] = np.arange(len(work))
    work = work.dropna(subset=["alpha", "step_num"]).sort_values(["alpha", "Bot Name", "row_id"])
    work["bot_run_id"] = work.groupby(["alpha", "Bot Name"], sort=False)["step_num"].transform(
        lambda values: (values == 0).astype(int).cumsum()
    )
    work.loc[work["bot_run_id"] <= 0, "bot_run_id"] = 1
    master: dict[tuple[float, str, int, str], list[float]] = {}
    servant: dict[tuple[float, str, int, str], list[float]] = {}
    key_name = "channel" if entity == "channel" else "id"
    for _, row in work.iterrows():
        base = (float(row["alpha"]), str(row["Bot Name"]), int(row["bot_run_id"]))
        step = float(row["step_num"])
        for item in exposure_items(row["master_exposure_last"]):
            key = str(item.get(key_name, ""))
            if key:
                master.setdefault((*base, key), []).append(step)
        for item in exposure_items(row["servant_exposure_last"]):
            key = str(item.get(key_name, ""))
            if key:
                servant.setdefault((*base, key), []).append(step)
    rows = []
    for key in sorted(set(master) & set(servant)):
        alpha, bot, run_id, entity_id = key
        rows.append(
            {
                "domain": domain,
                "entity": entity,
                "alpha": alpha,
                "bot": bot,
                "bot_run_id": run_id,
                "entity_id": entity_id,
                "gap_steps": min_gap(sorted(master[key]), sorted(servant[key])),
            }
        )
    items = pd.DataFrame(rows)
    if items.empty:
        return pd.DataFrame()
    return items.groupby(["domain", "entity", "alpha", "bot", "bot_run_id"], as_index=False).agg(
        gap_steps=("gap_steps", "mean"), n_common_entities=("entity_id", "count")
    )


def calculate_panels_a_b(politics: pd.DataFrame, entertainment: pd.DataFrame) -> dict[tuple[str, str], pd.DataFrame]:
    return {
        (domain, entity): gap_table(data, domain, entity)
        for domain, data in (("Politics", politics), ("Entertainment", entertainment))
        for entity in ("video", "channel")
    }


def vector_map(path: Path) -> dict[str, list[float]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def mean_vector(ids: list[str], vectors: dict[str, list[float]]) -> np.ndarray | None:
    values = [vectors[video_id] for video_id in ids if video_id in vectors]
    return np.asarray(values, dtype=np.float32).mean(axis=0) if values else None


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominator) if denominator else float("nan")


def semantic_pairs(df: pd.DataFrame, path: Path, last_m: int) -> pd.DataFrame:
    vectors = vector_map(path)
    rows = []
    for _, row in df.iterrows():
        categories = category_map(row.get("[CATEGORY]"))
        master = [video_id for video_id in exposure_ids(row.get("master_exposure_last")) if categories.get(video_id) == 25]
        servant = [video_id for video_id in exposure_ids(row.get("servant_exposure_last")) if categories.get(video_id) == 25]
        left = mean_vector(master, vectors)
        right = mean_vector(servant, vectors)
        rows.append(
            {
                "Group Name": row.get("Group Name", ""),
                "Bot Name": row.get("Bot Name", ""),
                "step": pd.to_numeric(row.get("step"), errors="coerce"),
                "alpha": alpha_from_row(row),
                "sim_pref_t": cosine(left, right) if left is not None and right is not None else float("nan"),
            }
        )
    steps = pd.DataFrame(rows).dropna(subset=["alpha", "step"])
    pairs = []
    for (group_name, bot_name), group in steps.sort_values("step").groupby(["Group Name", "Bot Name"]):
        tail = group.tail(last_m)
        pairs.append(
            {
                "Group Name": group_name,
                "Bot Name": bot_name,
                "alpha": float(group["alpha"].iloc[0]),
                "n_steps_used": len(tail),
                "sim_pref": float(tail["sim_pref_t"].mean(skipna=True)),
            }
        )
    return pd.DataFrame(pairs)


def calculate_panel_c(politics: pd.DataFrame, entertainment: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    return semantic_pairs(politics, args.politics_vectors, args.last_m), semantic_pairs(
        entertainment, args.entertainment_vectors, args.last_m
    )


def label_map(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    out = {}
    for video_id, info in data.items():
        label = str(info.get("stance_label", "") if isinstance(info, dict) else info).strip().lower()
        if label in LABEL_ORDER:
            out[str(video_id)] = label
    return out


def category25_ids(value: Any, categories: dict[str, int]) -> list[str]:
    out = []
    for item in exposure_items(value):
        if not item.get("id"):
            continue
        video_id = str(item["id"])
        category = categories.get(video_id, item.get("category"))
        if category is None and isinstance(item.get("snippet"), dict):
            category = item["snippet"].get("categoryId")
        try:
            if int(category) == 25:
                out.append(video_id)
        except Exception:
            continue
    return out


def stance_counts(ids: list[str], labels: dict[str, str]) -> np.ndarray | None:
    counts = np.zeros(5, dtype=float)
    index = {label: i for i, label in enumerate(LABEL_ORDER)}
    for video_id in ids:
        label = labels.get(video_id)
        if label in index:
            counts[index[label]] += 1
    return counts if counts.sum() else None


def jsd(p: np.ndarray, q: np.ndarray) -> float:
    p = p / p.sum()
    q = q / q.sum()
    midpoint = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return 0.5 * kl(p, midpoint) + 0.5 * kl(q, midpoint)


def stance_pairs(df: pd.DataFrame, path: Path, last_m: int) -> pd.DataFrame:
    labels = label_map(path)
    rows = []
    for row_id, (_, row) in enumerate(df.iterrows()):
        categories = category_map(row.get("[CATEGORY]"))
        rows.append(
            {
                "Group Name": row.get("Group Name", ""),
                "Bot Name": row.get("Bot Name", ""),
                "row_id": row_id,
                "step": pd.to_numeric(row.get("step"), errors="coerce"),
                "alpha": alpha_from_row(row),
                "master": stance_counts(category25_ids(row.get("master_exposure_last"), categories), labels),
                "servant": stance_counts(category25_ids(row.get("servant_exposure_last"), categories), labels),
            }
        )
    steps = pd.DataFrame(rows).dropna(subset=["alpha", "step"])
    pairs = []
    for (group_name, bot_name), group in steps.sort_values(["Group Name", "Bot Name", "row_id"]).groupby(
        ["Group Name", "Bot Name"]
    ):
        group = group.copy()
        group["bot_run_id"] = (group["step"] == 0).astype(int).cumsum()
        for run_id, run in group[group["bot_run_id"] > 0].groupby("bot_run_id"):
            tail = run.tail(last_m)
            master = np.zeros(5)
            servant = np.zeros(5)
            valid_master = valid_servant = 0
            for _, row in tail.iterrows():
                if isinstance(row["master"], np.ndarray):
                    master += row["master"]
                    valid_master += 1
                if isinstance(row["servant"], np.ndarray):
                    servant += row["servant"]
                    valid_servant += 1
            similarity = 1.0 - jsd(master, servant) if valid_master and valid_servant else float("nan")
            pairs.append(
                {
                    "Group Name": group_name,
                    "Bot Name": bot_name,
                    "bot_run_id": int(run_id),
                    "alpha": float(run["alpha"].iloc[0]),
                    "n_steps_used": int(len(tail)) if np.isfinite(similarity) else 0,
                    "stance_similarity": similarity,
                }
            )
    return pd.DataFrame(pairs)


def calculate_panel_d(politics: pd.DataFrame, entertainment: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    return stance_pairs(politics, args.politics_stance, args.last_m), stance_pairs(
        entertainment, args.entertainment_stance, args.last_m
    )


def calculate_figure_data(args: argparse.Namespace) -> dict[str, Any]:
    politics = pd.read_excel(args.politics_input, usecols=REQUIRED_COLUMNS)
    entertainment = pd.read_excel(args.entertainment_input, usecols=REQUIRED_COLUMNS)
    semantic_politics, semantic_entertainment = calculate_panel_c(politics, entertainment, args)
    stance_politics, stance_entertainment = calculate_panel_d(politics, entertainment, args)
    return {
        "time": calculate_panels_a_b(politics, entertainment),
        "semantic_politics": semantic_politics,
        "semantic_entertainment": semantic_entertainment,
        "stance_politics": stance_politics,
        "stance_entertainment": stance_entertainment,
    }


def summarize(df: pd.DataFrame, value: str) -> pd.DataFrame:
    out = df[["alpha", value]].dropna().groupby("alpha", as_index=False).agg(
        mean=(value, "mean"), sd=(value, "std"), n=(value, "count")
    )
    out["sd"] = out["sd"].fillna(0.0)
    out["sem"] = out["sd"] / np.sqrt(out["n"].clip(lower=1))
    out["ci95"] = 1.96 * out["sem"]
    return out.sort_values("alpha")


def fit_stats(df: pd.DataFrame, value: str) -> tuple[float, float, float]:
    data = df[["alpha", value]].dropna()
    x = data["alpha"].to_numpy(float)
    y = data[value].to_numpy(float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    total = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - float(np.sum((y - fitted) ** 2)) / total if total > 0 else float("nan")
    return float(slope), float(intercept), r2


def style_axis(ax: plt.Axes) -> None:
    ax.spines["left"].set_linewidth(1.05)
    ax.spines["bottom"].set_linewidth(1.05)
    ax.tick_params(direction="out", width=0.95, length=3.6, pad=2.2)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.55, alpha=0.78)


def draw_line(ax: plt.Axes, data: pd.DataFrame, color: str, band: str, label: str, marker: str, linestyle: Any, error: str) -> None:
    x = data["alpha"].to_numpy(float)
    y = data["mean"].to_numpy(float)
    err = data[error].fillna(0.0).to_numpy(float)
    ax.fill_between(x, y - err, y + err, color=band, alpha=0.58, lw=0)
    ax.plot(x, y, color=color, lw=1.65, ls=linestyle, marker=marker, ms=4.0, mfc="white", mew=1.2, label=label)


def draw_time_panel(ax: plt.Axes, frames: dict[tuple[str, str], pd.DataFrame], entity: str, title: str) -> None:
    colors = PANEL_PALETTES["time"]
    politics = summarize(frames[("Politics", entity)], "gap_steps")
    entertainment = summarize(frames[("Entertainment", entity)], "gap_steps")
    draw_line(ax, politics, colors["politics"], colors["politics_band"], "Politics", "o", "-", "sd")
    draw_line(ax, entertainment, colors["entertainment"], colors["entertainment_band"], "Entertainment", "s", (0, (4, 2)), "sd")
    ax.set_title(title, fontweight="bold", pad=4.2)
    ax.set_xlabel(r"$\alpha$", labelpad=5.0)
    ax.set_ylabel(r"$\Delta\tau$ (steps)", labelpad=5.5)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xticks(np.arange(0.0, 1.01, 0.2))
    values = np.concatenate([(politics["mean"] - politics["sd"]), (politics["mean"] + politics["sd"]), (entertainment["mean"] - entertainment["sd"]), (entertainment["mean"] + entertainment["sd"])])
    lower = max(0.0, float(np.nanmin(values)))
    upper = float(np.nanmax(values))
    span = max(1.0, upper - lower)
    ax.set_ylim(max(0.0, lower - 0.06 * span), upper + 0.10 * span)
    style_axis(ax)
    handles = [
        Line2D([0], [0], color=colors["politics"], lw=1.7, marker="o", mfc="white", label="Politics"),
        Line2D([0], [0], color=colors["entertainment"], lw=1.7, ls=(0, (4, 2)), marker="s", mfc="white", label="Entertainment"),
        Patch(facecolor="#E7E7E7", edgecolor="none", alpha=0.70, label="Mean +/- s.d."),
    ]
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.98, 0.91), frameon=False, handlelength=1.7)


def draw_metric_panel(ax: plt.Axes, politics_df: pd.DataFrame, entertainment_df: pd.DataFrame, value: str, title: str, ylabel: str, family: str, seed: int, bottom: float, top: float) -> None:
    colors = PANEL_PALETTES[family]
    politics = summarize(politics_df, value)
    entertainment = summarize(entertainment_df, value)
    for data, color, marker, offset, random_seed in (
        (politics_df, colors["politics"], "o", -0.01, seed),
        (entertainment_df, colors["entertainment"], "s", 0.01, seed + 17),
    ):
        clean = data[["alpha", value]].dropna()
        rng = np.random.default_rng(random_seed)
        x = clean["alpha"].to_numpy(float) + offset + rng.normal(0.0, 0.006, len(clean))
        ax.scatter(x, clean[value], s=8.5, marker=marker, color=color, alpha=0.16, linewidths=0, rasterized=True)
    draw_line(ax, politics, colors["politics"], colors["politics_band"], "Politics mean", "o", "-", "ci95")
    draw_line(ax, entertainment, colors["entertainment"], colors["entertainment_band"], "Entertainment mean", "s", "-", "ci95")
    fits = []
    for data, color, label in ((politics_df, colors["politics"], "Politics"), (entertainment_df, colors["entertainment"], "Entertainment")):
        slope, intercept, r2 = fit_stats(data, value)
        grid = np.linspace(0, 1, 200)
        ax.plot(grid, slope * grid + intercept, color=color, lw=1.25, ls=(0, (4, 2)))
        fits.append(Line2D([0], [0], color=color, lw=1.35, ls=(0, (4, 2)), label=rf"{label}: slope = {slope:.3f}, $R^2$ = {r2:.3f}"))
    ax.set_title(title, fontweight="bold", pad=4.2)
    ax.set_xlabel(r"$\alpha$", labelpad=5.0)
    ax.set_ylabel(ylabel, labelpad=5.5)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xticks(np.arange(0.0, 1.01, 0.2))
    values = np.concatenate([(politics["mean"] - politics["ci95"]), (politics["mean"] + politics["ci95"]), (entertainment["mean"] - entertainment["ci95"]), (entertainment["mean"] + entertainment["ci95"])])
    lower = float(np.nanmin(values))
    upper = float(np.nanmax(values))
    span = max(0.01, upper - lower)
    ax.set_ylim(lower - bottom * span, upper + top * span)
    style_axis(ax)
    fit_legend = ax.legend(handles=fits, loc="upper left", bbox_to_anchor=(0.01, 0.94), frameon=False, fontsize=7.4, handlelength=1.45)
    ax.add_artist(fit_legend)
    handles = [
        Line2D([0], [0], color=colors["politics"], lw=1.7, marker="o", mfc="white", label="Politics mean"),
        Line2D([0], [0], color=colors["entertainment"], lw=1.7, marker="s", mfc="white", label="Entertainment mean"),
        Line2D([0], [0], color=PALETTE["ink"], lw=1.25, ls=(0, (4, 2)), label="Linear fit"),
        Patch(facecolor="#E7E7E7", edgecolor="none", alpha=0.70, label="Mean +/- 95% CI"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=7.2, handlelength=1.7)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.16, 1.04, label, transform=ax.transAxes, fontsize=13.0, fontweight="bold", clip_on=False)


def plot_figure(data: dict[str, Any], args: argparse.Namespace) -> tuple[Path, Path, Path]:
    set_figure_style()
    fig, axes = plt.subplots(2, 2, figsize=(args.fig_width, args.fig_height), dpi=320)
    draw_time_panel(axes[0, 0], data["time"], "video", "Common videos")
    draw_time_panel(axes[0, 1], data["time"], "channel", "Common channels")
    draw_metric_panel(axes[1, 0], data["semantic_politics"], data["semantic_entertainment"], "sim_pref", "Semantic similarity", "Semantic similarity", "semantic", 20260629, 0.95, 0.95)
    draw_metric_panel(axes[1, 1], data["stance_politics"], data["stance_entertainment"], "stance_similarity", "Ideological similarity", "Ideological similarity (1-JSD)", "stance", 20260630, 0.74, 0.82)
    for label, axis in zip(("a", "b", "c", "d"), axes.flat):
        axis.set_box_aspect(0.84)
        add_panel_label(axis, label)
    fig.subplots_adjust(left=0.078, right=0.992, top=0.955, bottom=0.082, wspace=0.18, hspace=0.34)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / args.prefix
    png = output.with_suffix(".png")
    pdf = output.with_suffix(".pdf")
    tiff = output.with_suffix(".tiff")
    fig.savefig(png, dpi=600, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(pdf, dpi=600, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(tiff, dpi=600, bbox_inches="tight", pad_inches=0.02, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)
    return png, pdf, tiff


def main() -> None:
    args = parse_args()
    data = calculate_figure_data(args)
    png, pdf, tiff = plot_figure(data, args)
    print(f"[OK] PNG: {png}")
    print(f"[OK] PDF: {pdf}")
    print(f"[OK] TIFF: {tiff}")


if __name__ == "__main__":
    main()
