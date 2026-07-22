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
from matplotlib.lines import Line2D
from matplotlib.patches import ConnectionPatch, Rectangle
from scipy.signal import savgol_filter


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "figures"
OUTPUT_STEM = OUTPUT_DIR / "figure2"
SMOOTH_METHOD = "Savitzky-Golay filter"
SMOOTH_WINDOW = 11
SMOOTH_POLYORDER = 2

REQUIRED_COLUMNS = [
    "Group Name",
    "Bot Name",
    "step",
    "master_exposure_last",
    "servant_exposure_last",
    "[CATEGORY]",
]

DIRECT_METRICS = ["sim_all", "sim_pref", "sim_nonpref"]

ALPHA_PATTERNS = [
    re.compile(r"couplingRatio[_-]?([0-9]*\.?[0-9]+)", re.IGNORECASE),
    re.compile(r"Dual_Test_([0-9]*\.?[0-9]+)", re.IGNORECASE),
    re.compile(r"Test_([0-9]*\.?[0-9]+)", re.IGNORECASE),
]

ALPHA_COLORS = {
    0.0: "#756BB1",
    0.3: "#4EA3A2",
    0.7: "#D6A64F",
    1.0: "#C76D88",
}

METRIC_SPECS = [
    ("video_all", "sim_all", "All videos"),
    ("video_pref", "sim_pref", "Preferred videos"),
    ("video_nonpref", "sim_nonpref", "Non-preferred videos"),
]

INSET_COLORS = {
    "sim_all": "#2166AC",
    "sim_pref": "#C44536",
    "sim_nonpref": "#2F6B3C",
}

DOMAIN_LABELS = {
    "Politics": "Politics",
    "Entertainment": "Entertainment",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--politics-file", type=Path, default=ROOT / "data/political-news_data.xlsx")
    parser.add_argument("--entertainment-file", type=Path, default=ROOT / "data/entertainment_data.xlsx")
    parser.add_argument("--politics-pref-category", type=int, default=25)
    parser.add_argument("--entertainment-pref-category", type=int, default=24)
    parser.add_argument("--alphas", type=str, default="0.0,0.3,0.7,1.0")
    parser.add_argument("--band", choices=["std", "sem"], default="std")
    parser.add_argument("--last-m", type=int, default=50)
    parser.add_argument("--degree", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--fig-width", type=float, default=8.25)
    parser.add_argument("--fig-height", type=float, default=5.65)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--prefix", type=str, default=OUTPUT_STEM.name)
    return parser.parse_args()


def set_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "mathtext.fontset": "dejavusans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#202020",
            "axes.linewidth": 0.82,
            "axes.labelsize": 7.5,
            "axes.titlesize": 8.2,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.2,
            "axes.unicode_minus": False,
        }
    )


def load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported input format: {suffix}")


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
    out: dict[str, int] = {}
    for key, category in parsed.items():
        video_id = str(key).strip()
        if not video_id:
            continue
        try:
            out[video_id] = int(category)
        except Exception:
            continue
    return out


def item_video_id(item: dict[str, Any]) -> str | None:
    value = item.get("id")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_alpha(row: pd.Series) -> float | None:
    if "alpha" in row.index and pd.notna(row.get("alpha")):
        try:
            alpha = float(row.get("alpha"))
            if 0.0 <= alpha <= 1.0:
                return round(alpha, 6)
        except Exception:
            pass
    for text in (
        str(row.get("Group Name", "") or ""),
        str(row.get("File Name", "") or ""),
        str(row.get("Bot Name", "") or ""),
    ):
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


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else float("nan")


def exposure_ids(value: Any) -> list[str]:
    return [video_id for item in parse_exposure_items(value) if (video_id := item_video_id(item))]


def alpha_from_group(group_name: Any) -> float:
    match = re.search(r"couplingRatio_([0-9.]+)", str(group_name))
    return float(match.group(1)) if match else float("nan")


