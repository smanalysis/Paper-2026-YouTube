# Figure Reproduction Code

This directory contains the data and standalone scripts used to reproduce Figures 2–4, Figures S2–S10, and Table S3. By default, all scripts read only from the local `data/`, `stance_score/`, and `vector_similarity/` directories. Figures are saved to `figures/`. 
## Data Files

### `data/`

- `political-news_data.xlsx`: Step-level exposure data from the political-news experiments.
- `entertainment_data.xlsx`: Step-level exposure data from the entertainment experiments.

The scripts read the `data` worksheet and primarily use the following columns:

| Column | Description |
|---|---|
| `Group Name` | Experimental group name, such as `couplingRatio_0.3`, used to identify the behavioral-consistency parameter α. |
| `File Name` | Original log-file name corresponding to one bot-pair experimental record. |
| `Bot Name` | Bot-pair record identifier used to distinguish experimental replicates. |
| `step` | Interaction step, typically ranging from 0 to 149. |
| `master_exposure_last` | Videos shown to Account A in the final page state of the step. Each video may contain fields such as `id`, `title`, `channel`, and `duration`. |
| `servant_exposure_last` | Videos shown to Account B in the final page state of the step, with the same structure as above. |
| `[CATEGORY]` | Mapping from video IDs to YouTube category IDs; for example, 25 denotes News & Politics and 24 denotes Entertainment. |

### `stance_score/`

- `political-news_stance_score.json`
- `entertainment_stance_score.json`

Each JSON object is keyed by video ID. Each record contains `stance_label` (one of five ordered stance categories), `stance_score` (a continuous score from −1 to 1), and `confidence` (model confidence).

### `vector_similarity/`

- `political-news_video_vectors_bge_m3.json`
- `entertainment_video_vectors_bge_m3.json`

Each JSON object is keyed by video ID, with the corresponding value containing the 1,024-dimensional BGE-M3 semantic vector for that video.

## Python Scripts

| Script | Purpose |
|---|---|
| `plot_figure2.py` | Plots the stepwise Jaccard similarity of political and entertainment recommendations, with insets showing direct similarity over the final 50 steps. |
| `plot_figure3.py` | Produces Figure 3, combining common-video/channel time lags, semantic similarity, and stance similarity. |
| `plot_figure4.py` | Computes probability metrics, relative lifts, and segmented thresholds across α and produces the four-panel Figure 4. |
| `plot-figureS2.py` | Plots the video-category composition of Accounts A and B in the political and entertainment experiments. |
| `plot-figureS3-S6.py` | Plots the stepwise preferred-category share for Accounts A and B in the political and entertainment experiments. |
| `plot-figureS7-S8.py` | Plots stance-label composition, stance-score distributions, and confidence distributions for political and entertainment videos. |
| `plot-figureS9-S10.py` | Plots the stepwise mean stance scores of Accounts A and B in the political and entertainment experiments. |
| `summarize_tabS3.py` | Summarizes the number of bot-pair records and unique videos exposed to Accounts A and B by experiment and α. |

Plotting scripts save 600-dpi PNG, PDF, and TIFF files. `summarize_tabS3.py` produces `tabS3.csv`.

## Experiment System Code

In `system` directory, We have provided the Java source code (in `src` directory) for our experimental system along with the Maven dependency file (`pom.xml`) for the required libraries. Please note that we utilize the JxBrowser toolkit, which is a commercial package, so we cannot share it directly on GitHub. If you need to run the code, please email us at myong@bnu.edu.cn, and we will provide the necessary JAR files (put in `lib` directory) and license key (replace empty system property in `BrowserPanel.java`).