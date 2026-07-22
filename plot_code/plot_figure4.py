from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, PercentFormatter
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

P1_COLOR = "#267C77"
P0_COLOR = "#B98528"
P2_COLOR = "#7A5BA6"
LOW_COLOR = "#6672A5"
HIGH_COLOR = "#BD6B56"
LIFT_COLOR = "#21313F"
SD_COLOR = "#87909A"
TREND_COLOR = "#4E5D6C"
GRID_COLOR = "#ECEFF1"
TEXT_COLOR = "#1F2328"
INSET_FACE = "#FBFAF7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--politics-input", type=Path, default=ROOT / "data" / "political-news_data.xlsx")
    parser.add_argument("--entertainment-input", type=Path, default=ROOT / "data" / "entertainment_data.xlsx")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    parser.add_argument("--prefix", type=str, default="figure4")
    parser.add_argument("--steady-start-ratio", type=float, default=0.0)
    parser.add_argument("--exclude-alpha-ge", type=float, default=0.99)
    parser.add_argument("--fig-width", type=float, default=7.25)
    parser.add_argument("--fig-height", type=float, default=6.85)
    return parser.parse_args()



def norm_filename(value: Any) -> str:
    return str(value).strip() if value is not None else ''


def to_step_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        match = re.search('(\\d+)', str(value).strip())
        return int(match.group(1)) if match else None


def parse_json_tolerant(text: Any, default: Any) -> Any:
    if text is None:
        return default
    if isinstance(text, (dict, list)):
        return text
    if isinstance(text, float) and np.isnan(text):
        return default
    value = str(text).strip()
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        pass
    try:
        return ast.literal_eval(value)
    except Exception:
        pass
    normalized = value.replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', 'null')
    try:
        return json.loads(normalized)
    except Exception:
        return default


def parse_exposure_robust(cell: Any) -> tuple[set[str], set[str]]:
    if cell is None or (isinstance(cell, float) and np.isnan(cell)):
        return (set(), set())
    value = str(cell).strip()
    if not value:
        return (set(), set())
    candidates: list[str] = []
    if value.startswith('[') and value.endswith(']'):
        candidates.append(value)
        inner = value
        while inner.startswith('[') and inner.endswith(']'):
            inner = inner[1:-1].strip()
        if inner:
            candidates.append('[' + inner + ']')
    else:
        candidates.extend(['[' + value + ']', value])
    parsed = None
    for candidate in candidates:
        parsed = parse_json_tolerant(candidate, None)
        if parsed is not None:
            break
    if parsed is None:
        return (set(), set())
    video_ids: set[str] = set()
    channel_ids: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get('id'):
                video_ids.add(str(node['id']))
            if node.get('channel'):
                channel_ids.add(str(node['channel']))
            for child in node.values():
                if isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(parsed)
    return (video_ids, channel_ids)


def parse_select_robust(cell: Any) -> tuple[str | None, str | None]:
    parsed = parse_json_tolerant(cell, {})
    if not isinstance(parsed, dict):
        return (None, None)
    video_id = parsed.get('id')
    channel_id = parsed.get('channel')
    return (str(video_id) if video_id else None, str(channel_id) if channel_id else None)


def parse_category_map(cell: Any) -> dict[str, int]:
    parsed = parse_json_tolerant(cell, {})
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, int] = {}
    for (key, value) in parsed.items():
        try:
            result[str(key)] = int(value)
        except Exception:
            continue
    return result


def extract_alpha(file_name: str, group_name: str) -> float:
    for source in (file_name, group_name):
        match = re.search('Test_(\\d+\\.?\\d*)_', str(source))
        if match:
            return float(match.group(1))
        match = re.search('couplingRatio_(\\d+\\.?\\d*)', str(source))
        if match:
            return float(match.group(1))
    return float('nan')