def compute_step_sets(df: pd.DataFrame, domain: str, pref_categories: set[int]) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{domain} missing required columns: {missing}")
    records: list[dict[str, Any]] = []
    work = df[REQUIRED_COLUMNS].copy()
    work["row_id"] = np.arange(len(work))
    for _, row in work.iterrows():
        master = set(exposure_ids(row.get("master_exposure_last")))
        servant = set(exposure_ids(row.get("servant_exposure_last")))
        categories = parse_category_map(row.get("[CATEGORY]"))
        records.append(
            {
                "domain": domain,
                "Group Name": row.get("Group Name", ""),
                "Bot Name": row.get("Bot Name", ""),
                "row_id": int(row["row_id"]),
                "step": pd.to_numeric(row.get("step"), errors="coerce"),
                "alpha": alpha_from_group(row.get("Group Name", "")),
                "a_ids": master,
                "b_ids": servant,
                "a_pref": {video_id for video_id in master if categories.get(video_id) in pref_categories},
                "b_pref": {video_id for video_id in servant if categories.get(video_id) in pref_categories},
                "a_non": {video_id for video_id in master if video_id in categories and categories.get(video_id) not in pref_categories},
                "b_non": {video_id for video_id in servant if video_id in categories and categories.get(video_id) not in pref_categories},
            }
        )
    return pd.DataFrame(records).dropna(subset=["alpha", "step"]).reset_index(drop=True)


def union_jaccard_last_m(tail: pd.DataFrame, column_a: str, column_b: str) -> float:
    union_a: set[str] = set()
    union_b: set[str] = set()
    for values in tail[column_a].tolist():
        if isinstance(values, set):
            union_a |= values
    for values in tail[column_b].tolist():
        if isinstance(values, set):
            union_b |= values
    return jaccard(union_a, union_b)


def compute_pair_last_m(step_df: pd.DataFrame, last_m: int) -> pd.DataFrame:
    pairs: list[dict[str, Any]] = []
    work = step_df.sort_values(["domain", "alpha", "Bot Name", "row_id"]).copy()
    for (domain, alpha, bot_name), group in work.groupby(["domain", "alpha", "Bot Name"], sort=False):
        group = group.copy()
        group["bot_run_id"] = (group["step"] == 0).astype(int).cumsum()
        group.loc[group["bot_run_id"] <= 0, "bot_run_id"] = 1
        for run_id, run in group.groupby("bot_run_id", sort=False):
            tail = run.tail(last_m)
            pairs.append(
                {
                    "domain": domain,
                    "Group Name": run["Group Name"].iloc[0],
                    "Bot Name": bot_name,
                    "bot_run_id": int(run_id),
                    "alpha": float(alpha),
                    "n_steps_used": len(tail),
                    "sim_all": union_jaccard_last_m(tail, "a_ids", "b_ids"),
                    "sim_pref": union_jaccard_last_m(tail, "a_pref", "b_pref"),
                    "sim_nonpref": union_jaccard_last_m(tail, "a_non", "b_non"),
                }
            )
    return pd.DataFrame(pairs)


def compute_alpha_stats(pair_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (domain, alpha), group in pair_df.groupby(["domain", "alpha"], sort=False):
        row: dict[str, Any] = {"domain": domain, "alpha": float(alpha)}
        for metric in DIRECT_METRICS:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if len(values) else float("nan")
            row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else float("nan")
            row[f"{metric}_n"] = int(len(values))
            row[f"{metric}_sem"] = float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["domain", "alpha"]).reset_index(drop=True)


def fit_poly(alpha: np.ndarray, values: np.ndarray, degree: int) -> tuple[np.ndarray, float]:
    mask = np.isfinite(alpha) & np.isfinite(values)
    alpha = alpha[mask]
    values = values[mask]
    if len(alpha) <= degree:
        return np.array([0.0, float(np.nanmean(values) if len(values) else 0.0)]), float("nan")
    coefficients = np.polyfit(alpha, values, deg=degree)
    fitted = np.polyval(coefficients, alpha)
    residual = float(np.sum((values - fitted) ** 2))
    total = float(np.sum((values - np.mean(values)) ** 2))
    return coefficients, 1.0 - residual / total if total > 0 else float("nan")


