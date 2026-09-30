# High-Performance Computing for AI Applications in Physics

Personal course repository and Jupyter Book for MSc/PhD-level notes, examples,
exercises, notebooks, and HPC experiments.

The repository uses **GitHub as the synchronization point between the two local
workstations**. WILSON is a separate HPC execution environment reached from the
laboratory client when an exercise requires cluster resources.

```text
VS Code on Mac                      GitHub                       VS Code on lab PC
/Users/francesco/Desktop/hpc4ai  <->  francescobellina/hpc4ai  <->  local clone
                                                                      |
                                                                      | ssh / scp
                                                                      v
                                                           fbellina2@wilson.mib.infn.it
```

Repository: <https://github.com/francescobellina/hpc4ai>

Course exercise used as the reference for the WILSON warm-up workflow:
<https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/from-client-to-wilson.html>

## Mac / VS Code

The project location on the Mac is fixed to:

```text
/Users/francesco/Desktop/hpc4ai
```

Open it from Terminal with:

```bash
cd /Users/francesco/Desktop/hpc4ai
code .
```

### First GitHub push

If the directory has just been extracted and Git has not yet been initialized:

```bash
cd /Users/francesco/Desktop/hpc4ai
git init
git branch -M main
git add .
git commit -m "Initial HPC4AI project structure"
git remote add origin https://github.com/francescobellina/hpc4ai.git
git push -u origin main
```

If `origin` already exists, do not add it again. Check or correct it with:

```bash
git remote -v
git remote set-url origin https://github.com/francescobellina/hpc4ai.git
```

### Python environment and local book preview with `uv`

First-time setup:

```bash
cd /Users/francesco/Desktop/hpc4ai
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

Start the live Jupyter Book preview:

```bash
cd /Users/francesco/Desktop/hpc4ai
uv run --python .venv/bin/python jupyter book start
```

The development server normally reports a local address such as:

```text
http://localhost:3000
```

Use the address printed by Jupyter Book if a different port is selected.

The wrapper scripts and VS Code tasks perform the same operations and fall back
to the local `.venv` when `uv` is unavailable:

```bash
./scripts/setup-env.sh
./scripts/preview.sh
./scripts/build.sh
./scripts/check.sh
./scripts/clean.sh
```

## Lab PC: clone once, then pull/push

On the first laboratory session only:

```bash
git clone https://github.com/francescobellina/hpc4ai.git
cd hpc4ai
code .
./scripts/setup-env.sh
```

After the first clone, do **not** clone the repository again each week. At the
start of a lab session:

```bash
cd hpc4ai
git status
git pull --ff-only
```

After a coherent unit of work:

```bash
git add -A
git status
git commit -m "Describe the work done in the lab"
git push
```

When you return to the Mac:

```bash
cd /Users/francesco/Desktop/hpc4ai
git status
git pull --ff-only
```

The safest habit is: **pull before editing and push before switching computer**.

## WILSON access used by this project

The confirmed login identity for the notes is:

```text
WILSON username: fbellina2
WILSON host:     wilson.mib.infn.it
SSH login:       fbellina2@wilson.mib.infn.it
```

Connect from the laboratory client with:

```bash
ssh fbellina2@wilson.mib.infn.it
```

The warm-up exercise on the course site uses a local workspace named after the
WILSON username. With the project username substituted, the first-time local
workspace commands are:

```bash
cd
pwd
echo $HOME
mkdir fbellina2
cd fbellina2
mkdir hpc-lab-exercise
cd hpc-lab-exercise
pwd
```

When a course exercise transfers a file between the laboratory client and
WILSON, use the actual exercise filename while keeping the confirmed login:

```bash
# lab client -> WILSON
scp <SOURCE_FILE> fbellina2@wilson.mib.infn.it:<REMOTE_DESTINATION>

# WILSON -> lab client (run this on the lab client)
scp fbellina2@wilson.mib.infn.it:<REMOTE_RESULT> <LOCAL_DESTINATION>
```

Do not invent a remote directory, module name, scheduler command, or benchmark
result. Record those only when they are explicitly given by the course or
confirmed in the laboratory.

## Repository structure

Each lecture is a self-contained teaching unit. Theory, examples, exercises,
notebooks, source code, input data, and figures live close to one another.
Cross-lecture material lives in `shared/` or `content/reference/`.

```text
hpc4ai/
├── README.md
├── myst.yml                  # Jupyter Book 2 / MyST configuration
├── toc.yml                   # book navigation / table of contents
├── requirements.txt
├── environment.yml
├── .gitignore
├── .editorconfig
├── .gitattributes
│
├── content/
│   ├── index.md
│   ├── preface/
│   ├── workflow/
│   ├── lectures/
│   │   ├── lecture01/
│   │   │   ├── index.md
│   │   │   ├── theory.md
│   │   │   ├── examples.md
│   │   │   ├── exercises/
│   │   │   ├── notebooks/
│   │   │   ├── code/
│   │   │   ├── data/
│   │   │   └── figures/
│   │   ├── lecture02/
│   │   ├── ...
│   │   └── lecture13/
│   └── reference/
│
├── shared/                   # resources reused by multiple lectures
├── results/                  # small curated results; raw output stays untracked
├── scripts/                  # setup, build, preview, checks, cluster helpers
├── templates/                # reusable lecture/exercise/notebook templates
├── assets/                   # site-wide CSS/images/figures
├── config/                   # cluster connection values; never credentials
├── .github/workflows/        # CI + GitHub Pages deployment
└── .vscode/                  # shared VS Code settings, tasks, extensions
```

## Lecture structure

A lecture is not forced into a rigid number of pages, but it should follow a
coherent progression:

```text
Theory -> worked examples -> exercises -> code/notebooks -> analysis/results
```

Typical layout:

```text
lectureXX/
├── index.md
├── theory.md
├── examples.md
├── exercises/
│   ├── index.md
│   └── exerciseNN.md
├── notebooks/
├── code/
├── data/
└── figures/
```

Exercises should have a clear objective and should use `.md`, `.ipynb`, `.py`,
`.c`, `.cpp`, `.h`, `.sh`, or data files only when appropriate to the task.
Solutions are intended to be visible but collapsed by default in the rendered
book.

## Jupyter Book

This starter targets **Jupyter Book 2 / MyST**. New Jupyter Book 2 projects use
`myst.yml`; navigation is kept in `toc.yml` for readability. The older
`_config.yml` / `_toc.yml` layout is intentionally not used.

Useful commands:

```bash
./scripts/preview.sh     # live local preview
./scripts/build.sh       # strict HTML build
./scripts/check.sh       # project checks + strict build
./scripts/clean.sh       # remove generated _build files
```

The same commands are available from **VS Code -> Terminal -> Run Task**.

## GitHub Pages

The repository contains CI and deployment workflows. After pushing the repository
to GitHub, enable **Settings -> Pages -> GitHub Actions**. Deployment is triggered
by pushes to `main`.

For this repository the expected project-site path is:

```text
https://francescobellina.github.io/hpc4ai/
```

## Security

Never commit passwords, SSH private keys, personal access tokens, or temporary
authentication files. The WILSON username and hostname are connection metadata,
not credentials; the password/key remains outside Git.
