# HPC4AI project — agent guidelines

Personal Jupyter Book (Jupyter Book 2 / MyST) for the HPC4AI course: notes,
examples, exercises, notebooks. Content lives in `content/`: lectures under
`content/lectures/`, the lab report under `content/report/`.

## Commands

```bash
./scripts/setup-env.sh   # create/update .venv (uv, fallback python3)
./scripts/preview.sh     # live preview (requires .venv)
./scripts/build.sh       # strict HTML build
./scripts/check.sh       # structure check + strict build
./scripts/clean.sh       # rm -rf _build
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
- Content is in **English**, except the lab report (`content/report/`), which is
  in **Italian** (English only for theory quoted from sources). Remove or
  translate other Italian scratch notes before saving a page.
- Generated output is never edited: `_build/`, `.myst/`, `.venv/` are git-ignored.

## Structure conventions

One self-contained lecture per folder:

```text
content/lectures/lectureXX/
├── index.md      # title, objectives, prerequisites, layout links
├── theory.md     # concise theory
├── examples.md   # worked examples bridge theory and exercises
├── exercises/    # one .md per task: objective, procedure, questions,
│                 # collapsed dropdown solution (::::{dropdown})
├── notebooks/
├── code/
├── data/
└── figures/
```

- New lecture: copy `templates/lecture-template/`. New exercise:
  `templates/exercise-template.md`.
- Add every new page to `toc.yml`; order there matches the rendered book.
- Lectures without material stay `# Lecture NN — To be defined` until real
  course content arrives. Do not fill them with placeholders.
- Solutions in exercises are visible but collapsed (`::::{dropdown}`).
- Notebooks: keep outputs small, clear cell state, kernel name `hpc4ai`.
- Move a figure/notebook/code block to `shared/` only if two+ lectures reuse
  it.
- Curated outputs go in `results/`. Large raw output and logs stay untracked;
  do not commit `results/**/raw/`.

## Lab report (`content/report/`)

The lab report follows fixed guidelines:

```text
content/report/
├── index.md                  # purpose, structure, writing conventions
├── teoria.md                 # essential theory only; full treatment in the notebook
├── esercitazioni/
│   ├── index.md
│   └── esNN-<slug>.md        # one page per exercise, fixed schema
├── riepilogo.md              # final checkpoint table
├── appendice-codici.md       # appendix linking codes/execN/
├── codes/execN/              # full source per exercise + README (excluded from build)
├── notebooks/                # runnable version of the report exercises
└── figures/
```

- Exercise schema, in order: **Consegna** (highlighted `:::{note}` callout,
  optional parts marked `**(Optional)**`), **Parametri**, **Implementazione**
  (short snippets + build/run commands), **Procedura di validazione**,
  **Risultati e plot** (numbered tables/figures with caption, units, legend),
  **Commenti**, **Checkpoint** (2–4 bullets).
- `riepilogo.md` table columns: exercise, key result, validation passed (sì/no),
  open notes.
- Every result statement is backed by data, a table or a figure; declare all
  parameters (problem size, precision, iterations/tolerances, seeds,
  dataset/model config, software versions).
- Full code lives in `codes/execN/` with a README (dependencies, build/run
  commands, default params); the report body holds only short excerpts.

## Git

- Commit coherent units with meaningful messages (repo README and workflow docs
  require it). Pull `--ff-only` before editing; never force-push.
- On the lab PC: pull, work, commit, push. Keep Mac and lab in sync via GitHub.