def preprocess(exposure_df: pd.DataFrame) -> pd.DataFrame:
    exp = exposure_df.copy()
    if 'File Name' in exp.columns:
        exp['filename_clean'] = exp['File Name'].map(norm_filename)
    elif 'file_name' in exp.columns:
        exp['filename_clean'] = exp['file_name'].map(norm_filename)
    else:
        raise ValueError('Exposure table lacks File Name/file_name.')
    group_col = 'Group Name' if 'Group Name' in exp.columns else 'group_name' if 'group_name' in exp.columns else None
    if 'step' not in exp.columns:
        raise ValueError('Exposure table lacks step.')
    exp['step'] = exp['step'].map(to_step_int)
    exp = exp.dropna(subset=['step']).copy()
    exp['step'] = exp['step'].astype(int)
    master_col = 'master_exposure_last'
    servant_col = 'servant_exposure_last'
    if master_col not in exp.columns or servant_col not in exp.columns:
        raise ValueError('Exposure table lacks the master/servant exposure columns.')
    parsed_master = exp[master_col].apply(parse_exposure_robust)
    exp['m_vids'] = [item[0] for item in parsed_master]
    exp['m_chans'] = [item[1] for item in parsed_master]
    parsed_servant = exp[servant_col].apply(parse_exposure_robust)
    exp['s_vids'] = [item[0] for item in parsed_servant]
    exp['s_chans'] = [item[1] for item in parsed_servant]
    if '[CATEGORY]' in exp.columns:
        exp['category_map'] = exp['[CATEGORY]'].apply(parse_category_map)
    else:
        exp['category_map'] = [{} for _ in range(len(exp))]
    if group_col:
        exp['alpha'] = [extract_alpha(file_name, group_name) for (file_name, group_name) in zip(exp['filename_clean'], exp[group_col].astype(str))]
    else:
        exp['alpha'] = [extract_alpha(file_name, '') for file_name in exp['filename_clean']]
    merged = exp.copy()
    for column in ['select_master', 'select_servant']:
        if column not in merged.columns:
            merged[column] = np.nan
    master_select = merged['select_master'].apply(parse_select_robust)
    servant_select = merged['select_servant'].apply(parse_select_robust)
    merged['master_video_id'] = [item[0] for item in master_select]
    merged['master_channel'] = [item[1] for item in master_select]
    merged['servant_video_id'] = [item[0] for item in servant_select]
    merged['servant_channel'] = [item[1] for item in servant_select]
    merged = merged.reset_index(drop=True)
    merged['row_id'] = np.arange(len(merged))
    return merged


