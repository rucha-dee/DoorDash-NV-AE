"""
Regenerate report_figures with DM Sans, DoorDash scarlet / cod gray / white,
and non-overlapping data labels. Overwrites the hashed filenames the markdown
report already references.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, NullFormatter

HERE = Path(__file__).resolve().parent
FIG_DIR = HERE / "report_figures"
FONT_DIR = HERE / "fonts"

# Existing hashed filenames referenced by the markdown report
FIG1 = FIG_DIR / "62a74f8c2cbec9911418398d67c1167606511e1b.png"
FIG2 = FIG_DIR / "f449d994e338469ad3e3a71afeb290be6c7ba03b.png"
FIG3 = FIG_DIR / "7cd541cc3ae96496f3677ade6e49cde9546d1d94.png"
FIG4 = FIG_DIR / "5c74dd3d36cba2b1798fea314d01da60553fb8db.png"
FIG5 = FIG_DIR / "8e1766ecb3c1a17350439608acf99f817ed59789.png"
FIG6 = FIG_DIR / "bbba604fdf7f1cf30f3bdd433a033a80ac152926.png"

SCARLET = "#EB1700"
WHITE = "#FFFFFF"
COD = "#191919"
GRAY_MID = "#4A4A4A"
GRAY_MUTED = "#8C8C8C"
GRAY_BAR = "#E4E4E4"
GRAY_LINE = "#D0D0D0"

DPI = 220
MIN_N_CAT = 300


FP_REG = None
FP_MED = None


def register_fonts() -> None:
    global FP_REG, FP_MED
    for ttf in FONT_DIR.glob("DMSans-*.ttf"):
        font_manager.fontManager.addfont(str(ttf))
    FP_REG = font_manager.FontProperties(fname=str(FONT_DIR / "DMSans-Regular.ttf"))
    FP_MED = font_manager.FontProperties(fname=str(FONT_DIR / "DMSans-Medium.ttf"))
    plt.rcParams.update(
        {
            "font.family": "DM Sans",
            "font.sans-serif": ["DM Sans", "DM Sans Medium"],
            "font.weight": "regular",
            "text.color": COD,
            "axes.labelcolor": COD,
            "axes.edgecolor": COD,
            "xtick.color": COD,
            "ytick.color": COD,
            "axes.titleweight": "medium",
            "axes.titlesize": 14,
            "axes.labelsize": 10,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 9,
            "figure.facecolor": WHITE,
            "axes.facecolor": WHITE,
            "savefig.facecolor": WHITE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save(fig, path: Path) -> None:
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.28, facecolor=WHITE)
    plt.close(fig)
    print(f"wrote {path.name}")


def draw_tracked_title(fig, x, y, text, *, fontsize, fontproperties, color, extra=0.0026) -> None:
    """Draw a left-aligned title with extra tracking (figure-fraction per glyph)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    cursor = x
    for ch in text:
        t = fig.text(
            cursor,
            y,
            ch,
            ha="left",
            va="top",
            fontsize=fontsize,
            fontproperties=fontproperties,
            color=color,
        )
        fig.canvas.draw()
        width = t.get_window_extent(renderer=renderer).width / fig.bbox.width
        cursor += width + (extra * 2.4 if ch == " " else extra)


def label_box(**kwargs):
    defaults = dict(
        facecolor=WHITE,
        edgecolor="none",
        alpha=0.92,
        pad=0.18,
    )
    defaults.update(kwargs)
    return defaults


def style_ax(ax) -> None:
    ax.tick_params(length=3.5, pad=4)
    ax.yaxis.label.set_color(COD)
    ax.xaxis.label.set_color(COD)
    if FP_REG is not None:
        ax.yaxis.label.set_fontproperties(FP_REG)
        ax.xaxis.label.set_fontproperties(FP_REG)
        ax.title.set_fontproperties(FP_MED)
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_fontproperties(FP_REG)


