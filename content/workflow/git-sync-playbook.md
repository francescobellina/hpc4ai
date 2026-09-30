# Git synchronization playbook

## Start work on the Mac

```bash
cd /Users/francesco/Desktop/hpc4ai
git status
git switch main
git pull --ff-only
code .
```

## Start work on the lab PC

After the repository has been cloned once:

```bash
cd hpc4ai
git status
git switch main
git pull --ff-only
code .
```

## Save a coherent change

```bash
git add -A
git status
git commit -m "Explain what changed"
git push
```

## Return home after a lab session

```bash
cd /Users/francesco/Desktop/hpc4ai
git status
git pull --ff-only
```

## If `git pull --ff-only` refuses

Do not force-push immediately. Inspect first:

```bash
git status
git log --oneline --decorate --graph -10
```

Common causes are uncommitted local edits, commits created independently on both
machines, or being on the wrong branch.
