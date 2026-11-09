#!/usr/bin/env python3
"""Analisi dei log di `es05.sh collect` (Esercitazione 5, HPL e HPCG su WILSON).

    python analyze_es05.py [log_collect.txt]

Legge il log (di default il più recente in results/es05/), estrae per ogni run
layout, risultati, validazione e riga sacct, stampa le tabelle in Markdown e
salva le figure in content/report/figures/.
"""
import re
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
FIG = ROOT / "content/report/figures"

# Palette di riferimento (tema chiaro): superfici, testo, serie categoriali 1-3.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

# Sandy Bridge E5-2650: 16 core per nodo, 8 flop/ciclo in doppia precisione.
CORES, FLOP_CYCLE = 16, 8


def sections(text):
    """Divide il log nelle sezioni '========== titolo ==========' di collect."""
    parts = re.split(r"^========== (.+?) ==========$", text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def first(pattern, text, cast=str, default=None):
    m = re.search(pattern, text, re.M)
    return cast(m.group(1)) if m else default


def sacct(job, body):
    """Riga principale di sacct: limite, elapsed, stato, exit code."""
    m = re.search(rf"^{job}\s+.*?(\S+)\s+(\d\d:\d\d:\d\d)\s+(\d\d:\d\d:\d\d)\s+(\w+)\s+(\d+:\d+)\s*$", body, re.M)
    return dict(zip(("reqmem", "timelimit", "elapsed", "state", "exit"), m.groups())) if m else {}


def parse(text):
    hpl, hpcg = [], []
    for title, body in sections(text).items():
        m = re.match(r"(hpl|hpcg)/(\S+)/ \(job (\d+)\)", title)
        if not m:
            continue
        kind, name, job = m.groups()
        run = {
            "name": name,
            "job": job,
            "node": first(r"^Job: .*nodes: (\S+)", body),
            "tasks": first(r"MPI tasks: (\d+);", body, int),
            "threads": first(r"OpenMP threads per task: (\d+)", body, int),
            "masks": re.findall(r"cpu-bind=MASK - \S+, task\s+(\d+)\s+\d+ \[\d+\]: mask (0x[0-9a-f]+)", body),
            **sacct(job, body),
        }
        if kind == "hpl":
            wr = re.search(r"^WR\S+\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.e+]+)", body, re.M)
            if not wr:
                continue
            run.update(zip(("N", "NB", "P", "Q"), map(int, wr.groups()[:4])))
            run["time"], run["gflops"] = float(wr.group(5)), float(wr.group(6))
            run["residual"] = first(r"\)\*N\)=\s+([\d.e+-]+) \.+ (?:PASSED|FAILED)", body, float)
            run["check"] = first(r"\.\.\.\.\.\. (PASSED|FAILED)", body)
            run["ghz"] = [float(g) for g in re.findall(r"#\s+([\d.]+) GHz", body)]
            hpl.append(run)
        else:
            g = lambda key, cast=float: first(rf"^{re.escape(key)}=(.+)$", body, cast)  # noqa: E731
            run.update(
                procs=g("Machine Summary::Distributed Processes", int),
                omp=g("Machine Summary::Threads per processes", int),
                glob="x".join(str(g(f"Global Problem Dimensions::Global n{a}", int)) for a in "xyz"),
                local="x".join(str(g(f"Local Domain Dimensions::n{a}", int)) for a in "xyz"),
                pgrid="x".join(str(g(f"Processor Dimensions::np{a}", int)) for a in "xyz"),
                rate=first(r"HPCG result is VALID with a GFLOP/s rating of=([\d.]+)", body, float),
                valid="VALID" if "HPCG result is VALID" in body else "NON VALIDO",
                setup=g("Setup Information::Setup Time"),
                total=g("Benchmark Time Summary::Total"),
                t_mg=g("Benchmark Time Summary::MG"),
                t_spmv=g("Benchmark Time Summary::SpMV"),
                spmv=g("GFLOP/s Summary::Raw SpMV"),
                mg=g("GFLOP/s Summary::Raw MG"),
                ddot=g("GFLOP/s Summary::Raw DDOT"),
                waxpby=g("GFLOP/s Summary::Raw WAXPBY"),
                bw=g("GB/s Summary::Raw Total B/W"),
                mem=g("Memory Use Information::Total memory used for data (Gbytes)"),
                iters=g("Iteration Count Information::Total number of optimized iterations", int),
            )
            hpcg.append(run)
    return hpl, hpcg


def layout_key(name):
    """'15_N41280_2x8_P1Q2_r2' -> '2x8_P1Q2' (ripartizione e griglia, senza ripetizione)."""
    m = re.match(r"\d+_N41280_(\d+x\d+_P\d+Q\d+)", name)
    return m.group(1) if m else None


def label(key):
    tp, grid = key.split("_")
    t, c = tp.split("x")
    p, q = re.match(r"P(\d+)Q(\d+)", grid).groups()
    return f"{t} × {c}  (griglia {p}×{q})"


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_hpl_layouts(groups, path):
    keys = sorted(groups, key=lambda k: st.mean(groups[k]))
    fig, ax = plt.subplots(figsize=(7.2, 3.6), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    for y, k in enumerate(keys):
        v = groups[k]
        m, s = st.mean(v), st.stdev(v)
        ax.plot([m - s, m + s], [y, y], color=BLUE, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter(v, [y] * len(v), s=22, facecolor=SURFACE, edgecolor=INK2, linewidth=1, zorder=3)
        ax.scatter([m], [y], s=64, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.text(m + s + 0.8, y, f"{m:.1f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(keys)), [label(k) for k in keys], color=INK)
    ax.set_xlabel("HPL [GFLOP/s]  (N = 41280, NB = 192, 1 nodo)", color=INK2, fontsize=9)
    ax.set_xlim(232, 268)
    ax.scatter([], [], s=64, color=BLUE, label="media ± dev. std (3 run)")
    ax.scatter([], [], s=22, facecolor=SURFACE, edgecolor=INK2, label="run singolo")
    ax.legend(loc="lower right", fontsize=8, frameon=False, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_hpcg_layouts(runs, path):
    xs = [f"{r['procs']} × {r['omp']}" for r in runs]
    series = (("rate validato", "rate", BLUE), ("SpMV", "spmv", ORANGE), ("MG", "mg", AQUA))
    fig, ax = plt.subplots(figsize=(7.2, 3.6), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="x", visible=False)
    for name, key, color in series:
        ys = [r[key] for r in runs]
        ax.plot(range(len(xs)), ys, color=color, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
    ax.set_xticks(range(len(xs)), xs, color=INK)
    ax.set_xlabel("processi MPI × thread OpenMP  (griglia globale 416×208×208, 60 s, 1 nodo)", color=INK2, fontsize=9)
    ax.set_ylabel("GFLOP/s", color=INK2, fontsize=9)
    ax.set_ylim(0, 10.5)
    ax.set_xlim(-0.3, len(xs) - 1 + 0.3)
    ax.legend(loc="lower left", fontsize=8, frameon=False, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    log = Path(sys.argv[1]) if len(sys.argv) > 1 else max((ROOT / "results/es05").glob("collect_*.txt"))
    hpl, hpcg = parse(log.read_text(errors="replace"))
    print(f"Log: {log.relative_to(ROOT)} — {len(hpl)} run HPL, {len(hpcg)} run HPCG\n")

    print("| Run | Job | Nodo | Task × thread | N | P×Q | Time (s) | GFLOP/s | Residuo | Elapsed | Stato |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in hpl:
        print(f"| `{r['name']}` | {r['job']} | {r['node']} | {r['tasks']} × {r['threads']} | {r['N']} | {r['P']}×{r['Q']} "
              f"| {r['time']:.2f} | {r['gflops']:.2f} | {r['residual']:.2e} {r['check']} | {r.get('elapsed')} "
              f"| {r.get('state')} {r.get('exit')} |")

    groups = {}
    for r in hpl:
        k = layout_key(r["name"])
        if k and not r["name"].endswith("_perf"):
            groups.setdefault(k, []).append(r["gflops"])
    best = max(st.mean(v) for v in groups.values())
    print("\n| Ripartizione (griglia) | Run (GFLOP/s) | Media | Dev. std | Rispetto al migliore |")
    print("|---|---|---|---|---|")
    for k in sorted(groups, key=lambda k: -st.mean(groups[k])):
        v = groups[k]
        print(f"| {label(k)} | {' / '.join(f'{x:.1f}' for x in v)} | {st.mean(v):.1f} | {st.stdev(v):.1f} "
              f"| {(st.mean(v) / best - 1) * 100:+.1f}% |")

    ghz = [g for r in hpl for g in r["ghz"]]
    if ghz:
        f = st.mean(ghz)
        print(f"\nFrequenza effettiva (perf stat): {ghz} -> media {f:.3f} GHz")
        for lab, fr in (("base 2.0 GHz", 2.0), (f"misurata {f:.2f} GHz", f), ("turbo massimo 2.8 GHz", 2.8)):
            peak = CORES * fr * FLOP_CYCLE
            print(f"  {lab}: picco {peak:.1f} GFLOP/s; HPL migliore {best / peak * 100:.1f}%")

    print("\n| Run | Job | Nodo | Proc × thread | Griglia locale | Griglia proc. | GFLOP/s | SpMV | MG | Setup (s) | Tempo bench. (s) | Elapsed | Esito |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in hpcg:
        print(f"| `{r['name']}` | {r['job']} | {r['node']} | {r['procs']} × {r['omp']} | {r['local']} | {r['pgrid']} "
              f"| {r['rate']:.2f} | {r['spmv']:.2f} | {r['mg']:.2f} | {r['setup']:.1f} | {r['total']:.1f} "
              f"| {r.get('elapsed')} | {r['valid']} |")

    FIG.mkdir(parents=True, exist_ok=True)
    fig_hpl_layouts(groups, FIG / "es05-hpl-layout.png")
    layout_runs = [r for r in hpcg if re.match(r"1\d_\d+x\d+$", r["name"])]
    fig_hpcg_layouts(layout_runs, FIG / "es05-hpcg-layout.png")
    print("\nFigure: content/report/figures/es05-hpl-layout.png, es05-hpcg-layout.png")


if __name__ == "__main__":
    main()
