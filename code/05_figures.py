#!/usr/bin/env python3
"""05_figures.py - figures for the README and data descriptor. Pass --final to remove the DRAFT stamp."""
import os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(ROOT, "data", "processed"); F = os.path.join(ROOT, "figures")
FINAL = "--final" in sys.argv
BLUE, ORANGE, INK, MUTED, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlelocation": "left", "axes.titlecolor": INK})
insp = pd.read_csv(os.path.join(P, "ahcp_inspections.csv.gz"), usecols=["program", "inspection_year", "inspection_score", "protocol", "ahcp_inspection_id"])
snap = pd.read_csv(os.path.join(P, "ahcp_snapshots.csv.gz"), usecols=["vintage", "inspection_date"], parse_dates=["inspection_date"])


def finish(fig, name, caption):
    fig.text(0.01, 0.01, caption, fontsize=8, color=MUTED, ha="left", va="bottom")
    if not FINAL: fig.text(0.99, 0.985, "DRAFT - not verified", fontsize=9, color="#b3261e", ha="right", va="top", weight="bold")
    fig.savefig(os.path.join(F, name), dpi=180); plt.close(fig)


# Figure 1: coverage by inspection year, one panel per program (shared x, independent meaning, same y scale)
yrs = np.arange(2000, 2027); yr = insp.groupby(["program", "inspection_year"]).size()
fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, sharey=True)
for ax, (prog, label, col) in zip(axes, [("MF", "Multifamily", BLUE), ("PH", "Public housing", ORANGE)]):
    v = [int(yr.get((prog, y), 0)) for y in yrs]
    ax.bar(yrs, v, width=0.72, color=col, linewidth=0)
    ax.set_title(f"{label}: {sum(v):,} unique inspections"); ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x):,}")); ax.set_ylabel("Inspections")
    ax.axvspan(2009.55, 2012.45, color=GRID, alpha=0.6, linewidth=0)
axes[0].text(2011, max(yr) * 0.88, "No published file\ncovers 2010-2012", ha="center", va="center", fontsize=9, color=MUTED)
axes[0].annotate("Pandemic pause", xy=(2020.5, 2600), xytext=(2020.5, max(yr) * 0.55), ha="center", fontsize=9, color=MUTED, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
axes[1].set_xticks(yrs[::2]); axes[1].set_xlabel("Inspection year")
fig.tight_layout(rect=(0, 0.05, 1, 0.97))
finish(fig, "fig1_coverage_by_year.png", "AHCP v1.0. Unique inspections reconstructed from nine HUD score-file vintages (2011-2026). Source: HUD PD&R Physical Inspection Scores.")

# Figure 2: score distributions by protocol (share of inspections per 5-point band)
bins = np.arange(0, 105, 5); mid = bins[:-1] + 2.5
fig, ax = plt.subplots(figsize=(9, 4.4))
recent = insp[insp.inspection_year >= 2013]
for prot, col in (("UPCS", BLUE), ("NSPIRE", ORANGE)):
    s = recent[recent.protocol == prot].inspection_score.clip(upper=99.99)
    h = np.histogram(s, bins=bins)[0] / len(s) * 100
    ax.plot(mid, h, color=col, linewidth=2, marker="o", markersize=4, label=f"{prot} (n = {len(s):,})")
    ax.text(mid[-1] + 1.5, h[-1], prot, color=INK, va="center", fontsize=9)
ax.axvline(60, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3))); ax.text(59, ax.get_ylim()[1] * 0.92, "60 = passing", ha="right", fontsize=9, color=MUTED)
ax.set_xlim(0, 108); ax.set_xticks(bins[::2]); ax.set_xlabel("Inspection score (5-point bands)"); ax.set_ylabel("Share of inspections (%)")
ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.legend(frameon=False, loc="upper left")
ax.set_title("UPCS and NSPIRE scores are distributed differently")
fig.tight_layout(rect=(0, 0.06, 1, 0.97))
finish(fig, "fig2_score_distribution_by_protocol.png", "AHCP v1.0. Inspections dated 2013 onward. Scores are as published by HUD; AHCP does not rescale across protocols.")

# Figure 3: which inspection years each vintage lists (the rolling window)
snap["year"] = snap.inspection_date.dt.year
m = snap.groupby(["vintage", "year"]).size().unstack(fill_value=0).reindex(columns=yrs, fill_value=0)
fig, ax = plt.subplots(figsize=(9, 4.2))
cmap = LinearSegmentedColormap.from_list("seq", [SURF, "#bcd4f2", BLUE, "#123a6b"])
im = ax.imshow(np.where(m.values == 0, np.nan, m.values), aspect="auto", cmap=cmap, vmin=0)
ax.set_yticks(range(len(m.index))); ax.set_yticklabels(m.index); ax.set_xticks(range(0, len(yrs), 2)); ax.set_xticklabels(yrs[::2])
ax.set_xticks(np.arange(-.5, len(yrs), 1), minor=True); ax.set_yticks(np.arange(-.5, len(m.index), 1), minor=True)
ax.grid(which="minor", color=SURF, linewidth=2); ax.tick_params(which="both", length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_xlabel("Inspection year"); ax.set_ylabel("Score-file vintage")
cb = fig.colorbar(im, ax=ax, pad=0.02); cb.set_label("Rows listed", color=MUTED); cb.outline.set_visible(False)
ax.set_title("Each vintage lists only recent inspections; stacking them rebuilds the history")
fig.tight_layout(rect=(0, 0.06, 1, 0.97))
finish(fig, "fig3_vintage_window.png", "AHCP v1.0. Rows in each HUD score file by inspection year, both programs. Blank cells: no rows.")
print("figures written", "(final)" if FINAL else "(draft)")
