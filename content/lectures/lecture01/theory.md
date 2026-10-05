# Theory — TEORIA DI BASE e poi client, repository, and cluster

Prime due slides sui concetti di base di HPC e nozioni storiche.
Da tenere a mente:


Si passa poi a parlare di WILSON, con i comandi di base, salvataggio di programmi, righe di comando, e gestione dei file.
## Three different roles

A practical HPC workflow often separates:

- **development environment**: where code and notes are edited;
- **version-control service**: where history is synchronized and preserved;
- **execution environment**: where computational workloads run.

In this project those roles are represented by VS Code on the Mac or lab PC,
GitHub, and WILSON respectively.

## Reproducibility

A useful HPC repository should make it possible to answer:

1. Which source code produced a result?
2. Which input data and parameters were used?
3. Which software environment was loaded?
4. On which environment was the command executed?

## Environment modules

Lmod changes the active software environment by modifying shell environment
variables. Exact modules are system-specific and should only be documented after
confirmation.
