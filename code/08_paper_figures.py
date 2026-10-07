#!/usr/bin/env python3
"""08_paper_figures.py - vector figures for the article (paper/figs/*.pdf), sized for a two-column page."""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(ROOT, "data", "processed"); F = os.path.join(ROOT, "paper", "figs")
os.makedirs(F, exist_ok=True)
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 7.5, "axes.edgecolor": "#9a9993", "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 8, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "legend.fontsize": 7, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
COL, DBL = 3.45, 7.1
insp = pd.read_csv(os.path.join(P, "ahcp_inspections.csv.gz"), parse_dates=["inspection_date", "prev_inspection_date"],
                   usecols=["program", "inspection_year", "inspection_score", "protocol", "inspection_date", "prev_inspection_date", "prev_inspection_score", "score_change", "protocol_change", "score_conflict", "ahcp_inspection_id"])
snap = pd.read_csv(os.path.join(P, "ahcp_snapshots.csv.gz"), usecols=["vintage", "inspection_date", "ahcp_inspection_id", "inspection_score"], parse_dates=["inspection_date"])
kfmt = FuncFormatter(lambda x, _: f"{int(x/1000)}k" if x >= 1000 else f"{int(x)}")
yrs = np.arange(2000, 2027)

# Fig: coverage by year
yr = insp.groupby(["program", "inspection_year"]).size()
fig, axes = plt.subplots(2, 1, figsize=(COL, 3.1), sharex=True, sharey=True)
for ax, (prog, label, col) in zip(axes, [("MF", "(a) Multifamily", BLUE), ("PH", "(b) Public housing", ORANGE)]):
    v = [int(yr.get((prog, y), 0)) for y in yrs]
    ax.bar(yrs, v, width=0.7, color=col, linewidth=0); ax.set_title(label); ax.yaxis.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(kfmt); ax.set_ylabel("Unique inspections"); ax.axvspan(2009.55, 2012.45, color=GRID, alpha=0.7, linewidth=0)
