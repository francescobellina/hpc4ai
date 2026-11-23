#!/usr/bin/env python3
"""Analisi del log di `es03.sh collect` (Esercitazione 3, Tiny stories, many threads).

    python analyze_es03.py [log_collect.txt]

Legge il log (di default il più recente in results/es03/) con la baseline seriale
(job 61832) e il job OpenMP (job 62659), calcola i byte letti per token dalla
configurazione dei modelli, stampa le tabelle in Markdown e salva le figure in
content/esercizi/figures/.
"""
import re
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "content/esercizi/figures"

# Palette di riferimento (tema chiaro), la stessa dell'esercizio 5.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MODELS = ("15M", "42M", "110M")
COLORS = dict(zip(MODELS, (BLUE, ORANGE, AQUA)))
THREADS = (1, 2, 4, 8, 16)
LABEL_DY = {"15M": -2, "42M": -5, "110M": 6}  # scosta le etichette vicine a T = 16

ROW = re.compile(r"^(run_omp(?:_mm)?)\s+(\d+M)\s+(\d+)\s+(\d+)\s+(spread|close)\s+([\d.]+|ERRORE)\s+(\S+)$", re.M)


def sections(text):
    """Divide il log nelle sezioni '========== titolo ==========' di collect."""
    parts = re.split(r"^========== (.+?) ==========$", text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def bytes_per_token(c):
    """Byte di pesi letti per token da forward() di run.c (float32).

    Ogni token legge tutti i pesi dei layer, rms_final e il classificatore (che con
    vocab_size > 0 coincide con la tabella degli embedding), più una riga di
    embedding. Non legge l'intestazione né le vecchie tabelle freq_cis.
    """
    dim, hid, L, nh, nkv, V = (c[k] for k in ("dim", "hidden_dim", "n_layers", "n_heads", "n_kv_heads", "vocab_size"))
    kv = dim * nkv // nh
    layers = L * (2 * dim + 2 * dim * dim + 2 * dim * kv + 3 * dim * hid)
    return 4 * (layers + dim + V * dim + dim)


def kv_bytes(c, pos):
    """Byte di key e value cache letti dall'attenzione al passo pos (tutti i layer)."""
    kv = c["dim"] * c["n_kv_heads"] // c["n_heads"]
    return 2 * c["n_layers"] * (pos + 1) * kv * 4


def parse(text):
    sec = sections(text)
    base = {m: [] for m in MODELS}
    for m, v in re.findall(r"^tok_(\d+M)_r\d\.txt:achieved tok/s: ([\d.]+)", sec["4. Riepilogo tok/s"], re.M):
        base[m].append(float(v))
    job_base = sec["2. Output del job"]
    triad = {int(t): float(b) for t, b in re.findall(r"^triad: thread =\s+(\d+) .* banda = ([\d.]+) GB/s", job_base, re.M)}
    omp_title = next(t for t in sec if t.startswith("5. Job OpenMP"))
    omp = sec[omp_title]
    cfg = {}
    for m, body in re.findall(r"stories(\d+M)\.bin: (dim=.*bytes=\d+)", omp):
        cfg[m] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", body)}
    runs = [dict(prog=p, model=m, T=int(t), rep=int(r), bind=b, tok=float(v), text=s)
            for p, m, t, r, b, v, s in ROW.findall(omp)]
    triad_close = [(int(t), float(b)) for t, b in
                   re.findall(r"^triad: thread =\s+(\d+) .* banda = ([\d.]+) GB/s", omp.split("=== 3.")[-1], re.M)]
    gprof = {}
    for m, body in re.findall(r"^--- stories(\d+M)\n(.*?)(?=^--- |^=== )", omp, re.M | re.S):
        gprof[m] = {name: float(pct) for pct, name in re.findall(r"^\s+([\d.]+)\s+[\d.]+\s+[\d.]+\s+(?:\d+\s+[\d.]+\s+[\d.]+\s+)?(\w+)$", body, re.M)}
        gprof[m]["tok"] = float(re.search(r"achieved tok/s: ([\d.]+)", body).group(1))
        gprof[m]["forward_calls"] = int(re.search(r"^\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+(\d+)\s+[\d.]+\s+[\d.]+\s+forward$", body, re.M).group(1))
    state = re.search(r"^62659\s+.*?(\w+)\s+(\d+:\d+)\s*$", omp, re.M)
    node = re.search(r"^Job: \d+; nodo: (\S+)", omp, re.M).group(1)
    return dict(base=base, triad=triad, cfg=cfg, runs=runs, triad_close=triad_close, gprof=gprof,
                state=state.groups() if state else None, node=node)


def mean_tok(runs, prog, model, T, bind="spread"):
    v = [r["tok"] for r in runs if (r["prog"], r["model"], r["T"], r["bind"]) == (prog, model, T, bind)]
    return st.mean(v), v


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def log2_axis(ax, values):
    ax.set_xscale("log", base=2)
    ax.set_xticks(values, [str(v) for v in values])
    ax.minorticks_off()


def line(ax, x, y, color, dashed=False, label=None):
    ax.plot(x, y, color=color, linewidth=2 if not dashed else 1.5, linestyle="--" if dashed else "-",
            marker="o" if not dashed else "s", markersize=6 if not dashed else 5,
            markerfacecolor=color if not dashed else SURFACE, markeredgecolor=SURFACE if not dashed else color,
            markeredgewidth=1.5, label=label)


def fig_scaling(d, path):
    serial = {m: st.mean(d["base"][m]) for m in MODELS}
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.6, 3.6), facecolor=SURFACE)
    style(a)
    style(b)
    b.plot(THREADS, THREADS, color=INK2, linewidth=1, linestyle=":", label="ideale")
    for m in MODELS:
        for prog, dashed in (("run_omp", False), ("run_omp_mm", True)):
            tok = [mean_tok(d["runs"], prog, m, t)[0] for t in THREADS]
            line(a, THREADS, tok, COLORS[m], dashed)
            line(b, THREADS, [v / serial[m] for v in tok], COLORS[m], dashed)
        a.annotate(m, (16, mean_tok(d["runs"], "run_omp", m, 16)[0]), xytext=(6, 0), textcoords="offset points",
                   va="center", fontsize=9, color=INK)
        s16 = mean_tok(d["runs"], "run_omp", m, 16)[0] / serial[m]
        b.annotate(f"{m}  {s16:.1f}", (16, s16), xytext=(6, LABEL_DY[m]), textcoords="offset points", va="center",
                   fontsize=8, color=INK)
    a.set_yscale("log")
    a.set_yticks([5, 10, 20, 50, 100, 200, 300], ["5", "10", "20", "50", "100", "200", "300"])
    a.minorticks_off()
    for ax in (a, b):
        log2_axis(ax, THREADS)
        ax.set_xlim(0.85, 30)
        ax.set_xlabel("thread OpenMP (spread, un core ciascuno)", color=INK2, fontsize=9)
    a.set_ylabel("token al secondo", color=INK2, fontsize=9)
    a.set_title("velocità di generazione", fontsize=9, color=INK)
    b.set_yscale("log", base=2)
    b.set_yticks(THREADS, [str(v) for v in THREADS])
    b.set_ylabel("speedup rispetto al seriale", color=INK2, fontsize=9)
    b.set_title("speedup (seriale: run.c, job 61832)", fontsize=9, color=INK)
    handles = [plt.Line2D([], [], color=INK2, linewidth=2, marker="o", markeredgecolor=SURFACE, label="run_omp (matmul + teste)"),
               plt.Line2D([], [], color=INK2, linewidth=1.5, linestyle="--", marker="s", markerfacecolor=SURFACE,
                          label="run_omp_mm (solo matmul)"),
               plt.Line2D([], [], color=INK2, linewidth=1, linestyle=":", label="ideale")]
    b.legend(handles=handles, loc="upper left", fontsize=7.5, frameon=False, labelcolor=INK2, handlelength=3)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_bandwidth(d, path):
    fig, ax = plt.subplots(figsize=(7.2, 3.8), facecolor=SURFACE)
    style(ax)
    tri = [d["triad"][t] for t in THREADS]
    ax.plot(THREADS, tri, color=INK2, linewidth=1.5, marker="D", markersize=5, markerfacecolor=SURFACE,
            markeredgecolor=INK2, label="triad, spread (wnode01)")
    ax.annotate(f"triad {tri[-1]:.1f}", (16, tri[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=INK)
    ax.plot([t for t, _ in d["triad_close"]], [b for _, b in d["triad_close"]], linestyle="none", marker="D",
            markersize=5, color=INK2)
    for m in MODELS:
        bpt = bytes_per_token(d["cfg"][m])
        bw = [mean_tok(d["runs"], "run_omp", m, t)[0] * bpt / 1e9 for t in THREADS]
        line(ax, THREADS, bw, COLORS[m])
        ax.annotate(f"{m}  {bw[-1]:.1f}", (16, bw[-1]), xytext=(6, LABEL_DY[m] / 2), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    close = [r for r in d["runs"] if r["bind"] == "close"]
    bpt = bytes_per_token(d["cfg"]["110M"])
    ax.plot([r["T"] for r in close], [r["tok"] * bpt / 1e9 for r in close], linestyle="none", marker="o", markersize=7,
            markerfacecolor=SURFACE, markeredgecolor=AQUA, markeredgewidth=1.8)
    log2_axis(ax, THREADS)
    ax.set_xlim(0.85, 30)
    ax.set_ylim(0, 58)
    ax.set_xlabel("thread OpenMP", color=INK2, fontsize=9)
    ax.set_ylabel("GB/s", color=INK2, fontsize=9)
    ax.set_title("banda effettiva di run_omp (tok/s × byte di pesi per token) e banda triad del nodo",
                 fontsize=9, color=INK)
    handles = [plt.Line2D([], [], color=INK2, linewidth=2, marker="o", markeredgecolor=SURFACE,
                          label=f"run_omp, spread ({d['node']}, media di 3 run)"),
               plt.Line2D([], [], color=AQUA, linestyle="none", marker="o", markerfacecolor=SURFACE,
                          markeredgewidth=1.8, label="run_omp 110M, close (1 run)"),
               plt.Line2D([], [], color=INK2, linewidth=1.5, marker="D", markerfacecolor=SURFACE,
                          label="triad, spread (wnode01, job 61832)"),
               plt.Line2D([], [], color=INK2, linestyle="none", marker="D", label=f"triad, close ({d['node']})")]
    ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=False, labelcolor=INK2, handlelength=3)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    log = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else max((ROOT / "results/es03").glob("collect_*.txt"))
    d = parse(log.read_text(errors="replace"))
    runs = d["runs"]
    print(f"Log: {log.relative_to(ROOT)} — job OpenMP su {d['node']}, sacct {d['state']}, {len(runs)} run, "
          f"{sum(r['text'] == 'identico' for r in runs)} con testo identico al seriale\n")

    print("| Modello | dim | hidden_dim | layer | teste | vocab | seq_len | File (B) | Pesi letti per token (MB) | Classificatore | KV cache al passo 128 (MB) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        c = d["cfg"][m]
        bpt = bytes_per_token(c)
        cls = 4 * c["vocab_size"] * c["dim"]
        print(f"| {m} | {c['dim']} | {c['hidden_dim']} | {c['n_layers']} | {c['n_heads']} | {c['vocab_size']} | {c['seq_len']} "
              f"| {c['bytes']} | {bpt / 1e6:.2f} | {cls / 1e6:.1f} MB ({cls / bpt:.0%}) | {kv_bytes(c, 128) / 1e6:.2f} |")

    print("\n| Modello | Seriale tok/s (3 run) | Media | Banda effettiva (GB/s) | gprof -fno-inline: matmul | forward (self) | tok/s con -pg | chiamate a forward |")
    print("|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        v = d["base"][m]
        bw = st.mean(v) * bytes_per_token(d["cfg"][m]) / 1e9
        g = d["gprof"].get(m)
        extra = (f"{g['matmul']:.2f}% | {g['forward']:.2f}% | {g['tok']:.2f} | {g['forward_calls']}" if g else "— | — | — | —")
        print(f"| {m} | {' / '.join(f'{x:.2f}' for x in v)} | {st.mean(v):.2f} | {bw:.2f} | {extra} |")
    print("\nTriad (wnode01, spread): " + ", ".join(f"{t} thr {b:.2f}" for t, b in d["triad"].items()))
    print("Triad (" + d["node"] + ", close): " + ", ".join(f"{t} thr {b:.2f}" for t, b in d["triad_close"]))

    print("\n| Programma | Modello | T | tok/s (3 run) | Media | Spread (max−min)/media | S vs seriale | E | S vs T=1 | Banda eff. (GB/s) | Per thread (GB/s) | ms per regione parallela |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for prog in ("run_omp", "run_omp_mm"):
        for m in MODELS:
            c = d["cfg"][m]
            regions = c["n_layers"] * (8 if prog == "run_omp" else 7) + 1
            serial = st.mean(d["base"][m])
            t1 = mean_tok(runs, prog, m, 1)[0]
            for t in THREADS:
                mu, v = mean_tok(runs, prog, m, t)
                s = mu / serial
                bw = mu * bytes_per_token(c) / 1e9
                print(f"| `{prog}` | {m} | {t} | {' / '.join(f'{x:.2f}' for x in v)} | {mu:.2f} | {(max(v) - min(v)) / mu:.1%} "
                      f"| {s:.2f} | {s / t:.2f} | {mu / t1:.2f} | {bw:.1f} | {bw / t:.2f} | {1e3 / mu / regions:.3f} |")
    print("\nclose: " + ", ".join(f"{r['prog']} {r['model']} T={r['T']} {r['tok']:.2f} ({r['text']})"
                                  for r in runs if r["bind"] == "close"))

    FIG.mkdir(parents=True, exist_ok=True)
    fig_scaling(d, FIG / "es03-scaling.png")
    fig_bandwidth(d, FIG / "es03-banda.png")
    print("\nFigure in content/esercizi/figures/: es03-scaling.png, es03-banda.png")


if __name__ == "__main__":
    main()