def fig1_fulfillment(item: pd.DataFrame) -> None:
    completed = item[item.WAS_CANCELLED == 0]
    stores = ["DashMart1", "Grocery1", "Grocery2", "Grocery3"]
    unrecovered, subbed, totals = [], [], []
    for s in stores:
        g = completed[completed.DELIV_STORE_NAME == s]
        miss = g.WAS_MISSING.mean() * 100
        sub = g.WAS_SUBBED.mean() * 100
        unrecovered.append(miss - sub)
        subbed.append(sub)
        totals.append(miss)

    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    x = np.arange(len(stores))
    w = 0.52
    ax.bar(x, unrecovered, w, color=SCARLET, label="Item missing, no substitute")
    ax.bar(x, subbed, w, bottom=unrecovered, color=COD, label="Item substituted")

    ymax = max(totals) * 1.22
    ax.set_ylim(0, ymax)
    ax.set_xticks(x, stores)
    ax.set_ylabel("% of requested items")
    ax.set_title("Item-level fulfillment gap by store", loc="left", pad=14, fontproperties=FP_MED)

    for i, tot in enumerate(totals):
        # Keep even the 0.2% DashMart label clear of the axis line.
        y = max(tot + ymax * 0.045, 2.4)
        ax.text(
            x[i],
            y,
            f"{tot:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="medium",
            color=COD,
            clip_on=False,
        )

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=2,
        frameon=False,
        handlelength=1.1,
    )
    style_ax(ax)
    fig.subplots_adjust(top=0.86, bottom=0.22, left=0.10, right=0.96)
    save(fig, FIG1)


def fig2_kpis(deliv: pd.DataFrame) -> None:
    stores = ["DashMart1", "Grocery1", "Grocery2", "Grocery3"]
    rows = []
    for s in stores:
        g = deliv[deliv.DELIV_STORE_NAME == s]
        gc = g[g.WAS_CANCELLED == 0]
        rows.append(
            {
                "store": s,
                "cancel": g.WAS_CANCELLED.mean() * 100,
                "late": gc.DELIV_IS_20_MIN_LATE.mean() * 100,
                "mi": gc.DELIV_MISSING_INCORRECT_REPORT_BINARY.mean() * 100,
            }
        )
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(11.4, 6.0))
    x = np.arange(len(stores)) * 1.25
    w = 0.28
    series = [
        ("cancel", "Cancellation rate", COD),
        ("late", "20+ min late rate", SCARLET),
        ("mi", "Missing/incorrect-item complaint rate", GRAY_MID),
    ]
    for i, (col, _lab, color) in enumerate(series):
        offset = (i - 1) * w
        ax.bar(x + offset, df[col], w, color=color, zorder=2)

    ax.set_ylim(0, 7.6)
    ax.set_xlim(x[0] - 0.7, x[-1] + 0.7)
    ax.set_xticks(x, stores)
    ax.set_ylabel("% of deliveries")
    ax.set_title("Order-experience KPIs by store", loc="left", pad=12)

    for i, (col, _lab, color) in enumerate(series):
        offset = (i - 1) * w
        for xi, val in zip(x, df[col]):
            ax.text(
                xi + offset,
                max(val + 0.18, 0.32),
                f"{val:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8,
                fontproperties=FP_REG,
                color=COD,
                clip_on=False,
                zorder=3,
                bbox=label_box(pad=0.12, alpha=1.0),
            )

    ax.legend(
        handles=[Patch(facecolor=c, label=lab) for _, lab, c in series],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=3,
        frameon=False,
        handlelength=1.1,
    )
    style_ax(ax)
    fig.subplots_adjust(top=0.86, bottom=0.22, left=0.10, right=0.96)
    save(fig, FIG2)


def _category_rates(completed_items: pd.DataFrame, min_n: int = MIN_N_CAT) -> pd.DataFrame:
    g = completed_items.groupby("ITEM_CATEGORY_GRP", as_index=False).agg(
        n=("WAS_MISSING", "size"),
        miss=("WAS_MISSING", "mean"),
    )
    g = g[g.ITEM_CATEGORY_GRP != "Other/Rare"]
    g = g[g.n >= min_n].copy()
    g["rate"] = g.miss * 100
    return g.sort_values("rate", ascending=True)