axes[0].text(2011, 12500, "no published\nfile", ha="center", va="center", fontsize=6.5, color=MUTED)
axes[1].text(2020.5, 6500, "pandemic\npause", ha="center", va="center", fontsize=6.5, color=MUTED)
axes[1].annotate("", xy=(2020.5, 1300), xytext=(2020.5, 5200), arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
axes[1].set_xticks(yrs[::4]); axes[1].set_xlabel("Inspection year"); fig.tight_layout(h_pad=0.6); fig.savefig(os.path.join(F, "coverage.pdf")); plt.close(fig)

# Fig: vintage window heat map
snap["year"] = snap.inspection_date.dt.year
m = snap.groupby(["vintage", "year"]).size().unstack(fill_value=0).reindex(columns=yrs, fill_value=0)
fig, ax = plt.subplots(figsize=(COL, 2.25))
cmap = LinearSegmentedColormap.from_list("seq", ["#eef3fb", "#bcd4f2", BLUE, "#123a6b"])
im = ax.imshow(np.where(m.values == 0, np.nan, m.values), aspect="auto", cmap=cmap, vmin=0)
ax.set_yticks(range(len(m.index))); ax.set_yticklabels(m.index); ax.set_xticks(range(0, len(yrs), 4)); ax.set_xticklabels(yrs[::4])
ax.set_xticks(np.arange(-.5, len(yrs), 1), minor=True); ax.set_yticks(np.arange(-.5, len(m.index), 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.2); ax.tick_params(which="both", length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_xlabel("Inspection year"); ax.set_ylabel("Score-file vintage")
cb = fig.colorbar(im, ax=ax, pad=0.02, format=kfmt); cb.set_label("Rows listed"); cb.outline.set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(F, "window.pdf")); plt.close(fig)

# Fig: score distributions (double column): 5-point bands and integer detail around the pass mark
rec = insp[insp.inspection_year >= 2013]
fig, axes = plt.subplots(1, 2, figsize=(DBL, 2.3), gridspec_kw={"width_ratios": [1.15, 1]})
bins = np.arange(0, 105, 5); mid = bins[:-1] + 2.5
for prot, col, mk in (("UPCS", BLUE, "o"), ("NSPIRE", ORANGE, "s")):
    s = rec[rec.protocol == prot].inspection_score
    h = np.histogram(s.clip(upper=99.99), bins=bins)[0] / len(s) * 100
    axes[0].plot(mid, h, color=col, linewidth=1.4, marker=mk, markersize=3, label=f"{prot} (n = {len(s):,})")
    axes[0].text(mid[-1] + 1.5, h[-1], prot, color=INK, va="center", fontsize=7)
    k = np.arange(45, 76); hh = np.array([(s.round() == x).mean() * 100 for x in k])
    axes[1].plot(k, hh, color=col, linewidth=1.4, marker=mk, markersize=3, label=prot)
axes[0].set_xlim(0, 112); axes[0].set_xticks(bins[::2]); axes[0].set_xlabel("Inspection score (5-point bands)"); axes[0].set_ylabel("Share of inspections (%)")
axes[0].set_title("(a) Full range"); axes[0].legend(frameon=False, loc="upper left")
axes[1].set_xlabel("Inspection score (integer)"); axes[1].set_ylabel("Share of inspections (%)"); axes[1].set_title("(b) Around the pass mark")
axes[1].annotate("NSPIRE scores of 59", xy=(59, float((rec[rec.protocol == "NSPIRE"].inspection_score == 59).mean() * 100)), xytext=(47, 2.0), fontsize=7, color=INK,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
axes[1].legend(frameon=False, loc="upper right")
for ax in axes:
    ax.axvline(60, color=MUTED, linewidth=0.6, linestyle=(0, (3, 3))); ax.yaxis.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
fig.tight_layout(w_pad=1.5); fig.savefig(os.path.join(F, "scores.pdf")); plt.close(fig)

# Fig: change between consecutive inspections, by pair type
pairs = insp[insp.prev_inspection_score.notna() & (insp.prev_inspection_date.dt.year >= 2013)]
uu = pairs[(pairs.protocol == "UPCS") & (pairs.protocol_change == 0)].score_change
un = pairs[(pairs.protocol == "NSPIRE") & (pairs.protocol_change == 1)].score_change
fig, ax = plt.subplots(figsize=(COL, 2.2)); b = np.arange(-60, 65, 5); mb = b[:-1] + 2.5
for s, col, mk, lab in ((uu, BLUE, "o", "UPCS to UPCS"), (un, ORANGE, "s", "UPCS to NSPIRE")):
    ax.plot(mb, np.histogram(s.clip(-59.9, 59.9), bins=b)[0] / len(s) * 100, color=col, linewidth=1.4, marker=mk, markersize=3, label=f"{lab}\n(n = {len(s):,})")
ax.axvline(0, color=MUTED, linewidth=0.6, linestyle=(0, (3, 3))); ax.yaxis.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
ax.set_xlabel("Score change from previous inspection (points)"); ax.set_ylabel("Share of pairs (%)"); ax.set_ylim(0, 26); ax.legend(frameon=False, loc="upper left", labelspacing=0.7, borderaxespad=0.2)
fig.tight_layout(); fig.savefig(os.path.join(F, "change.pdf")); plt.close(fig)

# Fig: cross-vintage score revisions
fl = snap.sort_values(["ahcp_inspection_id", "vintage"]).groupby("ahcp_inspection_id").inspection_score.agg(["first", "last"])
d = (fl["last"] - fl["first"]); d = d[d != 0]
fig, ax = plt.subplots(figsize=(COL, 1.9)); b = np.arange(-20, 60, 4)
ax.bar(b[:-1] + 2, np.histogram(d.clip(-19.9, 55.9), bins=b)[0], width=3.4, color=BLUE, linewidth=0)
ax.axvline(0, color=MUTED, linewidth=0.6, linestyle=(0, (3, 3))); ax.yaxis.grid(True, color=GRID, linewidth=0.5); ax.set_axisbelow(True)
ax.set_xlabel("Latest listed score minus earliest listed score (points)"); ax.set_ylabel("Inspections")
fig.tight_layout(); fig.savefig(os.path.join(F, "revisions.pdf")); plt.close(fig)
print("paper figures written")
