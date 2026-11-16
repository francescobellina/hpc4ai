#!/usr/bin/env python3
"""Figure del capitolo 7 (Programmare con MPI): schemi disegnati con matplotlib.

    python codes/teoria/figure_mpi.py

Salva in content/teoria/figures/: mpi-bloccante-non-bloccante.png,
mpi-collettive.png, mpi-halo-1d.png.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

FIG = Path(__file__).resolve().parents[2] / "content/teoria/figures"

# Stessa palette delle figure dell'esercizio 5 (tema chiaro).
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
CRITICAL, GOOD = "#d03b3b", "#0ca30c"
LIGHT = "#efeeea"


def box(ax, x0, x1, y, text, color, h=0.5, hatch=None, dashed=False, fill=True, fontsize=8, textcolor=INK):
    ax.add_patch(Rectangle((x0, y - h / 2), x1 - x0, h,
                           facecolor=(color if fill else SURFACE), edgecolor=(color if dashed else SURFACE),
                           linewidth=1.5, linestyle="--" if dashed else "-", hatch=hatch, alpha=1.0))
    ax.text((x0 + x1) / 2, y, text, ha="center", va="center", fontsize=fontsize, color=textcolor)


def arrow(ax, a, b, color=INK2, rad=0.0, style="-|>", lw=1.2):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=10, color=color, linewidth=lw,
                                 connectionstyle=f"arc3,rad={rad}"))


def clean(ax):
    ax.set_facecolor(SURFACE)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def fig_blocking(path):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 2.9), facecolor=SURFACE)
    lanes = {0: 1.0, 1: 0.0}

    ax = axes[0]
    clean(ax)
    ax.set_title("Bloccante: MPI_Send, poi MPI_Recv (messaggio grande)", fontsize=9, color=INK, loc="left")
    for r, y in lanes.items():
        ax.text(-0.2, y, f"rank {r}", ha="right", va="center", fontsize=9, color=INK)
        box(ax, 0.3, 2.0, y, "MPI_Send", BLUE, textcolor=SURFACE)
        box(ax, 2.05, 6.7, y, "aspetta che l'altro rank\nchiami MPI_Recv", "#cfe0f6", hatch="///")
        box(ax, 6.9, 9.7, y, "MPI_Recv\n(mai raggiunta)", AQUA, dashed=True, fill=False, textcolor=INK2)
    ax.text(4.15, 0.5, "✖ deadlock: ognuno aspetta l'altro", ha="center", va="center", fontsize=8.5,
            color=CRITICAL, fontweight="bold")
    arrow(ax, (0.3, -0.65), (9.7, -0.65))
    ax.text(9.7, -0.85, "tempo", ha="right", va="center", fontsize=8, color=INK2)
    ax.set_xlim(-1.3, 10)
    ax.set_ylim(-1.0, 1.5)

    ax = axes[1]
    clean(ax)
    ax.set_title("Non bloccante: MPI_Irecv, MPI_Isend, poi MPI_Waitall", fontsize=9, color=INK, loc="left")
    for r, y in lanes.items():
        ax.text(-0.2, y, f"rank {r}", ha="right", va="center", fontsize=9, color=INK)
        box(ax, 0.3, 1.5, y, "Irecv", AQUA)
        box(ax, 1.55, 2.75, y, "Isend", BLUE, textcolor=SURFACE)
        box(ax, 2.8, 6.2, y, "calcolo indipendente", LIGHT)
        box(ax, 6.25, 8.0, y, "Waitall", YELLOW)
        ax.text(8.15, y, "✔ dati pronti", ha="left", va="center", fontsize=8, color=GOOD)
    arrow(ax, (2.75, 0.72), (6.6, 0.25), color=BLUE)
    arrow(ax, (2.75, 0.28), (6.6, 0.75), color=BLUE)
    ax.text(4.5, 0.5, "i messaggi\nviaggiano", ha="center", va="center", fontsize=7.5, color=INK2,
            bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1))
    arrow(ax, (0.3, -0.65), (9.7, -0.65))
    ax.text(9.7, -0.85, "tempo", ha="right", va="center", fontsize=8, color=INK2)
    ax.set_xlim(-1.3, 10)
    ax.set_ylim(-1.0, 1.5)

    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_collectives(path):
    ops = [
        ("MPI_Bcast", ["42", "–", "–", "–"], ["42", "42", "42", "42"]),
        ("MPI_Scatter", ["10 20 30 40", "–", "–", "–"], ["10", "20", "30", "40"]),
        ("MPI_Gather", ["10", "20", "30", "40"], ["10 20 30 40", "–", "–", "–"]),
        ("MPI_Reduce (SUM)", ["1", "2", "3", "4"], ["10", "–", "–", "–"]),
        ("MPI_Allreduce (SUM)", ["1", "2", "3", "4"], ["10", "10", "10", "10"]),
    ]
    fig, axes = plt.subplots(1, len(ops), figsize=(10.4, 2.9), facecolor=SURFACE)
    for ax, (name, before, after) in zip(axes, ops):
        clean(ax)
        ax.set_title(name, fontsize=9, color=INK)
        for r in range(4):
            y = 3 - r
            for x0, vals in ((0.0, before), (2.4, after)):
                v = vals[r]
                filled = v != "–"
                ax.add_patch(Rectangle((x0, y - 0.38), 1.9, 0.76, facecolor=("#dbe8f8" if filled else SURFACE),
                                       edgecolor=(BLUE if filled else GRID), linewidth=1))
                ax.text(x0 + 0.95, y, v, ha="center", va="center", fontsize=7.5 if len(v) > 3 else 9,
                        color=INK if filled else INK2)
            if ax is axes[0]:
                ax.text(-0.15, y, f"rank {r}", ha="right", va="center", fontsize=8, color=INK)
        arrow(ax, (1.95, 1.5), (2.35, 1.5))
        ax.text(0.95, -0.75, "prima", ha="center", fontsize=8, color=INK2)
        ax.text(3.35, -0.75, "dopo", ha="center", fontsize=8, color=INK2)
        ax.set_xlim(-1.2 if ax is axes[0] else -0.1, 4.4)
        ax.set_ylim(-1.0, 3.6)
    fig.text(0.5, 0.01, "Radice = rank 0.  “–” = valore non specificato (i buffer di input non vengono cancellati).",
             ha="center", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_halo(path):
    fig, ax = plt.subplots(figsize=(9.6, 2.6), facecolor=SURFACE)
    clean(ax)
    owned = 4
    width = owned + 2
    gap = 1.6
    for r in range(3):
        x0 = r * (width + gap)
        ax.text(x0 + width / 2, 1.05, f"rank {r}", ha="center", fontsize=9, color=INK)
        for c in range(width):
            ghost = c in (0, width - 1)
            ax.add_patch(Rectangle((x0 + c, 0), 1, 0.7, facecolor=(SURFACE if ghost else "#dbe8f8"),
                                   edgecolor=(INK2 if ghost else BLUE), linewidth=1, hatch="///" if ghost else None,
                                   linestyle="--" if ghost else "-"))
            label = f"u[{c}]" if ghost else str(r * owned + c - 1)
            ax.text(x0 + c + 0.5, 0.35, label, ha="center", va="center", fontsize=7 if ghost else 8,
                    color=INK2 if ghost else INK,
                    bbox=dict(facecolor=SURFACE, edgecolor="none", pad=0.5) if ghost else None)
        if r < 2:
            nx = (r + 1) * (width + gap)
            # ultimo valore proprio di r -> halo sinistro di r+1
            arrow(ax, (x0 + width - 1.5, 0.72), (nx + 0.5, 0.72), color=BLUE, rad=-0.45)
            # primo valore proprio di r+1 -> halo destro di r
            arrow(ax, (nx + 1.5, -0.02), (x0 + width - 0.5, -0.02), color=ORANGE, rad=-0.45)
    ax.text(0.5, -0.55, "MPI_PROC_NULL:\nresta al valore del bordo", ha="center", va="top", fontsize=7.5, color=INK2)
    last = 2 * (width + gap) + width - 0.5
    ax.text(last, -0.55, "MPI_PROC_NULL:\nresta al valore del bordo", ha="center", va="top", fontsize=7.5, color=INK2)
    ax.text(10.8, 1.75, "→ TAG_TO_RIGHT: il bordo destro va nell'halo sinistro del vicino", fontsize=8,
            color=BLUE, ha="center")
    ax.text(10.8, -0.85, "← TAG_TO_LEFT: il bordo sinistro va nell'halo destro del vicino", fontsize=8,
            color=ORANGE, ha="center")
    ax.add_patch(Rectangle((3.5, -1.4), 0.5, 0.3, facecolor="#dbe8f8", edgecolor=BLUE))
    ax.text(4.15, -1.25, "cella propria (indice globale)", fontsize=7.5, color=INK2, va="center")
    ax.add_patch(Rectangle((15.0, -1.4), 0.5, 0.3, facecolor=SURFACE, edgecolor=INK2, hatch="///", linestyle="--"))
    ax.text(15.65, -1.25, "cella fantasma (halo)", fontsize=7.5, color=INK2, va="center")
    ax.set_xlim(-0.5, 22.6)
    ax.set_ylim(-1.55, 2.0)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig_blocking(FIG / "mpi-bloccante-non-bloccante.png")
    fig_collectives(FIG / "mpi-collettive.png")
    fig_halo(FIG / "mpi-halo-1d.png")
    print("Figure in content/teoria/figures/: mpi-bloccante-non-bloccante.png, mpi-collettive.png, mpi-halo-1d.png")


if __name__ == "__main__":
    main()
