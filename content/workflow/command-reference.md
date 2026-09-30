# Workflow command reference

## Mac project

```bash
cd /Users/francesco/Desktop/hpc4ai
code .
```

## GitHub repository

```text
https://github.com/francescobellina/hpc4ai
```

```bash
git remote -v
git status
git pull --ff-only
git add -A
git commit -m "message"
git push
git log --oneline --decorate --graph -10
```

## First lab clone

```bash
git clone https://github.com/francescobellina/hpc4ai.git
cd hpc4ai
code .
```

## WILSON

```bash
ssh fbellina2@wilson.mib.infn.it
```

Transfer patterns from the lab client:

```bash
scp <SOURCE_FILE> fbellina2@wilson.mib.infn.it:<REMOTE_DESTINATION>
scp fbellina2@wilson.mib.infn.it:<REMOTE_RESULT> <LOCAL_DESTINATION>
```

Lmod inspection on WILSON:

```bash
module avail
module list
```

## Book with `uv`

```bash
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
uv run --python .venv/bin/python jupyter book start
```

Normal local preview address: `http://localhost:3000` (use the port printed by
the server if it differs).

## Wrapper scripts

```bash
./scripts/setup-env.sh
./scripts/preview.sh
./scripts/build.sh
./scripts/check.sh
./scripts/clean.sh
```
