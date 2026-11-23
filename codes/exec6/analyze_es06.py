#!/usr/bin/env python3
"""Verifiche del programma sequenziale e qualità delle ricostruzioni (Esercitazione 6).

    python analyze_es06.py [cartella_raw]

Legge i file scaricati da WILSON (di default results/es06/raw/: immagini small e
medium, uscite .pgm e .bin di denoise_serial) e:

1. confronta le uscite del programma del corso con una implementazione NumPy di
   riferimento dello stesso passo di Jacobi (stesso ordine delle somme, quindi
   risultati identici bit per bit se il programma fa ciò che dice);
2. ricostruisce l'immagine media con NumPy per i lambda dei run e per qualche lambda
   in più, controlla che l'arrotondamento a 8 bit coincida con i .pgm del corso, e
   calcola MSE, PSNR e SSIM (Wang et al. 2004) rispetto all'immagine pulita;
3. salva le figure es06-ricostruzioni.png, es06-ssim-mappe.png, es06-profilo.png e
   es06-qualita-lambda.png in content/esercizi/figures/.
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "content/esercizi/figures"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


# ---------------------------------------------------------------- I/O
def read_pgm(path):
    """P2 come pgm_io.h: commenti '#' ammessi, valori divisi per il massimo."""
    tokens = []
    for line in Path(path).read_text().splitlines():
        tokens += line.split("#", 1)[0].split()
    assert tokens[0] == "P2", path
    w, h, maxval = int(tokens[1]), int(tokens[2]), int(tokens[3])
    vals = np.array(tokens[4:], dtype=np.int64)
    assert vals.size == w * h, path
    return vals.reshape(h, w), maxval


def read_norm(path):
    v, m = read_pgm(path)
    return v / m


def to_8bit(u):
    """Come pgm_write: clip in [0, 1], poi lround(255 u) (arrotondamento lontano da zero)."""
    x = 255 * np.clip(u, 0.0, 1.0)
    return np.floor(x + 0.5).astype(np.int64)


# ---------------------------------------------------------------- Jacobi di riferimento
def jacobi_step(f, u, lam):
    """Un passo di jacobi_step di denoise_serial.c, con le somme nello stesso ordine.

    Nel C: neighbours = 0.0; += sopra; += sotto; += sinistra; += destra (solo se
    esistono). Sommare 0.0 per un vicino che manca è esatto, quindi l'ordine resta
    quello del C anche usando maschere.
    """
    h, w = u.shape
    zero = np.zeros_like(u)
    up, down, left, right = zero.copy(), zero.copy(), zero.copy(), zero.copy()
    up[1:, :] = u[:-1, :]
    down[:-1, :] = u[1:, :]
    left[:, 1:] = u[:, :-1]
    right[:, :-1] = u[:, 1:]
    count = np.full(u.shape, 4.0)
    count[0, :] -= 1
    count[-1, :] -= 1
    count[:, 0] -= 1
    count[:, -1] -= 1
    neighbours = 0.0 + up
    neighbours = neighbours + down
    neighbours = neighbours + left
    neighbours = neighbours + right
    new = (f + lam * neighbours) / (1.0 + lam * count)
    return new, float(np.max(np.abs(new - u)))


def solve(f, lam, steps, tol):
    """Come il ciclo di main: ferma se change < tol dopo l'aggiornamento."""
    u, change, done = f.copy(), 0.0, 0
    while done < steps:
        u, change = jacobi_step(f, u, lam)
        done += 1
        if change < tol:
            break
    return u, done, change, ("tolerance" if change < tol else "iteration limit")


# ---------------------------------------------------------------- qualità
def mse(v, c):
    return float(np.mean((v - c) ** 2))


def psnr(v, c, L=1.0):
    return 10 * np.log10(L ** 2 / mse(v, c))


def gaussian_window(size=11, sigma=1.5):
    x = np.arange(size) - (size - 1) / 2
    g = np.exp(-x ** 2 / (2 * sigma ** 2))
    return g / g.sum()  # separabile: w(i, j) = g(i) g(j), somma 1


def filt_valid(x, g):
    """Media pesata con la finestra gaussiana, solo dove la finestra sta tutta nell'immagine."""
    n = len(g)
    rows = sum(g[k] * x[k:x.shape[0] - n + 1 + k, :] for k in range(n))
    return sum(g[k] * rows[:, k:x.shape[1] - n + 1 + k] for k in range(n))


def ssim_map(x, y, L=1.0, K1=0.01, K2=0.03):
    """SSIM locale, eq. 13 di Wang et al. (2004), finestra gaussiana 11 x 11, sigma 1.5."""
    g = gaussian_window()
    C1, C2 = (K1 * L) ** 2, (K2 * L) ** 2
    mx, my = filt_valid(x, g), filt_valid(y, g)
    sxx = filt_valid(x * x, g) - mx ** 2
    syy = filt_valid(y * y, g) - my ** 2
    sxy = filt_valid(x * y, g) - mx * my
    return ((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx ** 2 + my ** 2 + C1) * (sxx + syy + C2))


