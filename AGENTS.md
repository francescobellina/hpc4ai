# HPC4AI project — agent guidelines

Personal Jupyter Book (Jupyter Book 2 / MyST) for the HPC4AI course: notes,
examples, exercises, notebooks. Content lives in `content/`, lecture by lecture.

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
- Content is in **English**. Remove or translate Italian scratch notes before
  saving a page.
- Generated output is never edited: `_build/`, `.myst/`, `.venv/` are git-ignored.

## Structure conventions

One self-contained lecture per folder:

```text
content/lectures/lectureXX/
├── index.md      # title, objectives, prerequisites, layout links
├── theory.md     # concise theory
├── examples.md   # worked examples bridge theory and exercises
├── exercises/    # one .md per task: objective, procedure, questions,
│                 # collapsed dropdown solution (:::: dropdown ::::)
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
- Solutions in exercises are visible but collapsed (`:::: dropdown`, color
  success).
- Notebooks: keep outputs small, clear cell state, kernel name `hpc4ai`.
- Move a figure/notebook/code block to `shared/` only if two+ lectures reuse
  it.
- Curated outputs go in `results/`. Large raw output and logs stay untracked;
  do not commit `results/**/raw/`.

## Git

- Commit coherent units with meaningful messages (repo README and workflow docs
  require it). Pull `--ff-only` before editing; never force-push.
- On the lab PC: pull, work, commit, push. Keep Mac and lab in sync via GitHub.