def _hbar_categories(df: pd.DataFrame, title: str, subtitle: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.4, max(6.2, 0.38 * len(df) + 2.2)))
    median = df.rate.median()
    colors = [SCARLET if r >= median else COD for r in df.rate]
    y = np.arange(len(df))
    ax.barh(y, df.rate, color=colors, height=0.68)

    xmax = df.rate.max() * 1.32
    ax.set_xlim(0, xmax)
    ax.set_yticks(y, df.ITEM_CATEGORY_GRP)
    ax.set_xlabel("% of requested items not received as originally ordered")
    style_ax(ax)
    # Figure-level header so title and subtitle have independent y positions
    # (ax.set_title + a 1.02 axes text used to share one pad and collide).
    fig.subplots_adjust(top=0.78, bottom=0.10, left=0.22, right=0.94)
    left = ax.get_position().x0
    draw_tracked_title(
        fig,
        left,
        0.980,
        title,
        fontsize=14.5 if len(title) < 55 else 13.5,
        fontproperties=FP_MED,
        color=COD,
        extra=0.0038 if len(title) < 55 else 0.0030,
    )
    fig.text(
        left,
        0.918,
        subtitle,
        ha="left",
        va="top",
        fontsize=9.5,
        fontproperties=FP_REG,
        color=GRAY_MID,
    )

    for yi, val in zip(y, df.rate):
        # Tiny bars (Ice Cream 0.1%) still get a label off the axis, not on it.
        ax.text(
            max(val + xmax * 0.022, 1.35),
            yi,
            f"{val:.1f}%",
            va="center",
            ha="left",
            fontsize=9,
            color=COD,
            clip_on=False,
        )

    save(fig, path)


def fig3_category_all(item: pd.DataFrame) -> None:
    completed = item[item.WAS_CANCELLED == 0]
    df = _category_rates(completed)
    _hbar_categories(
        df,
        "Item unfulfillment rate by category — all stores",
        "Categories with 300+ requests. Color split at the median: scarlet = above, gray = below.",
        FIG3,
    )


def fig4_category_grocery(item: pd.DataFrame) -> None:
    completed = item[(item.WAS_CANCELLED == 0) & (item.DELIV_STORE_NAME != "DashMart1")]
    df = _category_rates(completed)
    _hbar_categories(
        df,
        "Item unfulfillment rate by category — grocery partners only",
        "DashMart1 excluded. Channel-mix removed: Produce is now the best-fulfilled category.",
        FIG4,
    )


def fig5_clat(deliv: pd.DataFrame) -> None:
    completed = deliv[deliv.WAS_CANCELLED == 0].dropna(subset=["DELIV_CLAT"]).copy()
    bins = [-0.01, 1, 2, 3, 5, 8, 15, 1e9]
    labels = ["0–1", "1–2", "2–3", "3–5", "5–8", "8–15", "15+"]
    completed["bucket"] = pd.cut(completed.DELIV_CLAT, bins=bins, labels=labels)
    g = (
        completed.groupby("bucket", observed=True)
        .agg(n=("DELIVERY_UUID", "size"), late=("DELIV_IS_20_MIN_LATE", "mean"))
        .reindex(labels)
    )
    g["late_pct"] = g.late * 100

    fig, (ax_rate, ax_vol) = plt.subplots(
        2,
        1,
        figsize=(10.4, 7.0),
        sharex=True,
        gridspec_kw={"height_ratios": [1.45, 1.0], "hspace": 0.12},
    )
    x = np.arange(len(g))

    ax_rate.plot(
        x,
        g.late_pct,
        color=SCARLET,
        marker="o",
        markersize=7,
        linewidth=2.1,
        zorder=3,
    )
    ax_rate.set_ylabel("% delivered 20+ min late")
    ax_rate.set_ylim(0, 36)
    ax_rate.set_title("Longer Dasher acceptance time → higher lateness risk", loc="left", pad=10)
    for xi, val in zip(x, g.late_pct):
        ax_rate.text(
            xi,
            val + 1.4,
            f"{val:.0f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontproperties=FP_MED,
            color=SCARLET,
            clip_on=False,
        )
    style_ax(ax_rate)

    ax_vol.bar(x, g.n, color="#D6D6D6", width=0.62, zorder=1, edgecolor=WHITE, linewidth=0.4)
    ax_vol.set_ylabel("# of deliveries")
    ax_vol.set_xlabel("Dasher acceptance time (DELIV_CLAT), minutes")
    ax_vol.set_xticks(x, labels)
    ax_vol.set_ylim(0, g.n.max() * 1.32)
    for xi, n in zip(x, g.n):
        ax_vol.text(
            xi,
            n + g.n.max() * 0.045,
            f"{int(n):,}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontproperties=FP_REG,
            color=COD,
            clip_on=False,
        )
    style_ax(ax_vol)
    fig.subplots_adjust(top=0.90, bottom=0.10, left=0.12, right=0.96)
    save(fig, FIG5)


