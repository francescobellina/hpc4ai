# Project layout

The repository is organized around **self-contained lectures**.

## Lecture-local resources

```text
content/lectures/lectureXX/
├── index.md
├── theory.md
├── examples.md
├── exercises/
├── notebooks/
├── code/
├── data/
└── figures/
```

| Location | Purpose |
|---|---|
| `index.md` | Lecture landing page, objectives, prerequisites, contents |
| `theory.md` | Concise theory, equations, definitions, HPC/physics context |
| `examples.md` | Worked examples that bridge theory and exercises |
| `exercises/` | Practical tasks with objectives, procedure, questions, solutions |
| `notebooks/` | Interactive Python, analysis, plots, ML or result interpretation |
| `code/` | `.py`, `.c`, `.cpp`, `.h`, `.sh` and other source/executable files |
| `data/` | Small lecture-specific inputs or curated datasets |
| `figures/` | Lecture-specific diagrams and figures |

Not every lecture needs the same number of files. Empty directories are kept in
Git with `.gitkeep` until needed.

## Shared resources

Use `shared/` only when a resource is genuinely reused by more than one lecture.

## Results

Use `results/` for small outputs useful for reproducibility. Large raw output,
temporary files, and machine-generated logs should normally remain untracked.

## Reference material

`content/reference/` contains short reusable explanations for recurring tools so
they do not need to be re-explained in every lecture.
