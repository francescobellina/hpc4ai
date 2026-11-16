#!/usr/bin/env python3
"""Analisi dei log di `es05.sh collect` (Esercitazione 5, HPL e HPCG su WILSON).

    python analyze_es05.py [log_collect.txt]

Legge il log (di default il più recente in results/es05/), estrae per ogni run
layout, risultati, validazione e riga sacct, stampa le tabelle in Markdown e
salva le figure in content/esercizi/figures/.
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

# Palette di riferimento (tema chiaro): superfici, testo, serie categoriali 1-3.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"

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
                t_ddot=g("Benchmark Time Summary::DDOT"),
                t_waxpby=g("Benchmark Time Summary::WAXPBY"),
                ar_min=g("DDOT Timing Variations::Min DDOT MPI_Allreduce time"),
                ar_max=g("DDOT Timing Variations::Max DDOT MPI_Allreduce time"),
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


def nodes_of(name):
    """'S064_N41280_n4_2x8_P2Q4' o 'W064_n4_16x1' -> 4."""
    return int(re.search(r"_n(\d+)_", name).group(1))


def hpl_scaling(hpl, peak):
    """Strong (N = 41280 fisso, da 1 core a 8 nodi) e memory-scaled (N ∝ √nodi)."""
    strong = sorted((r for r in hpl if re.match(r"S\d{3}_", r["name"])), key=lambda r: r["tasks"] * r["threads"])
    one = next(r for r in strong if r["tasks"] * r["threads"] == CORES)
    memory = [one] + sorted((r for r in hpl if r["name"].startswith("M")), key=lambda r: nodes_of(r["name"]))

    print("\nHPL strong scaling, N = 41280 (S = T_1/T_c, E = S/c; per nodo: rispetto al run a 16 core)")
    print("| Core | Nodi | Task × thread | P×Q | Time (s) | GFLOP/s | GFLOP/s per core | Speedup | Efficienza | Efficienza per nodo | Picco (2.40 GHz) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    t1 = strong[0]["time"]
    for r in strong:
        c, n = r["tasks"] * r["threads"], nodes_of(r["name"])
        s = t1 / r["time"]
        en = f"{one['time'] / r['time'] / n:.2f}" if c >= CORES else "—"
        print(f"| {c} | {n} | {r['tasks']} × {r['threads']} | {r['P']}×{r['Q']} | {r['time']:.1f} | {r['gflops']:.1f} "
              f"| {r['gflops'] / c:.2f} | {s:.2f} | {s / c:.2f} | {en} | {r['gflops'] / (c * peak / CORES) * 100:.1f}% |")

    print("\nHPL memory-scaled (8N²/nodi costante; E = R_k/(k R_1))")
    print("| Nodi | N | Matrice per nodo (GiB) | P×Q | Time (s) | GFLOP/s | GFLOP/s per nodo | Efficienza | Picco (2.40 GHz) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in memory:
        n = nodes_of(r["name"])
        e = r["gflops"] / (n * one["gflops"])
        print(f"| {n} | {r['N']} | {8 * r['N'] ** 2 / n / 2**30:.1f} | {r['P']}×{r['Q']} | {r['time']:.1f} | {r['gflops']:.1f} "
              f"| {r['gflops'] / n:.1f} | {e:.2f} | {r['gflops'] / (n * peak) * 100:.1f}% |")
    return strong, memory, one


def hpcg_scaling(hpcg):
    """Weak (griglia locale 104³) e strong (griglia globale 256³), efficienza sul rate validato."""
    weak = sorted([r for r in hpcg if r["name"] == "10_16x1" or r["name"].startswith("W")], key=lambda r: r["procs"])
    strong = sorted((r for r in hpcg if re.match(r"S\d{3}_", r["name"])), key=lambda r: r["procs"])
    for title, runs in (("weak, griglia locale 104 × 104 × 104", weak), ("strong, griglia globale 256 × 256 × 256", strong)):
        r1, r16 = runs[0], next(r for r in runs if r["procs"] == CORES)
        print(f"\nHPCG {title} (S = R_p/R_1, E = S/p; per nodo: rispetto ai 16 processi)")
        print("| Processi | Nodi | Griglia globale | Iterazioni | GFLOP/s | Speedup | Efficienza | Efficienza per nodo "
              "| MG | DDOT (% del tempo) | Allreduce min–max (s) |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in runs:
            p = r["procs"]
            s = r["rate"] / r1["rate"]
            en = f"{r['rate'] / (r16['rate'] * p / CORES):.2f}" if p >= CORES else "—"
            print(f"| {p} | {max(1, p // CORES)} | {r['glob']} | {r['iters']} | {r['rate']:.2f} | {s:.2f} | {s / p:.2f} | {en} "
                  f"| {r['mg']:.2f} | {r['t_ddot']:.1f} s ({r['t_ddot'] / r['total'] * 100:.0f}%) "
                  f"| {r['ar_min']:.1f}–{r['ar_max']:.1f} |")
    return weak, strong


def log2_axis(ax, values):
    ax.set_xscale("log", base=2)
    ax.set_xticks(values, [str(v) for v in values])
    ax.minorticks_off()


def fig_hpl_scaling(strong, memory, one, path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.6, 3.5), facecolor=SURFACE)
    cores = [r["tasks"] * r["threads"] for r in strong]
    speed = [strong[0]["time"] / r["time"] for r in strong]
    style(a)
    a.plot(cores, cores, color=INK2, linewidth=1, linestyle="--", label="ideale")
    a.plot(cores, speed, color=BLUE, linewidth=2, marker="o", markersize=6,
           markeredgecolor=SURFACE, markeredgewidth=1.5, label="misurato")
    a.set_yscale("log", base=2)
    log2_axis(a, cores)
    a.set_yticks(cores, [str(v) for v in cores])
    a.axvline(CORES, color=GRID, linewidth=1.5, zorder=1)
    a.text(CORES * 1.08, 1.3, "1 nodo", fontsize=8, color=INK2)
    for c, s in zip(cores[-3:], speed[-3:]):
        a.annotate(f"{s:.1f}", (c, s), xytext=(0, -13), textcoords="offset points", ha="center", fontsize=8, color=INK)
    a.set_xlabel("core (N = 41280 fisso)", color=INK2, fontsize=9)
    a.set_ylabel("speedup  T₁ / T", color=INK2, fontsize=9)
    a.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=INK2)

    style(b)
    nodes = [1, 2, 4, 8]
    s_eff = [one["time"] / r["time"] / nodes_of(r["name"]) for r in strong if r["tasks"] * r["threads"] >= CORES]
    m_eff = [r["gflops"] / (nodes_of(r["name"]) * one["gflops"]) for r in memory]
    for ys, color, name in ((m_eff, ORANGE, "memory-scaled"), (s_eff, BLUE, "strong")):
        b.plot(nodes, ys, color=color, linewidth=2, marker="o", markersize=6,
               markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
        b.annotate(f"{ys[-1]:.2f}", (nodes[-1], ys[-1]), xytext=(7, -3), textcoords="offset points", fontsize=8, color=INK)
    log2_axis(b, nodes)
    b.set_ylim(0, 1.08)
    b.set_xlim(0.85, 10.5)
    b.set_xlabel("nodi (2 processi × 8 thread per nodo)", color=INK2, fontsize=9)
    b.set_ylabel("efficienza rispetto a 1 nodo", color=INK2, fontsize=9)
    b.legend(loc="lower left", fontsize=8, frameon=False, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_hpcg_scaling(weak, strong, path):
    fig, ax = plt.subplots(figsize=(7.2, 3.6), facecolor=SURFACE)
    style(ax)
    for runs, color, name in ((weak, ORANGE, "weak (griglia locale 104³)"), (strong, BLUE, "strong (griglia globale 256³)")):
        ys = [r["rate"] / runs[0]["rate"] / r["procs"] for r in runs]
        ps = [r["procs"] for r in runs]
        ax.plot(ps, ys, color=color, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
        ax.annotate(f"{ys[-1]:.2f}", (ps[-1], ys[-1]), xytext=(8, -3), textcoords="offset points", fontsize=8, color=INK)
    log2_axis(ax, [r["procs"] for r in strong])
    ax.set_xlim(0.8, 200)
    ax.axvline(CORES, color=GRID, linewidth=1.5, zorder=1)
    ax.text(CORES * 1.08, 1.02, "1 nodo", fontsize=8, color=INK2)
    ax.set_ylim(0, 1.12)
    ax.set_xlabel("processi MPI (1 thread ciascuno, 16 per nodo; 60 s richiesti)", color=INK2, fontsize=9)
    ax.set_ylabel("efficienza  R / (p · R₁)", color=INK2, fontsize=9)
    ax.legend(loc="lower left", fontsize=8, frameon=False, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_hpcg_times(strong, path):
    runs = [r for r in strong if r["procs"] >= CORES]
    parts = (("MG", "t_mg", AQUA), ("SpMV", "t_spmv", ORANGE), ("DDOT", "t_ddot", BLUE), ("WAXPBY", "t_waxpby", YELLOW))
    fig, ax = plt.subplots(figsize=(7.2, 2.9), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    left = [0.0] * len(runs)
    for name, key, color in parts:
        w = [r[key] / r["total"] * 100 for r in runs]
        ax.barh(range(len(runs)), w, left=left, height=0.6, color=color, edgecolor=SURFACE, linewidth=2, label=name)
        if key == "t_ddot":
            for y, (x0, d) in enumerate(zip(left, w)):
                if d >= 10:
                    ax.text(x0 + d / 2, y, f"DDOT {d:.0f}%", ha="center", va="center", fontsize=8, color=SURFACE)
        left = [x + y for x, y in zip(left, w)]
    ax.set_yticks(range(len(runs)), [f"{r['procs']} processi, {r['procs'] // CORES} nod{'o' if r['procs'] == CORES else 'i'}"
                                     for r in runs], color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% del tempo del benchmark  (strong scaling, griglia globale 256³)", color=INK2, fontsize=9)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=4, fontsize=8, frameon=False, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    log = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else max((ROOT / "results/es05").glob("collect_*.txt"))
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
    f = st.mean(ghz) if ghz else None
    if f:
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
    names = ["es05-hpl-layout.png", "es05-hpcg-layout.png"]

    # Gli studi di scaling ci sono solo nei log raccolti dopo hpl-scaling e hpcg-scaling.
    if f and any(r["name"].startswith("M") for r in hpl):
        strong, memory, one = hpl_scaling(hpl, CORES * f * FLOP_CYCLE)
        fig_hpl_scaling(strong, memory, one, FIG / "es05-hpl-scaling.png")
        names.append("es05-hpl-scaling.png")
    if any(r["name"].startswith("W") for r in hpcg):
        weak, strong = hpcg_scaling(hpcg)
        fig_hpcg_scaling(weak, strong, FIG / "es05-hpcg-scaling.png")
        fig_hpcg_times(strong, FIG / "es05-hpcg-tempi.png")
        names += ["es05-hpcg-scaling.png", "es05-hpcg-tempi.png"]
    print("\nFigure in content/esercizi/figures/: " + ", ".join(names))


if __name__ == "__main__":
    main()
