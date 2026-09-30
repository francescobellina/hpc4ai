# VS Code, Git, and GitHub

Repository: <https://github.com/francescobellina/hpc4ai>

## Mac project path

```bash
cd /Users/francesco/Desktop/hpc4ai
code .
```

## First push from the Mac

Use this only if the local directory is not yet connected to GitHub:

```bash
cd /Users/francesco/Desktop/hpc4ai
git init
git branch -M main
git add .
git commit -m "Initial HPC4AI project structure"
git remote add origin https://github.com/francescobellina/hpc4ai.git
git push -u origin main
```

If `origin` is already configured:

```bash
git remote -v
git remote set-url origin https://github.com/francescobellina/hpc4ai.git
```

## First laboratory session: clone once

```bash
git clone https://github.com/francescobellina/hpc4ai.git
cd hpc4ai
code .
```

## Every later session

Before changing files:

```bash
git status
git pull --ff-only
```

After a coherent unit of work:

```bash
git add -A
git status
git commit -m "Short meaningful description"
git push
```

## Return to the Mac

```bash
cd /Users/francesco/Desktop/hpc4ai
git status
git pull --ff-only
code .
```

## Local Jupyter Book preview with `uv`

First time:

```bash
cd /Users/francesco/Desktop/hpc4ai
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

Start the development server:

```bash
uv run --python .venv/bin/python jupyter book start
```

Open the address reported by the command, normally `http://localhost:3000`.

## Why `--ff-only`?

For this personal two-computer workflow, `git pull --ff-only` is a useful guard:
it updates the local branch only when Git can move it forward without creating
an unexpected merge commit. If the command refuses, inspect the state instead
of forcing a merge.

## VS Code tasks

Open **Terminal -> Run Task** for:

- `Environment: Setup / update`
- `Book: Preview`
- `Book: Build (strict)`
- `Book: Check`
- `Book: Clean`
- `Git: Status`
- `Git: Pull (ff-only)`
- `Git: Push`
- `WILSON: SSH from lab client`

The book and Git tasks work on macOS and Linux lab clients. The WILSON task is
intended to be used only from an environment that can reach the cluster.
