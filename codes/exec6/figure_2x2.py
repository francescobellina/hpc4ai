#!/usr/bin/env python3
"""Figure del caso 2 × 2 della consegna (Esercitazione 6): iterazione di Jacobi a mano.

    python figure_2x2.py

Calcolo esatto (frazioni) dell'aggiornamento di Jacobi per l'immagine con righe
(0, 1) e (1, 0) e lambda = 1, senza usare il programma del corso: è la previsione
teorica da confrontare con l'output di denoise_serial. Salva in
content/esercizi/figures/ le figure es06-2x2-passo.png (calcolo pixel per pixel
della prima iterazione), es06-2x2-iterazioni.png (u^(t) fino al punto fisso) e
es06-2x2-delta.png (variazione massima contro t), e stampa la tabella dei valori.
"""
from fractions import Fraction as F
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "content/esercizi/figures"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"

LAM = F(1)
f = [[F(0), F(1)], [F(1), F(0)]]
H, W = 2, 2


def neighbours(i, j):
    return [(k, l) for k, l in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if 0 <= k < H and 0 <= l < W]


def jacobi(u):
    """Un passo di Jacobi: legge solo u (vecchio) e f, scrive un array nuovo."""
    return [[(f[i][j] + LAM * sum(u[k][l] for k, l in neighbours(i, j))) / (1 + LAM * len(neighbours(i, j)))
             for j in range(W)] for i in range(H)]


def delta(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(H) for j in range(W))


def frac(x):
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def draw_grid(ax, u, title, highlight=None, neigh=(), show_frac=True):
    """Disegna una matrice 2 × 2 di pixel in scala di grigi (0 nero, 1 bianco) con i valori."""
    for i in range(H):
        for j in range(W):
            v = float(u[i][j])
            ax.add_patch(Rectangle((j, H - 1 - i), 1, 1, facecolor=str(v), edgecolor=GRID, linewidth=1))
            txt = (frac(u[i][j]) + "\n" if show_frac and u[i][j].denominator > 1 else "") + f"{v:.4f}"
            ax.text(j + 0.5, H - 0.5 - i, txt, ha="center", va="center", fontsize=8.5,
                    color="white" if v < 0.5 else INK)
    for (i, j), color, lw in [(p, ORANGE, 3) for p in neigh] + ([(highlight, BLUE, 3.5)] if highlight else []):
        ax.add_patch(Rectangle((j + 0.04, H - 1 - i + 0.04), 0.92, 0.92, fill=False, edgecolor=color, linewidth=lw))
    ax.set_xlim(-0.05, W + 0.05)
    ax.set_ylim(-0.05, H + 0.05)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=9, color=INK)