def calculate_bot_metrics(group: pd.DataFrame, direction: str, steady_start_ratio: float, preferred_categories: frozenset[int]) -> dict[str, Any]:
    if direction == 'M2S':
        (source_prefix, target_prefix) = ('m', 's')
    else:
        (source_prefix, target_prefix) = ('s', 'm')
    sort_columns = ['step', 'row_id'] if 'row_id' in group.columns else ['step']
    group = group.sort_values(sort_columns).reset_index(drop=True)
    n_rows = len(group)
    if n_rows == 0:
        return {}
    alpha = float(group['alpha'].iloc[0])
    start_index = int(max(0, min(0.999, steady_start_ratio)) * n_rows)
    target_future_videos = [set() for _ in range(n_rows)]
    target_future_channels = [set() for _ in range(n_rows)]
    running_videos: set[str] = set()
    running_channels: set[str] = set()
    for index in range(n_rows - 2, -1, -1):
        running_videos = running_videos.union(group.iloc[index + 1][f'{target_prefix}_vids'])
        running_channels = running_channels.union(group.iloc[index + 1][f'{target_prefix}_chans'])
        target_future_videos[index] = running_videos.copy()
        target_future_channels[index] = running_channels.copy()
    target_history_videos: set[str] = set()
    target_history_channels: set[str] = set()
    v_m1_hit = v_m1_valid = v_m4_hit = v_m4_valid = 0
    v_m4_pref_hit = v_m4_pref_valid = 0
    v_m4_nonpref_hit = v_m4_nonpref_valid = 0
    c_m1_hit = c_m1_valid = c_m4_hit = c_m4_valid = 0
    for index in range(n_rows):
        row = group.iloc[index]
        target_history_videos.update(row[f'{target_prefix}_vids'])
        target_history_channels.update(row[f'{target_prefix}_chans'])
        if index < start_index:
            continue
        master_video = str(row['master_video_id']) if pd.notna(row['master_video_id']) else None
        servant_video = str(row['servant_video_id']) if pd.notna(row['servant_video_id']) else None
        master_channel = str(row['master_channel']) if pd.notna(row['master_channel']) else None
        servant_channel = str(row['servant_channel']) if pd.notna(row['servant_channel']) else None
        if direction == 'M2S':
            (clicked_video, other_video) = (master_video, servant_video)
            (clicked_channel, other_channel) = (master_channel, servant_channel)
        else:
            (clicked_video, other_video) = (servant_video, master_video)
            (clicked_channel, other_channel) = (servant_channel, master_channel)
        source_videos: set[str] = row[f'{source_prefix}_vids']
        source_channels: set[str] = row[f'{source_prefix}_chans']
        category_map = row['category_map'] if isinstance(row.get('category_map'), dict) else {}
        if clicked_video and clicked_video not in target_history_videos and (clicked_video != other_video):
            v_m1_valid += 1
            if clicked_video in target_future_videos[index]:
                v_m1_hit += 1
        unclicked_videos = source_videos - ({clicked_video} if clicked_video else set())
        valid_unclicked_videos = unclicked_videos - target_history_videos
        if valid_unclicked_videos:
            v_m4_valid += len(valid_unclicked_videos)
            v_m4_hit += len(valid_unclicked_videos.intersection(target_future_videos[index]))
            preferred = {video_id for video_id in valid_unclicked_videos if category_map.get(video_id) in preferred_categories}
            nonpreferred = {video_id for video_id in valid_unclicked_videos if video_id in category_map and category_map.get(video_id) not in preferred_categories}
            if preferred:
                v_m4_pref_valid += len(preferred)
                v_m4_pref_hit += len(preferred.intersection(target_future_videos[index]))
            if nonpreferred:
                v_m4_nonpref_valid += len(nonpreferred)
                v_m4_nonpref_hit += len(nonpreferred.intersection(target_future_videos[index]))
        if clicked_channel and clicked_channel not in target_history_channels and (clicked_channel != other_channel):
            c_m1_valid += 1
            if clicked_channel in target_future_channels[index]:
                c_m1_hit += 1
        unclicked_channels = source_channels - ({clicked_channel} if clicked_channel else set())
        valid_unclicked_channels = unclicked_channels - target_history_channels
        if valid_unclicked_channels:
            c_m4_valid += len(valid_unclicked_channels)
            c_m4_hit += len(valid_unclicked_channels.intersection(target_future_channels[index]))
    run_id = int(group['bot_run_id'].iloc[0]) if 'bot_run_id' in group.columns else 1
    base_bot = str(group['filename_clean'].iloc[0])
    return {'alpha': alpha, 'bot_file': f'{base_bot}#run{run_id}', 'bot_run_id': run_id, 'direction': direction, 'v_m1_hit': v_m1_hit, 'v_m1_valid': v_m1_valid, 'v_m4_hit': v_m4_hit, 'v_m4_valid': v_m4_valid, 'v_m4_pref_hit': v_m4_pref_hit, 'v_m4_pref_valid': v_m4_pref_valid, 'v_m4_nonpref_hit': v_m4_nonpref_hit, 'v_m4_nonpref_valid': v_m4_nonpref_valid, 'c_m1_hit': c_m1_hit, 'c_m1_valid': c_m1_valid, 'c_m4_hit': c_m4_hit, 'c_m4_valid': c_m4_valid}