# ---------------------------------------------------------------- figure
def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


CROP = (slice(1434, 1844), slice(819, 1229))  # y 0.70-0.90, x 0.40-0.60: angolo del rettangolo e inizio della barra


def fig_images(imgs, names, metrics, path):
    fig, axes = plt.subplots(2, len(imgs), figsize=(2.3 * len(imgs), 5.0), facecolor=SURFACE)
    for k, (img, name) in enumerate(zip(imgs, names)):
        axes[0, k].imshow(img, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        axes[0, k].set_title(name + ("" if metrics[k] is None else f"\nMSE {metrics[k][0]:.4f} · SSIM {metrics[k][2]:.3f}"),
                             fontsize=8.5, color=INK)
        axes[0, k].add_patch(plt.Rectangle((CROP[1].start, CROP[0].start), 410, 410, fill=False, edgecolor=ORANGE, linewidth=1.2))
        axes[1, k].imshow(img[CROP], cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        axes[1, k].set_title("ingrandimento (riquadro arancione)", fontsize=7.5, color=INK2)
        for a in axes[:, k]:
            a.set_xticks([])
            a.set_yticks([])
            for s in a.spines.values():
                s.set_color(GRID)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)  # il rumore non si comprime: dpi più basso per restare sotto 1 MB
    plt.close(fig)


def fig_ssim_maps(maps, names, path):
    fig, axes = plt.subplots(1, len(maps), figsize=(3.07 * len(maps), 3.4), facecolor=SURFACE)
    for a, m, name in zip(axes, maps, names):
        im = a.imshow(m, cmap="Blues_r", vmin=0, vmax=1, interpolation="nearest")
        a.set_title(f"{name}: MSSIM {m.mean():.3f}", fontsize=8.5, color=INK)
        a.set_xticks([])
        a.set_yticks([])
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02)
    cb.set_label("SSIM locale (1 = identica alla pulita)", fontsize=8, color=INK2)
    cb.ax.tick_params(labelsize=7, colors=INK2)
    fig.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


ROWS = slice(614, 819)  # y 0.30-0.40: dentro il rettangolo, i cui bordi qui sono verticali
EDGES = ((215, 280, "bordo sinistro del rettangolo (j = 246)"), (828, 893, "bordo destro del rettangolo (j = 860)"))


def fig_profile(clean, noisy, recs, path):
    """Profilo medio su 205 righe attraverso i due bordi verticali del rettangolo.

    La media sulle righe riduce il rumore di circa sqrt(205) = 14 volte e lascia la
    forma media del bordo: la larghezza della rampa misura la sfocatura.
    """
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), facecolor=SURFACE)
    colors = (ORANGE, BLUE, AQUA)
    for ax, (j0, j1, title) in zip(axes, EDGES):
        style(ax)
        x = np.arange(j0, j1)
        ax.plot(x, noisy[ROWS, j0:j1].mean(axis=0), color=INK2, linewidth=0.8, alpha=0.6, label="rumorosa")
        for (lam, u), color in zip(recs, colors):
            ax.plot(x, u[ROWS, j0:j1].mean(axis=0), color=color, linewidth=1.6, label=f"λ = {lam:g}")
        ax.plot(x, clean[ROWS, j0:j1].mean(axis=0), color=INK, linewidth=1.2, linestyle="--", label="pulita")
        ax.set_xlabel("colonna j", color=INK2, fontsize=9)
        ax.set_title(title, fontsize=9, color=INK)
        ax.set_ylim(0.1, 0.85)
    axes[0].set_ylabel("media sulle righe 614–818", color=INK2, fontsize=9)
    axes[0].legend(fontsize=7.5, frameon=False, labelcolor=INK2, loc="center right")
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def edge_width(u, j_edge, side):
    """Pixel dal bordo in cui il profilo medio passa dal 10% al 90% del salto (misura della sfocatura)."""
    j0, j1 = (j_edge - 40, j_edge + 40)
    prof = u[ROWS, j0:j1].mean(axis=0)
    lo, hi = (prof[:15].mean(), prof[-15:].mean()) if side == "left" else (prof[-15:].mean(), prof[:15].mean())
    if side == "right":
        prof = prof[::-1]
    t10, t90 = lo + 0.1 * (hi - lo), lo + 0.9 * (hi - lo)
    return int(np.argmax(prof >= t90) - np.argmax(prof >= t10))