def fig_step(path):
    """Prima iterazione pixel per pixel: per ogni pixel, i vicini letti da u^(0) e il valore scritto in u^(1)."""
    u0, u1 = f, jacobi(f)
    fig, axes = plt.subplots(2, 4, figsize=(8.4, 4.6), facecolor=SURFACE)
    for n, (i, j) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        nb = neighbours(i, j)
        draw_grid(axes[0, n], u0, f"pixel ({i},{j}): legge da $u^{{(0)}}$", highlight=(i, j), neigh=nb, show_frac=False)
        s = " + ".join(frac(u0[k][l]) for k, l in nb)
        axes[0, n].text(1, -0.32, f"({frac(f[i][j])} + {s}) / (1 + 2) = {frac(u1[i][j])}", ha="center",
                        va="top", fontsize=8.5, color=INK)
        partial = [[u1[a][b] if (a, b) <= (i, j) else None for b in range(W)] for a in range(H)]
        ax = axes[1, n]
        for a in range(H):
            for b in range(W):
                v = partial[a][b]
                ax.add_patch(Rectangle((b, H - 1 - a), 1, 1, facecolor=str(float(v)) if v is not None else SURFACE,
                                       edgecolor=GRID, linewidth=1, hatch=None if v is not None else "///"))
                if v is not None:
                    ax.text(b + 0.5, H - 0.5 - a, f"{frac(v)}\n{float(v):.4f}", ha="center", va="center",
                            fontsize=8.5, color="white" if float(v) < 0.5 else INK)
        ax.add_patch(Rectangle((j + 0.04, H - 1 - i + 0.04), 0.92, 0.92, fill=False, edgecolor=BLUE, linewidth=3.5))
        ax.set_xlim(-0.05, W + 0.05)
        ax.set_ylim(-0.05, H + 0.05)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("scritto in $u^{(1)}$ (array nuovo)", fontsize=9, color=INK)
    fig.text(0.5, 0.005, "blu: pixel aggiornato   arancione: primi vicini letti (solo dall'array vecchio)   "
             "tratteggio: non ancora calcolato", ha="center", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1), h_pad=2.5)
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_iterations(us, path):
    fig, axes = plt.subplots(1, 7, figsize=(9.6, 2.3), facecolor=SURFACE)
    for t, ax in enumerate(axes[:6]):
        draw_grid(ax, us[t], f"$u^{{({t})}}$" if t else "$u^{(0)} = f$")
        if t:
            ax.text(1, -0.25, f"$\\Delta^{{({t - 1})}}$ = {frac(delta(us[t], us[t - 1]))}", ha="center", va="top", fontsize=8, color=INK2)
    star = [[F(2, 5), F(3, 5)], [F(3, 5), F(2, 5)]]
    draw_grid(axes[6], star, "$u^*$ (punto fisso)", show_frac=False)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_delta(deltas, path, eps=1e-6):
    fig, ax = plt.subplots(figsize=(6.4, 3.0), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    t = list(range(len(deltas)))
    ax.semilogy(t, deltas, color=BLUE, linewidth=2, marker="o", markersize=3.5, markeredgewidth=0)
    ax.minorticks_off()
    ax.axhline(eps, color=ORANGE, linewidth=1.5, linestyle="--")
    stop = next(k for k, d in enumerate(deltas) if d < eps)
    ax.annotate(f"$\\Delta^{{({stop})}}$ = {deltas[stop]:.2e} < $\\varepsilon = 10^{{-6}}$", (stop, deltas[stop]), xytext=(-8, -18),
                textcoords="offset points", ha="right", fontsize=8, color=INK)
    ax.set_xlabel("iterazione t", color=INK2, fontsize=9)
    ax.set_ylabel(r"$\Delta^{(t)} = \max\,|u^{(t+1)} - u^{(t)}|$", color=INK2, fontsize=9)
    ax.set_title(r"caso 2 × 2, $\lambda = 1$: $\Delta^{(t)} = (2/3)^{t+1}$ (calcolo teorico)", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return stop


def main():
    us = [f]
    for _ in range(40):
        us.append(jacobi(us[-1]))
    deltas = [float(delta(us[t + 1], us[t])) for t in range(len(us) - 1)]
    print("| t | u(0,0) = u(1,1) | u(0,1) = u(1,0) | Δ(t) = max|u(t+1) − u(t)| |")
    print("|---|---|---|---|")
    for t in range(6):
        print(f"| {t} | {frac(us[t][0][0])} = {float(us[t][0][0]):.4f} | {frac(us[t][0][1])} = {float(us[t][0][1]):.4f} "
              f"| {frac(delta(us[t + 1], us[t]))} = {deltas[t]:.4f} |")
    for t in range(1, 6):
        assert delta(us[t], us[t - 1]) == F(2, 3) ** t  # Δ^(t-1) = (2/3)^t
    FIG.mkdir(parents=True, exist_ok=True)
    fig_step(FIG / "es06-2x2-passo.png")
    fig_iterations(us, FIG / "es06-2x2-iterazioni.png")
    stop = fig_delta(deltas, FIG / "es06-2x2-delta.png")
    print(f"\nPrimo t con Δ(t) < 1e-6: t = {stop} (Δ = {deltas[stop]:.3e}), cioè dopo il calcolo di u({stop + 1}); "
          f"u({stop + 1}) = {float(us[stop + 1][0][0]):.9f}, {float(us[stop + 1][0][1]):.9f}")
    print("Figure: es06-2x2-passo.png, es06-2x2-iterazioni.png, es06-2x2-delta.png")


if __name__ == "__main__":
    main()
