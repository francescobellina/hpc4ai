# HPC4AI project — agent guidelines

Personal Jupyter Book (Jupyter Book 2 / MyST) for the HPC4AI course. The main
source is the course site
(<https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/home.html>).
Content lives in `content/`, in three parts plus appendices:

- **Part I — Theory** (`content/teoria/`): macro-chapters following the course
  chapters (1 architectures, 2 parallel computing, 3 performance and
  benchmarking, 4 resources and Slurm, 5 OpenMP, 6 MPI) plus a glossary.
- **Part II — Exercises** (`content/esercizi/`): warm-up and the exercises for the
  report, numbered as in the course; only exercises are numbered.
- **Part III — Report** (`content/relazione/`): the English synthesis of the
  exercise results, exported to PDF.
- Appendices: `content/workflow/`, `content/reference/`.

## Commands

```bash
./scripts/setup-env.sh   # create/update .venv (uv, fallback python3)
./scripts/preview.sh     # live preview (requires .venv)
./scripts/build.sh       # strict HTML build
./scripts/check.sh       # structure check + strict build
./scripts/clean.sh       # rm -rf _build
jupyter book build --pdf content/relazione/index.md   # report PDF -> exports/
```

After any content change run `./scripts/check.sh`. Strict build fails on
warnings: resolve them, do not bypass.

## Repository rules

- WILSON = remote HPC (`fbellina2@wilson.mib.infn.it`). Mac/VS Code = edit.
  GitHub = sync. Lab client = transfer source.
- **Never invent cluster facts.** Record only what the course or laboratory
  confirms: remote paths, module names, compiler versions, scheduler commands,
  benchmark results. Confirmed so far: WILSON username `fbellina2`, host
  `wilson.mib.infn.it`.
- **Never commit credentials**: passwords, SSH keys, tokens. `config/cluster.env`
  is local, git-ignored; `config/cluster.example.env` is the template.
- Theory, exercises and appendices are in **Italian**; the report
  (`content/relazione/`) is in **English**.
- Generated output is never edited: `_build/`, `.myst/`, `.venv/` are git-ignored.

## Structure conventions

```text
content/
├── teoria/            # NN-<slug>.md, one macro-chapter per course chapter
│   ├── figures/
│   └── notebooks/
├── esercizi/
│   ├── index.md       # overview, exercise ↔ theory map, course report checklist
│   ├── warm-up/
│   ├── esNN-<slug>.md # one page per exercise (full lab notebook)
│   ├── riepilogo.md   # checkpoint table
│   ├── appendice-codici.md
│   ├── figures/
│   └── notebooks/
└── relazione/index.md # English report, PDF export in its frontmatter
codes/execN/           # full source per exercise + README (excluded from build)
results/esNN/          # curated logs
```

- Theory chapters are reorganized from existing notes; do not drop schemes,
  figures or tables when moving text. Theory is not numbered as lectures.
- Add every new page to `toc.yml`; order there matches the rendered book.
- Exercise schema, in order: **Consegna** (highlighted `:::{note}` callout,
  optional parts marked `**(Optional)**`), **Teoria di riferimento**
  (`:::{seealso}` with `{ref}` links to labels in `content/teoria/`; no backticks
  inside `{ref}` text), **Parametri**, **Implementazione** (short snippets +
  build/run commands), **Procedura di validazione**, **Risultati e plot**
  (numbered tables/figures with caption, units, legend), **Commenti**,
  **Checkpoint** (2–4 bullets).
- `riepilogo.md` table columns: exercise, key result, validation passed (sì/no),
  open notes.
- Every result statement is backed by data, a table or a figure; declare all
  parameters (problem size, precision, iterations/tolerances, seeds,
  dataset/model config, software versions).
- The report adds no new data: every number comes from an exercise page. Labels in
  the report use the `r-` prefix (labels are global across the book).
- Solutions in warm-up exercises are visible but collapsed (`::::{dropdown}`).
- Notebooks: keep outputs small, clear cell state, kernel name `hpc4ai`.
- Large raw output and logs stay untracked; do not commit `results/**/raw/`.
  `exports/` (PDF) is generated and git-ignored.

## Git

- Commit coherent units with meaningful messages (repo README and workflow docs
  require it). Pull `--ff-only` before editing; never force-push.
- On the lab PC: pull, work, commit, push. Keep Mac and lab in sync via GitHub.