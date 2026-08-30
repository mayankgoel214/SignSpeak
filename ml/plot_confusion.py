"""Render eval/results.json's leave-one-signer-out confusion matrix to a PNG.

Two deliberate choices, the same ones the live page makes, so the committed image
and the site tell the same story:

  The diagonal is drawn in neutral grey. A single colour ramp across the whole
  matrix is dominated by the diagonal -- every correct answer -- and the errors,
  which are the only reason to look at a confusion matrix, disappear into the
  background.

  The error ramp is one hue, not a rainbow, and it is capped at 20% so a 5%
  mistake is still visible. A perceptually uneven multi-hue map invents structure
  that is not in the data.

Usage:  python ml/plot_confusion.py
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

BG = "#141413"
SURFACE = "#1a1a19"
INK = "#f3f2ed"
INK_DIM = "#a9a99e"
INK_FAINT = "#8c8c81"
GRID = "#34342f"
DIAGONAL = "#55554d"
EMPTY = "#212120"
ERROR_CAP = 0.20

# One hue, low to high, matching web/charts.js.
AMBER = ["#212120", "#33200a", "#563608", "#83520d", "#b87413", "#e39724", "#f5bb64"]


def font(size, weight="normal"):
    path = os.path.join(ROOT, "scripts", "fonts", "InterVariable.ttf")
    if os.path.exists(path):
        return fm.FontProperties(fname=path, size=size, weight=weight)
    return fm.FontProperties(size=size, weight=weight)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "eval", "results.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "eval", "confusion-matrix.png")
    with open(src) as f:
        r = json.load(f)

    classes = [c.upper() for c in r["dataset"]["classes"]]
    si = r["signer_independent"]
    cm = np.array(si["confusion_matrix"], dtype=float)
    n = len(classes)

    rows = cm.sum(axis=1, keepdims=True)
    share = np.divide(cm, rows, out=np.zeros_like(cm), where=rows > 0)

    ramp = LinearSegmentedColormap.from_list("amber", AMBER)

    fig, ax = plt.subplots(figsize=(10, 10.2))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)

    for i in range(n):
        for j in range(n):
            value = share[i, j]
            if i == j:
                # Correct answers, deliberately recessive: alpha carries the value
                # so the diagonal reads as present without competing with errors.
                colour = DIAGONAL
                alpha = 0.25 + 0.75 * value
            else:
                colour = ramp(min(value / ERROR_CAP, 1.0)) if value > 0 else EMPTY
                alpha = 1.0
            ax.add_patch(
                plt.Rectangle((j - 0.44, i - 0.44), 0.88, 0.88, facecolor=colour, alpha=alpha, linewidth=0)
            )

    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(n - 0.4, -0.6)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(classes, fontproperties=font(9), color=INK_FAINT)
    ax.set_yticklabels(classes, fontproperties=font(9), color=INK_FAINT)
    ax.tick_params(length=0, pad=6)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_xlabel("predicted", fontproperties=font(10.5), color=INK_DIM, labelpad=10)
    ax.set_ylabel("true letter", fontproperties=font(10.5), color=INK_DIM, labelpad=10)

    # Title and subtitle are placed by hand rather than through set_title, so the
    # two cannot land on top of each other as the figure size changes.
    LEFT = 0.115
    worst = si["top_confusions"][0]
    fig.text(
        LEFT, 0.950, f"{si['mean_accuracy']:.1%} on a signer the model never saw",
        fontproperties=font(18, "semibold"), color=INK, ha="left", va="center",
    )
    fig.text(
        LEFT, 0.916,
        f"Leave-one-signer-out, {len(si['folds'])} folds, {si['n_test_total']:,} samples each held out exactly once",
        fontproperties=font(9.5), color=INK_DIM, ha="left", va="center",
    )
    fig.text(
        LEFT, 0.893,
        f"per-fold {si['min_accuracy']:.1%}–{si['max_accuracy']:.1%} · "
        f"worst pair {worst['true'].upper()}→{worst['predicted'].upper()} at {worst['rate']:.1%} of all "
        f"{worst['true'].upper()}",
        fontproperties=font(9.5), color=INK_FAINT, ha="left", va="center",
    )

    # Legend: the error ramp, and the diagonal's separate treatment.
    SWATCH_Y, LABEL_Y = 0.030, 0.037
    fig.text(LEFT, 0.062, "error rate", fontproperties=font(9), color=INK_FAINT, va="center")
    for k, colour in enumerate(AMBER):
        fig.patches.append(
            plt.Rectangle((LEFT + k * 0.022, SWATCH_Y), 0.020, 0.014,
                          facecolor=colour, transform=fig.transFigure, figure=fig, linewidth=0)
        )
    fig.text(LEFT + len(AMBER) * 0.022 + 0.010, LEFT and LABEL_Y,
             f"0 → {ERROR_CAP:.0%}+", fontproperties=font(9), color=INK_FAINT, va="center")
    fig.patches.append(
        plt.Rectangle((0.50, SWATCH_Y), 0.020, 0.014, facecolor=DIAGONAL,
                      transform=fig.transFigure, figure=fig, linewidth=0)
    )
    fig.text(0.528, LABEL_Y, "correct (diagonal, deliberately recessive)",
             fontproperties=font(9), color=INK_FAINT, va="center")

    fig.subplots_adjust(left=LEFT, right=0.97, top=0.855, bottom=0.125)
    fig.savefig(out, dpi=150, facecolor=BG)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
