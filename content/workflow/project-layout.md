# Project layout

The book follows the course site: theory first, then exercises, then the report.

```text
content/
├── teoria/       # Part I: macro-chapters 01–06 + glossary, figures/, notebooks/
├── esercizi/     # Part II: warm-up/, esNN-<slug>.md, riepilogo, figures/, notebooks/
├── relazione/    # Part III: English report, exported to PDF
├── workflow/     # working environment and WILSON guide
└── reference/    # short reusable references (Linux, Git, MPI, ...)
codes/execN/      # full source per exercise, with README
results/esNN/     # curated logs used by the exercise pages
```

| Location | Purpose |
|---|---|
| `content/teoria/` | Theory by topic, following the six course chapters |
| `content/esercizi/` | One page per exercise with the full lab notebook; each links to its theory |
| `content/relazione/` | The report to submit: an English synthesis of the exercises |
| `codes/` | Full source, batch scripts and analysis scripts (excluded from the build) |
| `results/` | Small curated outputs useful for reproducibility |

Large raw output, temporary files and machine-generated logs normally stay
untracked. `content/reference/` holds short reusable explanations for recurring
tools so they are not repeated in every chapter.