def compute_metrics(merged: pd.DataFrame, steady_start_ratio: float, exclude_alpha_ge: float, preferred_categories: frozenset[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sort_columns = ['alpha', 'filename_clean', 'row_id'] if 'row_id' in merged.columns else ['alpha', 'filename_clean']
    work = merged.sort_values(sort_columns).copy()
    for ((alpha, _), full_group) in work.groupby(['alpha', 'filename_clean'], sort=False):
        if len(full_group) < 2:
            continue
        if not np.isnan(float(alpha)) and float(alpha) >= exclude_alpha_ge:
            continue
        full_group = full_group.copy()
        full_group['bot_run_id'] = (full_group['step'] == 0).astype(int).cumsum()
        full_group = full_group[full_group['bot_run_id'] > 0]
        for (_, run_group) in full_group.groupby('bot_run_id', sort=False):
            if len(run_group) < 2:
                continue
            rows.append(calculate_bot_metrics(run_group, 'M2S', steady_start_ratio, preferred_categories))
            rows.append(calculate_bot_metrics(run_group, 'S2M', steady_start_ratio, preferred_categories))
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        return metrics
    for prefix in ['v', 'c']:
        metrics[f'{prefix}_m1_rate'] = metrics.apply(lambda row: row[f'{prefix}_m1_hit'] / row[f'{prefix}_m1_valid'] if row[f'{prefix}_m1_valid'] > 0 else np.nan, axis=1)
        metrics[f'{prefix}_m2_rate'] = 1 - metrics[f'{prefix}_m1_rate']
        metrics[f'{prefix}_m4_rate'] = metrics.apply(lambda row: row[f'{prefix}_m4_hit'] / row[f'{prefix}_m4_valid'] if row[f'{prefix}_m4_valid'] > 0 else np.nan, axis=1)
        metrics[f'{prefix}_m3_rate'] = 1 - metrics[f'{prefix}_m4_rate']
    metrics['v_m4_pref_rate'] = metrics.apply(lambda row: row['v_m4_pref_hit'] / row['v_m4_pref_valid'] if row['v_m4_pref_valid'] > 0 else np.nan, axis=1)
    metrics['v_m4_nonpref_rate'] = metrics.apply(lambda row: row['v_m4_nonpref_hit'] / row['v_m4_nonpref_valid'] if row['v_m4_nonpref_valid'] > 0 else np.nan, axis=1)
    return metrics


def prepare_metric_points(metrics: pd.DataFrame, comparison_column: str) -> pd.DataFrame:
    columns = ['direction', 'alpha', 'bot_file', 'v_m1_rate', comparison_column]
    missing = [column for column in columns if column not in metrics.columns]
    if missing:
        raise ValueError(f'Metrics are missing required columns: {missing}')
    points = metrics[columns].dropna(subset=columns).copy()
    points = points.rename(columns={'v_m1_rate': 'p1_rate', comparison_column: 'p0_rate'})
    points['alpha'] = points['alpha'].astype(float).round(6)
    points['p1_rate'] = points['p1_rate'].astype(float)
    points['p0_rate'] = points['p0_rate'].astype(float)
    return points


def build_panel_result(metrics: pd.DataFrame, label: str, comparison_column: str, second_metric_label: str) -> dict[str, Any]:
    points = prepare_metric_points(metrics, comparison_column)
    relative_summary = build_relative_summary(points)
    relative_candidates, relative_best = find_relative_turning_point(relative_summary)
    probability_summary = build_probability_summary(points, second_metric_label=second_metric_label)
    return {
        "raw": points,
        "points": points,
        "relative_summary": relative_summary,
        "relative_candidates": relative_candidates,
        "relative_best": relative_best,
        "probability_summary": probability_summary,
    }


def calculate_dataset(path: Path, preferred_category: int, steady_start_ratio: float, exclude_alpha_ge: float) -> pd.DataFrame:
    exposure = pd.read_excel(path)
    merged = preprocess(exposure)
    return compute_metrics(merged, steady_start_ratio, exclude_alpha_ge, frozenset({preferred_category}))


def calculate_figure_data(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    politics_metrics = calculate_dataset(args.politics_input, 25, args.steady_start_ratio, args.exclude_alpha_ge)
    entertainment_metrics = calculate_dataset(args.entertainment_input, 24, args.steady_start_ratio, args.exclude_alpha_ge)
    return {
        "politics_total": build_panel_result(politics_metrics, "Politics", "v_m4_rate", "P0"),
        "entertainment_total": build_panel_result(entertainment_metrics, "Entertainment", "v_m4_rate", "P0"),
        "politics_preference": build_panel_result(politics_metrics, "Politics", "v_m4_pref_rate", "P2"),
        "entertainment_preference": build_panel_result(entertainment_metrics, "Entertainment", "v_m4_pref_rate", "P2"),
    }



def set_refresh_figure_style() -> None:
    mpl.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans', 'sans-serif'], 'mathtext.fontset': 'dejavusans', 'font.size': 7.2, 'axes.labelsize': 8.0, 'axes.titlesize': 8.8, 'xtick.labelsize': 6.9, 'ytick.labelsize': 6.9, 'legend.fontsize': 6.9, 'axes.linewidth': 0.78, 'axes.edgecolor': TEXT_COLOR, 'axes.facecolor': 'white', 'figure.facecolor': 'white', 'xtick.major.width': 0.72, 'ytick.major.width': 0.72, 'xtick.major.size': 2.7, 'ytick.major.size': 2.7, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none', 'axes.unicode_minus': False})


def style_axis(ax: plt.Axes) -> None:
    ax.grid(True, axis='y', color=GRID_COLOR, linewidth=0.58, alpha=0.95)
    ax.grid(True, axis='x', color=GRID_COLOR, linewidth=0.35, alpha=0.38)
    ax.set_axisbelow(True)
    ax.tick_params(direction='out', colors=TEXT_COLOR, pad=2.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for side in ['left', 'bottom']:
        ax.spines[side].set_color(TEXT_COLOR)
        ax.spines[side].set_linewidth(0.78)


def build_relative_summary(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work['delta_p1_minus_p0'] = work['p1_rate'] - work['p0_rate']
    work['relative_improvement'] = np.where(work['p0_rate'] > 0, work['delta_p1_minus_p0'] / work['p0_rate'], np.nan)
    work = work[np.isfinite(work['relative_improvement'])].copy()
    summary = work.groupby('alpha', as_index=False).agg(relative_mean=('relative_improvement', 'mean'), relative_sd=('relative_improvement', lambda x: float(np.std(x, ddof=1)) if len(x) > 1 else 0.0), relative_variance=('relative_improvement', lambda x: float(np.var(x, ddof=1)) if len(x) > 1 else 0.0), relative_sem=('relative_improvement', lambda x: float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0), n=('relative_improvement', 'size')).sort_values('alpha').reset_index(drop=True)
    return summary


def build_probability_summary(df: pd.DataFrame, second_metric_label: str='P0') -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (alpha, group) in df.groupby('alpha', sort=True):
        for (metric, col) in [('P1', 'p1_rate'), (second_metric_label, 'p0_rate')]:
            values = group[col].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
            n = int(len(values))
            sd = float(values.std(ddof=1)) if n > 1 else 0.0
            rows.append({'alpha': float(alpha), 'metric': metric, 'mean': float(values.mean()) if n else np.nan, 'sd': sd, 'sem': sd / np.sqrt(n) if n > 1 else 0.0, 'n': n})
    return pd.DataFrame(rows)


def plateau_fit_stats(values: pd.Series | np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {'level': np.nan, 'sse': np.nan, 'n': 0.0}
    level = float(np.mean(arr))
    sse = float(np.sum((arr - level) ** 2))
    return {'level': level, 'sse': sse, 'n': float(len(arr))}


def find_relative_turning_point(summary: pd.DataFrame, min_alpha_per_side: int=2) -> tuple[pd.DataFrame, dict[str, Any]]:
    alphas = sorted((float(a) for a in summary['alpha'].dropna().unique()))
    rows: list[dict[str, Any]] = []
    for idx in range(len(alphas) - 1):
        left_max = alphas[idx]
        right_min = alphas[idx + 1]
        left = summary[summary['alpha'] <= left_max].copy()
        right = summary[summary['alpha'] >= right_min].copy()
        boundary = (left_max + right_min) / 2.0
        left_unique = int(left['alpha'].nunique())
        right_unique = int(right['alpha'].nunique())
        if left_unique < min_alpha_per_side or right_unique < min_alpha_per_side:
            rows.append({'boundary_alpha': boundary, 'left_max_alpha': left_max, 'right_min_alpha': right_min, 'left_unique_alpha': left_unique, 'right_unique_alpha': right_unique, 'left_level': np.nan, 'right_level': np.nan, 'sse_total': np.nan, 'status': f'skip_need_{min_alpha_per_side}_alpha_each_side'})
            continue
        left_fit = plateau_fit_stats(left['relative_mean'])
        right_fit = plateau_fit_stats(right['relative_mean'])
        sse_total = left_fit['sse'] + right_fit['sse']
        rows.append({'boundary_alpha': boundary, 'left_max_alpha': left_max, 'right_min_alpha': right_min, 'left_unique_alpha': left_unique, 'right_unique_alpha': right_unique, 'left_level': left_fit['level'], 'right_level': right_fit['level'], 'level_gap': right_fit['level'] - left_fit['level'], 'abs_level_gap': abs(right_fit['level'] - left_fit['level']), 'sse_left': left_fit['sse'], 'sse_right': right_fit['sse'], 'sse_total': sse_total, 'sse_per_alpha': sse_total / (left_unique + right_unique), 'status': 'ok'})
    candidates = pd.DataFrame(rows)
    valid = candidates[candidates['status'] == 'ok'].dropna(subset=['sse_total']).copy()
    if valid.empty:
        return (candidates, {})
    best = valid.sort_values(['sse_total', 'abs_level_gap', 'boundary_alpha'], ascending=[True, False, True]).iloc[0].to_dict()
    return (candidates, best)


def alpha_positions(summary: pd.DataFrame) -> tuple[list[float], dict[float, int]]:
    alphas = sorted((float(a) for a in summary['alpha'].dropna().unique()))
    return (alphas, {alpha: idx for (idx, alpha) in enumerate(alphas)})


def draw_plateau(ax: plt.Axes, best: dict[str, Any], alpha_to_pos: dict[float, int], n_alpha: int) -> float | None:
    if not best:
        return None
    left_pos = alpha_to_pos.get(float(best['left_max_alpha']))
    right_pos = alpha_to_pos.get(float(best['right_min_alpha']))
    if left_pos is None or right_pos is None:
        return None
    boundary_pos = (left_pos + right_pos) / 2.0
    ax.hlines(float(best['left_level']), -0.38, boundary_pos, color=LOW_COLOR, lw=3.0, zorder=5)
    ax.hlines(float(best['right_level']), boundary_pos, n_alpha - 0.62, color=HIGH_COLOR, lw=3.0, zorder=5)
    ax.axvspan(-0.5, boundary_pos, color=LOW_COLOR, alpha=0.055, lw=0, zorder=0)
    ax.axvspan(boundary_pos, n_alpha - 0.5, color=HIGH_COLOR, alpha=0.06, lw=0, zorder=0)
    ax.axvline(boundary_pos, color='#626A70', lw=0.78, ls=(0, (1.5, 2.0)), zorder=4)
    return boundary_pos


def set_lift_ylim(ax: plt.Axes, summary: pd.DataFrame, best: dict[str, Any], compressed: bool=False, spread_col: str='relative_sem', top_pad_scale: float | None=None) -> None:
    vals = list(summary['relative_mean'].astype(float).replace([np.inf, -np.inf], np.nan).dropna())
    spread = summary[spread_col].astype(float) if spread_col in summary.columns else summary['relative_sem'].astype(float)
    vals.extend(summary['relative_mean'].astype(float).add(spread).dropna().tolist())
    vals.extend(summary['relative_mean'].astype(float).sub(spread).dropna().tolist())
    if best:
        vals.extend([float(best['left_level']), float(best['right_level'])])
    if not vals:
        ax.set_ylim(-0.1, 1.0)
        return
    lo = min(vals)
    hi = max(vals)
    span = max(hi - lo, 0.08)
    bottom_pad = 0.22 * span if compressed else 0.25 * span
    top_multiplier = top_pad_scale if top_pad_scale is not None else 0.55 if compressed else 0.7
    top_pad = top_multiplier * span
    ax.set_ylim(lo - bottom_pad, hi + top_pad)


def draw_probability_band(ax: plt.Axes, summary: pd.DataFrame, metric: str, color: str, label: str, linestyle: str | tuple[int, tuple[float, ...]]='-', marker: str='o', linewidth: float=1.15, marker_size: float=2.3, marker_edge_width: float=0.35, band_alpha: float=0.18) -> None:
    data = summary[summary['metric'] == metric].copy()
    if data.empty:
        return
    x = data['xpos'].astype(float).to_numpy()
    mean = data['mean'].astype(float).to_numpy()
    sem = data['sem'].astype(float).to_numpy()
    ax.fill_between(x, mean - sem, mean + sem, color=color, alpha=band_alpha, linewidth=0, zorder=2)
    ax.plot(x, mean, color=color, lw=linewidth, ls=linestyle, marker=marker, ms=marker_size, mec='white', mew=marker_edge_width, label=label, zorder=5)


def draw_relative_inset(parent_ax: plt.Axes, result: dict[str, Any], second_metric_label: str, mode: str, anchor: tuple[float, float, float, float]=(0.085, 0.555, 0.43, 0.36), trend_flatten: float=1.55) -> plt.Axes:
    summary = result['relative_summary'].copy()
    (alphas, alpha_to_pos) = alpha_positions(summary)
    summary['xpos'] = summary['alpha'].astype(float).map(alpha_to_pos)
    x = summary['xpos'].astype(float).to_numpy()
    y = summary['relative_mean'].astype(float).to_numpy()
    sem = summary['relative_sem'].astype(float).fillna(0.0).to_numpy()
    ax = parent_ax.inset_axes(anchor)
    ax.set_facecolor(INSET_FACE)
    ax.grid(True, axis='y', color='#E6E2DA', linewidth=0.42, alpha=0.86)
    ax.grid(False, axis='x')
    ax.set_axisbelow(True)
    for side in ['left', 'bottom', 'right', 'top']:
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color('#C8CED4')
        ax.spines[side].set_linewidth(0.58)
    ax.tick_params(axis='both', direction='out', colors=TEXT_COLOR, width=0.52, length=2.0, pad=1.2, labelsize=5.2)
    ax.set_xlim(-0.45, len(alphas) - 0.55)
    tick_idx = [0, len(alphas) // 2, len(alphas) - 1] if len(alphas) > 2 else list(range(len(alphas)))
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([f'{alphas[i]:.1f}' for i in tick_idx])
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel('$\\alpha$', fontsize=5.7, labelpad=0.2)
    ax.set_ylabel('')
    denom = 'P_2' if second_metric_label == 'P2' else 'P_0'
    ax.text(0.04, 0.96, f'$(P_1-{denom})/{denom}$', transform=ax.transAxes, ha='left', va='top', fontsize=5.2, color=TEXT_COLOR, zorder=9)
    if mode == 'trend':
        vals = np.concatenate([y - sem, y + sem])
        vals = vals[np.isfinite(vals)]
        if vals.size:
            mid = float(np.nanmean(y[np.isfinite(y)]))
            half_span = max(0.34, float(np.nanmax(np.abs(vals - mid))) * trend_flatten)
            ax.set_ylim(mid - half_span, mid + half_span)
        (lo, hi) = ax.get_ylim()
        lo = min(lo, -0.25)
        hi = max(hi, 0.5)
        tick_step = 0.5
    else:
        set_lift_ylim(ax, summary, result['relative_best'], compressed=True, spread_col='relative_sem', top_pad_scale=0.3)
        (lo, hi) = ax.get_ylim()
        lo = min(lo, -0.25)
        hi = max(hi, 0.5)
        tick_step = 0.5
    lo = np.floor(lo / tick_step) * tick_step
    hi = np.ceil(hi / tick_step) * tick_step
    if hi <= lo:
        hi = lo + tick_step
    ax.set_ylim(lo, hi)
    ax.yaxis.set_major_locator(MultipleLocator(tick_step))
    ax.vlines(x, y - sem, y + sem, color=SD_COLOR, lw=0.75, alpha=0.55, zorder=2)
    ax.plot(x, y, color=LIFT_COLOR, lw=1.05, marker='o', ms=2.3, mfc='white', mec=LIFT_COLOR, mew=0.55, zorder=5)
    if mode == 'plateau':
        draw_plateau(ax, result['relative_best'], alpha_to_pos, len(alphas))
        best = result['relative_best']
        if best:
            left = float(best['left_level'])
            right = float(best['right_level'])
            fold = right / left if abs(left) > 1e-12 else np.nan
            sse = float(best.get('sse_total', np.nan))
            ax.text(0.64, 0.08, f'fold = {fold:.2f}$\\times$', transform=ax.transAxes, ha='center', va='bottom', fontsize=5.9, fontweight='bold', color=TEXT_COLOR, zorder=8)
            ax.text(0.96, 0.82, f'SSE = {sse:.3f}', transform=ax.transAxes, ha='right', va='top', fontsize=5.9, fontweight='bold', color=TEXT_COLOR, zorder=8)
    else:
        finite = np.isfinite(x) & np.isfinite(y)
        if finite.sum() >= 1:
            mean_level = float(np.nanmean(y[finite]))
            ax.axhline(mean_level, color=TREND_COLOR, lw=1.45, zorder=6)
    return ax


def draw_probability_panel(ax: plt.Axes, result: dict[str, Any], label: str, panel_letter: str, panel_kind: str, second_metric_label: str, relative_mode: str, relative_anchor: tuple[float, float, float, float], trend_flatten: float=1.55) -> None:
    rel_summary = result['relative_summary'].copy()
    prob_summary = result['probability_summary'].copy()
    (alphas, alpha_to_pos) = alpha_positions(rel_summary)
    prob_summary['xpos'] = prob_summary['alpha'].astype(float).map(alpha_to_pos)
    style_axis(ax)
    ax.set_title(f'{label}: {panel_kind}', pad=5, fontweight='bold')
    ax.set_xlim(-0.55, len(alphas) - 0.45)
    ax.set_xticks(range(len(alphas)))
    ax.set_xticklabels([f'{a:.1f}' for a in alphas])
    ax.set_xlabel('$\\alpha$', labelpad=2.0)
    ax.set_ylabel('Probability')
    ax.set_ylim(0.0, 0.6)
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    comparison_color = P2_COLOR if second_metric_label == 'P2' else P0_COLOR
    comparison_linestyle = (0, (3.0, 1.4)) if second_metric_label == 'P2' else '-'
    comparison_marker = 's' if second_metric_label == 'P2' else 'o'
    draw_probability_band(ax, prob_summary, 'P1', P1_COLOR, '$P_1$', linewidth=2.15, marker_size=5.0, marker_edge_width=0.85, band_alpha=0.17)
    draw_probability_band(ax, prob_summary, second_metric_label, comparison_color, f'${second_metric_label}$', linestyle=comparison_linestyle, marker=comparison_marker, linewidth=2.05, marker_size=4.8, marker_edge_width=0.8, band_alpha=0.16)
    draw_relative_inset(ax, result, second_metric_label, mode=relative_mode, anchor=relative_anchor, trend_flatten=trend_flatten)
    ax.text(-0.115, 1.065, panel_letter, transform=ax.transAxes, ha='left', va='bottom', fontsize=14.5, fontweight='bold', clip_on=False)


def plot_figure(results: dict[str, dict[str, Any]], args: argparse.Namespace) -> tuple[Path, Path, Path]:
    set_refresh_figure_style()
    fig, axes = plt.subplots(2, 2, figsize=(args.fig_width, args.fig_height), dpi=320, sharex=False)
    relative_inset = (0.085, 0.595, 0.425, 0.335)
    draw_probability_panel(axes[0, 0], results["politics_total"], "Politics", "a", "all videos", "P0", relative_mode="plateau", relative_anchor=relative_inset)
    draw_probability_panel(axes[0, 1], results["entertainment_total"], "Entertainment", "b", "all videos", "P0", relative_mode="plateau", relative_anchor=relative_inset)
    draw_probability_panel(axes[1, 0], results["politics_preference"], "Politics", "c", "preferred videos", "P2", relative_mode="trend", relative_anchor=relative_inset, trend_flatten=2.45)
    draw_probability_panel(axes[1, 1], results["entertainment_preference"], "Entertainment", "d", "preferred videos", "P2", relative_mode="trend", relative_anchor=relative_inset)
    handles = [
        Line2D([0], [0], color=P1_COLOR, lw=1.3, marker="o", markersize=3.4, label=r"$P_1$"),
        Line2D([0], [0], color=P0_COLOR, lw=1.3, marker="o", markersize=3.4, label=r"$P_0$"),
        Line2D([0], [0], color=P2_COLOR, lw=1.3, ls=(0, (3.0, 1.4)), marker="s", markersize=3.4, label=r"$P_2$"),
        Line2D([0], [0], color=LIFT_COLOR, lw=1.1, marker="o", markerfacecolor="white", markeredgecolor=LIFT_COLOR, markersize=3.2, label=r"Inset: relative lift"),
        Line2D([0], [0], color=LOW_COLOR, lw=2.2, label="Inset: lower/higher plateau"),
        Line2D([0], [0], color=TREND_COLOR, lw=1.5, label="Inset: mean reference"),
    ]
    legend = fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.038), ncol=3, frameon=True, handlelength=1.95, columnspacing=1.25, borderpad=0.28)
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_edgecolor("#D8D8D8")
    legend.get_frame().set_linewidth(0.55)
    legend.get_frame().set_alpha(0.92)
    fig.tight_layout(rect=(0.0, 0.083, 1.0, 1.0), w_pad=1.85, h_pad=2.10)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_path = args.output_dir / f"{args.prefix}.png"
    pdf_path = args.output_dir / f"{args.prefix}.pdf"
    tiff_path = args.output_dir / f"{args.prefix}.tiff"
    fig.savefig(png_path, dpi=600, bbox_inches="tight")
    fig.savefig(pdf_path, dpi=600, bbox_inches="tight")
    fig.savefig(tiff_path, dpi=600, bbox_inches="tight")
    plt.close(fig)
    return png_path, pdf_path, tiff_path


def main() -> None:
    args = parse_args()
    results = calculate_figure_data(args)
    png_path, pdf_path, tiff_path = plot_figure(results, args)
    for name, result in results.items():
        print(f"[OK] {name}: rows={len(result['points'])}, bot_pairs={result['points']['bot_file'].nunique()}")
    print(f"[OK] PNG: {png_path}")
    print(f"[OK] PDF: {pdf_path}")
    print(f"[OK] TIFF: {tiff_path}")


if __name__ == "__main__":
    main()