def fig6_complaint_or() -> None:
    # From py_m2_coefs.csv (clustered). Ordered by odds ratio descending.
    rows = [
        ("Delivery was 20+ min late", 2.413, 1.515, 3.843, True),
        ("Store: Grocery1 (vs DashMart1)", 2.136, 1.503, 3.036, True),
        ("Item unfulfilled rate (0 → 100%)", 2.099, 0.961, 4.584, False),
        ("Store: Grocery2/3 (vs DashMart1)", 1.614, 1.030, 2.528, True),
        ("Order includes alcohol", 1.195, 0.526, 2.716, False),
        ("Each add'l item requested", 1.103, 1.050, 1.159, True),
        ("Order includes perishable item", 1.089, 0.790, 1.499, False),
        ("Order value (+$1)", 0.993, 0.983, 1.003, False),
    ]
    labels, ors, lo, hi, sig = zip(*rows)
    y = np.arange(len(rows))[::-1]

    fig, ax = plt.subplots(figsize=(10.6, 6.4))
    ax.axvline(1.0, color=GRAY_LINE, linewidth=1.0, linestyle="--", zorder=0)

    for yi, or_, l, h, s in zip(y, ors, lo, hi, sig):
        color = SCARLET if s else GRAY_MUTED
        ax.plot([l, h], [yi, yi], color=color, linewidth=2.2, solid_capstyle="round", zorder=2)
        ax.scatter([or_], [yi], s=36, color=COD, zorder=3, linewidths=0)

    ax.set_yticks(y, labels)
    ax.set_xscale("log")
    ax.set_xlim(0.42, 9.5)
    ax.set_xlabel("Odds ratio (95% CI, log scale)")
    ax.set_title("What drives a missing/incorrect-item complaint?", loc="left", pad=12)
    ax.set_xticks([0.5, 1, 2, 4, 8])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="x", which="minor", length=0)

    # Labels sit to the right of each whisker, never on the interval.
    for yi, or_, h, s in zip(y, ors, hi, sig):
        star = "*" if s else ""
        # Short CIs (e.g. 1.10*) still need a gap from the marker, not just from hi.
        label_x = max(h * 1.18, or_ * 1.35)
        ax.text(
            label_x,
            yi,
            f"{or_:.2f}{star}",
            va="center",
            ha="left",
            fontsize=9.5,
            fontproperties=FP_REG,
            color=COD,
            clip_on=False,
        )

    ax.legend(
        handles=[
            Patch(facecolor=SCARLET, label="Significant (p < 0.05)"),
            Patch(facecolor=GRAY_MUTED, label="Not significant"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=2,
        frameon=False,
        handlelength=1.1,
    )
    style_ax(ax)
    fig.subplots_adjust(top=0.86, bottom=0.20, left=0.34, right=0.92)
    save(fig, FIG6)


def main() -> None:
    register_fonts()
    item = pd.read_csv(HERE / "item_level.csv", low_memory=False)
    deliv = pd.read_csv(HERE / "delivery_level.csv", low_memory=False)
    fig1_fulfillment(item)
    fig2_kpis(deliv)
    fig3_category_all(item)
    fig4_category_grocery(item)
    fig5_clat(deliv)
    fig6_complaint_or()


if __name__ == "__main__":
    main()
