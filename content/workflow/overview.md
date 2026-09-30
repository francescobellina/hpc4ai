# Workflow overview

The repository uses **GitHub as the central synchronization point** between the
Mac at home and the laboratory PC. WILSON is reached separately from the lab
client for HPC work.

```text
                         +--------------------------------------+
                         |                GitHub                |
                         | francescobellina/hpc4ai (canonical)  |
                         +-------------------+------------------+
                                             ^
                                    push/pull|push/pull
                     +-----------------------+-----------------------+
                     |                                               |
        +------------+-------------+                    +------------+----------+
        | Mac / VS Code            |                    | Lab PC / VS Code      |
        | /Users/francesco/Desktop |                    | local Git clone       |
        | /hpc4ai                   |                    +------------+----------+
        +--------------------------+                                 |
                                                                     | ssh / scp
                                                                     v
                                                        +------------+----------+
                                                        | WILSON                |
                                                        | fbellina2             |
                                                        | @wilson.mib.infn.it   |
                                                        +-----------------------+
```

## The key distinction

The **lab PC** is where the Git repository is cloned and edited during laboratory
sessions. **WILSON** is the remote HPC execution environment. Do not treat them as
the same machine in commands or notes.

## Golden rule

**Pull before you start editing; push before you move to the other computer.**

## Home / Mac

```bash
cd /Users/francesco/Desktop/hpc4ai
git status
git pull --ff-only
# edit / test / write in VS Code
git add -A
git commit -m "Describe the change"
git push
```

## First lab session

Clone only once:

```bash
git clone https://github.com/francescobellina/hpc4ai.git
cd hpc4ai
code .
```

## Later lab sessions

```bash
cd hpc4ai
git status
git pull --ff-only
# edit / run / collect useful results
git add -A
git commit -m "Describe the lab work"
git push
```

## Cluster step when required

From the lab client:

```bash
ssh fbellina2@wilson.mib.infn.it
```

File transfers required by an exercise use `scp`; Git synchronization remains
Mac <-> GitHub <-> lab PC unless the course explicitly instructs otherwise.