def fig_lambda(rows, base, path):
    lams = [r["lam"] for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.0), facecolor=SURFACE)
    for a, key, label in zip(axes, ("mse", "psnr", "mssim"), ("MSE", "PSNR (dB)", "MSSIM")):
        style(a)
        a.plot(lams, [r[key] for r in rows], color=BLUE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE)
        for r in rows:
            if r["lam"] in (0.2, 1.0):
                a.plot(r["lam"], r[key], marker="o", markersize=8, markerfacecolor=SURFACE, markeredgecolor=ORANGE,
                       markeredgewidth=1.8, linestyle="none")
        a.axhline(base[key], color=INK2, linewidth=1, linestyle="--")
        a.text(lams[0], base[key], " rumorosa", va="bottom", fontsize=7.5, color=INK2)
        a.set_xscale("log")
        a.set_xlabel("λ", color=INK2, fontsize=9)
        a.set_title(label, fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    raw = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "results/es06/raw"

    print("## 1. Uscite del programma del corso contro il riferimento NumPy\n")
    print("| Caso | λ, iter. max, tol. | Iterazioni (NumPy) | Arresto | Max change | max |C − NumPy| |")
    print("|---|---|---|---|---|---|")
    cases = [("costante 3 × 4", "const.pgm", "const.bin", 1.0, 200, 1e-6),
             ("2 × 2, 1 iterazione", "t2x2.pgm", "t2x2-1it.bin", 1.0, 1, 0.0),
             ("2 × 2, a convergenza", "t2x2.pgm", "t2x2-conv.bin", 1.0, 200, 1e-6),
             ("small 17 × 19", "images/small/noisy.pgm", "small-serial.bin", 1.0, 200, 1e-6)]
    for name, src, binf, lam, steps, tol in cases:
        f = read_norm(raw / src)
        u, done, change, why = solve(f, lam, steps, tol)
        c = np.fromfile(raw / binf, dtype="<f8").reshape(f.shape)
        print(f"| {name} | {lam:g}, {steps}, {tol:g} | {done} | {why} | {change:.12g} | {np.max(np.abs(c - u)):.3g} |")

    clean, noisy = read_norm(raw / "images/medium/clean.pgm"), read_norm(raw / "images/medium/noisy.pgm")
    base = dict(mse=mse(noisy, clean), psnr=psnr(noisy, clean), mssim=float(ssim_map(noisy, clean).mean()))
    print("\n## 2. Immagine media 2048 × 2048: ricostruzioni e qualità\n")
    print(f"Rumorosa contro pulita: MSE {base['mse']:.5f}, PSNR {base['psnr']:.2f} dB, MSSIM {base['mssim']:.4f}\n")
    print("| λ | Iter. max | Iterazioni | Arresto | Max change | .pgm del corso = NumPy a 8 bit | MSE | PSNR (dB) | MSSIM |")
    print("|---|---|---|---|---|---|---|---|---|")
    rows, recs = [], {}
    # 200 iterazioni come nei run del corso; per lambda > 2 servono più iterazioni per
    # arrivare alla stessa tolleranza, quindi il limite sale (dichiarato nella tabella).
    for lam in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0):
        steps = 200 if lam <= 2 else 10000
        u, done, change, why = solve(noisy, lam, steps, 1e-6)
        pgm = {0.2: "serial-l02.pgm", 1.0: "serial.pgm"}.get(lam)
        same = "—"
        if pgm:
            course, _ = read_pgm(raw / pgm)
            diff = int(np.sum(course != to_8bit(u)))
            same = "sì" if diff == 0 else f"{diff} pixel diversi"
        if pgm or lam == 20.0:
            recs[lam] = u
        r = dict(lam=lam, mse=mse(u, clean), psnr=psnr(u, clean), mssim=float(ssim_map(u, clean).mean()))
        rows.append(r)
        print(f"| {lam:g} | {steps} | {done} | {why} | {change:.3g} | {same} | {r['mse']:.5f} | {r['psnr']:.2f} | {r['mssim']:.4f} |")

    FIG.mkdir(parents=True, exist_ok=True)
    imgs = [clean, noisy, recs[0.2], recs[1.0], recs[20.0]]
    names = ["pulita", "rumorosa (input)", "λ = 0.2", "λ = 1", "λ = 20"]
    print("\nLarghezza del bordo 10-90% (pixel), media sulle righe 614-818:")
    for name, u in zip(names, imgs):
        print(f"  {name}: sinistro {edge_width(u, 246, 'left')}, destro {edge_width(u, 860, 'right')}")
    metrics = [None] + [(mse(v, clean), psnr(v, clean), float(ssim_map(v, clean).mean())) for v in imgs[1:]]
    fig_images(imgs, names, metrics, FIG / "es06-ricostruzioni.png")
    fig_ssim_maps([ssim_map(v, clean) for v in imgs[1:]], names[1:], FIG / "es06-ssim-mappe.png")
    fig_profile(clean, noisy, [(0.2, recs[0.2]), (1.0, recs[1.0]), (20.0, recs[20.0])], FIG / "es06-profilo.png")
    fig_lambda(rows, base, FIG / "es06-qualita-lambda.png")
    print("\nFigure: es06-ricostruzioni.png, es06-ssim-mappe.png, es06-profilo.png, es06-qualita-lambda.png")


if __name__ == "__main__":
    main()