def adaptive_ylim(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 0.0, 1.0
    lower = float(np.nanmin(values))
    upper = float(np.nanmax(values))
    span = max(upper - lower, 0.04)
    return max(0.0, lower - 0.12 * span), min(1.0, upper + 0.18 * span)


def build_global_category_map(df: pd.DataFrame) -> tuple[dict[str, int], int]:
    global_map: dict[str, int] = {}
    conflicts = 0
    for value in df.get("[CATEGORY]", pd.Series(dtype=object)):
        category_map = parse_category_map(value)
        for video_id, category in category_map.items():
            previous = global_map.get(video_id)
            if previous is not None and previous != category:
                conflicts += 1
            global_map[video_id] = int(category)
    return global_map, conflicts


def row_last_video_ids(row: pd.Series) -> list[str]:
    video_ids: list[str] = []
    for column in ("master_exposure_last", "servant_exposure_last"):
        for item in parse_exposure_items(row.get(column)):
            video_id = item_video_id(item)
            if video_id:
                video_ids.append(str(video_id))
    return video_ids


def apply_global_category_fallback(
    df: pd.DataFrame,
    global_map: dict[str, int],
) -> pd.DataFrame:
    work = df.copy()
    completed_categories: list[str] = []
    for _, row in work.iterrows():
        category_map = parse_category_map(row.get("[CATEGORY]"))
        for video_id in row_last_video_ids(row):
            if video_id not in category_map and video_id in global_map:
                category_map[video_id] = int(global_map[video_id])
        completed_categories.append(json.dumps(category_map, ensure_ascii=False, sort_keys=True))
    work["[CATEGORY]"] = completed_categories
    return work


def compute_step_rows_with_nonpref(df: pd.DataFrame, dataset: str, pref_category: int) -> pd.DataFrame:
    needed = ["step", "master_exposure_last", "servant_exposure_last", "[CATEGORY]", "Bot Name"]
    missing = [col for col in needed if col not in df.columns]
    if missing:
        raise ValueError(f"{dataset} missing required columns: {missing}")

    work = df.copy().reset_index(drop=True)
    work["row_id"] = np.arange(len(work))
    work["dataset"] = dataset
    work["step"] = pd.to_numeric(work["step"], errors="coerce")
    work["alpha"] = work.apply(extract_alpha, axis=1)
    work = work.dropna(subset=["step", "alpha"]).copy()
    work["step"] = work["step"].astype(int)
    work["alpha"] = work["alpha"].astype(float)
    work["Bot Name"] = work["Bot Name"].astype(str)

    work = work.sort_values(["alpha", "Bot Name", "row_id"]).copy()
    work["run_index"] = work.groupby(["alpha", "Bot Name"], sort=False)["step"].transform(
        lambda s: (s == 0).astype(int).cumsum()
    )
    work["bot_run"] = work["Bot Name"] + "#run" + work["run_index"].astype(str)

    rows: list[dict[str, Any]] = []
    for _, row in work.iterrows():
        master_items = parse_exposure_items(row.get("master_exposure_last"))
        servant_items = parse_exposure_items(row.get("servant_exposure_last"))
        category_map = parse_category_map(row.get("[CATEGORY]"))

        master_videos = {vid for item in master_items if (vid := item_video_id(item))}
        servant_videos = {vid for item in servant_items if (vid := item_video_id(item))}

        master_pref: set[str] = set()
        servant_pref: set[str] = set()
        master_nonpref: set[str] = set()
        servant_nonpref: set[str] = set()

        for item in master_items:
            vid = item_video_id(item)
            if vid is None or vid not in category_map:
                continue
            if category_map.get(vid) == pref_category:
                master_pref.add(vid)
            else:
                master_nonpref.add(vid)

        for item in servant_items:
            vid = item_video_id(item)
            if vid is None or vid not in category_map:
                continue
            if category_map.get(vid) == pref_category:
                servant_pref.add(vid)
            else:
                servant_nonpref.add(vid)

        rows.append(
            {
                "dataset": dataset,
                "alpha": row["alpha"],
                "step": row["step"],
                "bot_run": row["bot_run"],
                "video_all": jaccard(master_videos, servant_videos),
                "video_pref": jaccard(master_pref, servant_pref),
                "video_nonpref": jaccard(master_nonpref, servant_nonpref),
            }
        )

    return pd.DataFrame(rows)


def aggregate_step_metrics(row_metrics: pd.DataFrame, band: str) -> pd.DataFrame:
    value_cols = ["video_all", "video_pref", "video_nonpref"]
    agg = row_metrics.groupby(["dataset", "alpha", "step"], as_index=False).agg(
        n_bot_runs=("bot_run", "nunique"),
        **{f"{col}_mean": (col, "mean") for col in value_cols},
        **{f"{col}_std": (col, "std") for col in value_cols},
        **{f"{col}_count": (col, "count") for col in value_cols},
    )
    for col in value_cols:
        std = agg[f"{col}_std"].fillna(0.0)
        count = agg[f"{col}_count"].clip(lower=1)
        agg[f"{col}_band"] = std / np.sqrt(count) if band == "sem" else std
    return agg.sort_values(["dataset", "alpha", "step"]).reset_index(drop=True)


def selected_alphas(alpha_text: str, available: list[float]) -> list[float]:
    selected: list[float] = []
    for token in alpha_text.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = round(float(token), 6)
        except ValueError:
            continue
        if any(np.isclose(value, alpha) for alpha in available):
            selected.append(value)
    if selected:
        return selected
    available_sorted = sorted({round(float(v), 6) for v in available})
    if len(available_sorted) <= 4:
        return available_sorted
    idx = np.linspace(0, len(available_sorted) - 1, 4).round().astype(int)
    return [available_sorted[i] for i in idx]


def smooth_time_series(values: np.ndarray, window: int = SMOOTH_WINDOW, polyorder: int = SMOOTH_POLYORDER) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.size < 3:
        return arr

    finite = np.isfinite(arr)
    if finite.sum() < 3:
        return arr

    filled = arr.copy()
    if not finite.all():
        x = np.arange(arr.size)
        filled[~finite] = np.interp(x[~finite], x[finite], arr[finite])

    use_window = min(window, arr.size if arr.size % 2 == 1 else arr.size - 1)
    min_window = polyorder + 2
    if min_window % 2 == 0:
        min_window += 1
    use_window = max(use_window, min_window)
    if use_window > arr.size:
        use_window = arr.size if arr.size % 2 == 1 else arr.size - 1
    if use_window <= polyorder or use_window < 3:
        return filled

    return savgol_filter(filled, window_length=use_window, polyorder=polyorder, mode="interp")


def step_to_plot_x(step: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(step, dtype=float) + 1.0


def panel_ylim(values: list[np.ndarray]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    vals = np.concatenate(values)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return 0.0, 1.0
    ymin = float(np.nanmin(vals))
    ymax = float(np.nanmax(vals))
    span = max(ymax - ymin, 0.06)
    return max(-0.02, ymin - 0.08 * span), min(1.0, ymax + 0.18 * span)


def style_main_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#E4E4E4", linewidth=0.5, alpha=0.78)
    ax.tick_params(direction="out", length=2.6, width=0.72, color="#202020", pad=1.5)
    ax.set_axisbelow(True)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(0.82)
        ax.spines[side].set_color("#202020")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def style_inset_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#E7E7E7", linewidth=0.32, alpha=0.7)
    ax.tick_params(direction="out", length=1.8, width=0.55, pad=1.0, labelsize=4.8)
    ax.yaxis.set_ticks_position("right")
    ax.yaxis.set_label_position("right")
    ax.tick_params(axis="y", labelleft=False, labelright=True, pad=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.55)
        spine.set_color("#333333")
    ax.set_xlabel("")
    ax.set_ylabel("")


def draw_direct_inset(
    ax: plt.Axes,
    pair_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    metric: str,
    color: str,
    degree: int,
) -> None:
    plot_pair = pair_df.dropna(subset=["alpha", metric]).copy()
    plot_stats = stats_df.dropna(subset=["alpha", f"{metric}_mean"]).copy()
    if plot_pair.empty or plot_stats.empty:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", va="center", fontsize=5.5)
        style_inset_axis(ax)
        return

    rng = np.random.default_rng(20260620)
    jitter = rng.normal(0.0, 0.012, size=len(plot_pair))
    point_x = plot_pair["alpha"].to_numpy(dtype=float) + jitter
    point_y = plot_pair[metric].to_numpy(dtype=float)
    ax.scatter(
        point_x,
        point_y,
        s=5.0,
        color=color,
        alpha=0.18,
        edgecolors="none",
        zorder=1,
    )

    x = plot_stats["alpha"].to_numpy(dtype=float)
    y = plot_stats[f"{metric}_mean"].to_numpy(dtype=float)
    sem = plot_stats[f"{metric}_sem"].fillna(0.0).to_numpy(dtype=float)
    ax.errorbar(
        x,
        y,
        yerr=sem,
        fmt="o",
        markersize=2.0,
        markerfacecolor="white",
        markeredgecolor="#202020",
        markeredgewidth=0.45,
        capsize=1.5,
        capthick=0.45,
        elinewidth=0.5,
        linewidth=0.75,
        color="#202020",
        zorder=3,
    )

    coeff, r2 = fit_poly(x, y, degree)
    xs = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 150)
    ax.plot(xs, np.polyval(coeff, xs), color=color, linewidth=1.05, zorder=4)
    slope = float(coeff[0]) if len(coeff) >= 2 else float("nan")

    ax.text(
        0.05,
        0.92,
        f"slope={slope:.3f}\n" + rf"$R^2={r2:.2f}$",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=4.9,
        color="#202020",
        linespacing=1.22,
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.80, pad=0.8),
    )

    y_lim = adaptive_ylim(plot_pair[metric].to_numpy(dtype=float))
    ax.set_xlim(-0.06, 1.06)
    ax.set_ylim(*y_lim)
    ax.set_xticks([0.0, 0.5, 1.0])
    style_inset_axis(ax)


def draw_last_m_rectangle(
    ax: plt.Axes,
    data_by_alpha: list[pd.DataFrame],
    metric: str,
    last_m: int,
) -> tuple[float, float, float, float] | None:
    steps = [df["step"].to_numpy(dtype=float) for df in data_by_alpha if not df.empty]
    if not steps:
        return None
    max_step = max(float(np.nanmax(s)) for s in steps if s.size)
    start = max(0.0, max_step - last_m + 1)
    start_x = float(step_to_plot_x(start))
    max_step_x = float(step_to_plot_x(max_step))
    ys: list[np.ndarray] = []
    for df in data_by_alpha:
        if df.empty:
            continue
        in_window = df[df["step"].between(start, max_step)]
        if not in_window.empty:
            y = in_window[f"{metric}_mean"].to_numpy(dtype=float)
            err = in_window[f"{metric}_band"].fillna(0.0).to_numpy(dtype=float)
            ys.append(np.concatenate([y - err, y + err]))
    y0, y1 = ax.get_ylim()
    if ys:
        vals = np.concatenate(ys)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            lo = float(np.nanmin(vals))
            hi = float(np.nanmax(vals))
            axis_span = y1 - y0
            span = max(hi - lo, 0.15 * axis_span)
            cy = (lo + hi) / 2
            rect_y0 = max(y0, cy - 0.42 * span)
            rect_y1 = min(y1 - 0.10 * axis_span, cy + 0.42 * span)
            if rect_y1 <= rect_y0:
                rect_y1 = min(y1 - 0.10 * axis_span, y0 + 0.88 * axis_span)
                rect_y0 = max(y0, rect_y1 - 0.22 * axis_span)
        else:
            rect_y0, rect_y1 = y0, y1
    else:
        rect_y0, rect_y1 = y0, y1

    rect = Rectangle(
        (start_x, rect_y0),
        max_step_x - start_x,
        rect_y1 - rect_y0,
        fill=False,
        edgecolor="#202020",
        linewidth=0.72,
        linestyle=(0, (3, 2)),
        zorder=7,
    )
    ax.add_patch(rect)
    return start_x, max_step_x, rect_y0, rect_y1


def add_inset_connector(ax: plt.Axes, axins: plt.Axes, rect_bounds: tuple[float, float, float, float] | None) -> None:
    if rect_bounds is None:
        return
    start, _, rect_y0, rect_y1 = rect_bounds
    target_y = rect_y0 + 0.72 * (rect_y1 - rect_y0)
    conn = ConnectionPatch(
        xyA=(1.0, 0.0),
        coordsA=axins.transAxes,
        xyB=(start, target_y),
        coordsB=ax.transData,
        arrowstyle="->",
        mutation_scale=7.2,
        linewidth=0.65,
        color="#202020",
        alpha=0.82,
        zorder=8,
        shrinkA=1.5,
        shrinkB=1.5,
    )
    ax.add_artist(conn)


def draw_panel(
    ax: plt.Axes,
    step_agg: pd.DataFrame,
    direct_pair: pd.DataFrame,
    direct_stats: pd.DataFrame,
    domain: str,
    metric: str,
    direct_metric: str,
    title: str,
    alphas: list[float],
    last_m: int,
    degree: int,
    panel_label: str,
) -> None:
    panel_values: list[np.ndarray] = []
    data_by_alpha: list[pd.DataFrame] = []
    for alpha in alphas:
        data = step_agg[(step_agg["dataset"] == domain) & np.isclose(step_agg["alpha"], alpha)].sort_values("step")
        data_by_alpha.append(data)
        if data.empty:
            continue
        x = step_to_plot_x(data["step"].to_numpy(dtype=float))
        y = data[f"{metric}_mean"].to_numpy(dtype=float)
        err = data[f"{metric}_band"].fillna(0.0).to_numpy(dtype=float)
        y_smooth = smooth_time_series(y)
        lower_smooth = smooth_time_series(y - err)
        upper_smooth = smooth_time_series(y + err)
        lower_smooth = np.minimum(lower_smooth, y_smooth)
        upper_smooth = np.maximum(upper_smooth, y_smooth)
        color = ALPHA_COLORS.get(round(float(alpha), 1), "#555555")
        ax.fill_between(x, lower_smooth, upper_smooth, color=color, alpha=0.10, linewidth=0, zorder=1)
        ax.plot(x, y_smooth, color=color, linewidth=1.35, solid_capstyle="round", zorder=2)
        panel_values.append(np.concatenate([lower_smooth, upper_smooth]))

    ax.set_title(title, fontweight="bold", pad=3.0)
    ax.set_ylim(*panel_ylim(panel_values))
    style_main_axis(ax)
    all_steps = step_agg.loc[step_agg["dataset"] == domain, "step"].dropna().to_numpy(dtype=float)
    if all_steps.size:
        xmin = math.floor(float(np.nanmin(all_steps)))
        xmax = math.ceil(float(np.nanmax(all_steps)))
        ax.set_xscale("log")
        ax.set_xlim(max(1.0, float(step_to_plot_x(xmin))), float(step_to_plot_x(xmax)) * 1.02)
        if xmax >= 140:
            tick_steps = np.array([0, 1, 10, 50, 100, 150], dtype=float)
            tick_steps = tick_steps[tick_steps <= xmax]
        else:
            tick_steps = np.linspace(max(0, xmin), xmax, 4).round().astype(int)
        ax.set_xticks(step_to_plot_x(tick_steps))
        ax.set_xticklabels([str(int(tick)) for tick in tick_steps])

    rect_bounds = draw_last_m_rectangle(ax, data_by_alpha, metric, last_m)
    inset_y = 0.515 if panel_label == "e" else 0.585
    inset_position = [0.305, inset_y, 0.39, 0.33]
    axins = ax.inset_axes(inset_position)
    draw_direct_inset(
        axins,
        direct_pair[direct_pair["domain"] == domain],
        direct_stats[direct_stats["domain"] == domain],
        direct_metric,
        INSET_COLORS.get(direct_metric, "#2166AC"),
        degree,
    )
    add_inset_connector(ax, axins, rect_bounds)


def add_panel_label(fig: plt.Figure, ax: plt.Axes, label: str) -> None:
    box = ax.get_position()
    fig.text(
        box.x0 - 0.022,
        box.y1 + 0.010,
        label,
        ha="left",
        va="bottom",
        fontsize=10.5,
        fontweight="bold",
        color="#111111",
    )


def calculate_figure_data(args: argparse.Namespace) -> dict[str, Any]:
    politics_raw = load_table(args.politics_file)
    entertainment_raw = load_table(args.entertainment_file)
    politics_global, _ = build_global_category_map(politics_raw)
    entertainment_global, _ = build_global_category_map(entertainment_raw)
    politics_main = apply_global_category_fallback(politics_raw, politics_global)
    entertainment_main = apply_global_category_fallback(entertainment_raw, entertainment_global)
    politics_rows = compute_step_rows_with_nonpref(politics_main, "Politics", args.politics_pref_category)
    entertainment_rows = compute_step_rows_with_nonpref(
        entertainment_main, "Entertainment", args.entertainment_pref_category
    )
    row_metrics = pd.concat([politics_rows, entertainment_rows], ignore_index=True)
    step_agg = aggregate_step_metrics(row_metrics, args.band)
    available_alphas = sorted(step_agg["alpha"].dropna().unique().tolist())
    alphas = selected_alphas(args.alphas, available_alphas)
    if not alphas:
        raise ValueError("No alpha values available for plotting.")
    politics_direct_step = compute_step_sets(politics_raw, "Politics", {args.politics_pref_category})
    entertainment_direct_step = compute_step_sets(
        entertainment_raw, "Entertainment", {args.entertainment_pref_category}
    )
    direct_pair = pd.concat(
        [
            compute_pair_last_m(politics_direct_step, args.last_m),
            compute_pair_last_m(entertainment_direct_step, args.last_m),
        ],
        ignore_index=True,
    )
    direct_stats = compute_alpha_stats(direct_pair)
    specs = [
        ("a", "Politics", "video_all", "sim_all", "Politics: all videos"),
        ("b", "Politics", "video_pref", "sim_pref", "Politics: preferred videos"),
        ("c", "Politics", "video_nonpref", "sim_nonpref", "Politics: non-preferred videos"),
        ("d", "Entertainment", "video_all", "sim_all", "Entertainment: all videos"),
        ("e", "Entertainment", "video_pref", "sim_pref", "Entertainment: preferred videos"),
        ("f", "Entertainment", "video_nonpref", "sim_nonpref", "Entertainment: non-preferred videos"),
    ]
    panels: dict[str, dict[str, Any]] = {}
    for letter, domain, metric, direct_metric, title in specs:
        panels[letter] = {
            "domain": domain,
            "metric": metric,
            "direct_metric": direct_metric,
            "title": title,
            "step_agg": step_agg[step_agg["dataset"] == domain].copy(),
            "direct_pair": direct_pair[direct_pair["domain"] == domain].copy(),
            "direct_stats": direct_stats[direct_stats["domain"] == domain].copy(),
        }
    return {"panels": panels, "alphas": alphas}


def plot_figure(data: dict[str, Any], args: argparse.Namespace) -> tuple[Path, Path, Path]:
    set_style()
    fig, axes = plt.subplots(2, 3, figsize=(args.fig_width, args.fig_height), dpi=320, sharex=True)
    letters = ["a", "b", "c", "d", "e", "f"]
    alphas = data["alphas"]
    for ax, letter in zip(axes.flat, letters):
        panel = data["panels"][letter]
        draw_panel(
            ax,
            panel["step_agg"],
            panel["direct_pair"],
            panel["direct_stats"],
            panel["domain"],
            panel["metric"],
            panel["direct_metric"],
            panel["title"],
            alphas,
            args.last_m,
            args.degree,
            letter,
        )
    for ax in axes[:, 0]:
        ax.set_ylabel("Jaccard similarity")
    for ax in axes.flat:
        ax.set_xlabel(r"Step, $t$")
    alpha_handles = [
        Line2D([0], [0], color=ALPHA_COLORS.get(round(float(alpha), 1), "#555555"), lw=1.5, label=rf"$\alpha={alpha:.1f}$")
        for alpha in alphas
    ]
    alpha_legend = fig.legend(
        handles=alpha_handles,
        loc="lower center",
        ncol=len(alpha_handles),
        bbox_to_anchor=(0.5, 0.028),
        frameon=True,
        handlelength=2.0,
        columnspacing=1.4,
        borderpad=0.35,
        fontsize=6.6,
    )
    alpha_legend.get_frame().set_facecolor("white")
    alpha_legend.get_frame().set_edgecolor("#D6D6D6")
    alpha_legend.get_frame().set_linewidth(0.65)
    fig.subplots_adjust(left=0.065, right=0.992, top=0.95, bottom=0.142, wspace=0.24, hspace=0.36)
    for ax, letter in zip(axes.flat, letters):
        add_panel_label(fig, ax, letter)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_path = args.output_dir / f"{args.prefix}.png"
    pdf_path = args.output_dir / f"{args.prefix}.pdf"
    tiff_path = args.output_dir / f"{args.prefix}.tiff"
    fig.savefig(png_path, dpi=600, bbox_inches="tight", pad_inches=0.025)
    fig.savefig(pdf_path, dpi=600, bbox_inches="tight", pad_inches=0.025)
    fig.savefig(
        tiff_path,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.025,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)
    return png_path, pdf_path, tiff_path


def main() -> None:
    args = parse_args()
    data = calculate_figure_data(args)
    png_path, pdf_path, tiff_path = plot_figure(data, args)
    print(f"[OK] PNG: {png_path}")
    print(f"[OK] PDF: {pdf_path}")
    print(f"[OK] TIFF: {tiff_path}")


if __name__ == "__main__":
    main()
