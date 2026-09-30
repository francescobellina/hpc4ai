# Exercise 1.1 — Create the local course workspace

## Objective

Reproduce the first step of the course warm-up and create a local workspace that
is clearly associated with the WILSON username `fbellina2`.

## Run on

**Lab client** (the local machine used in the laboratory), not WILSON.

## Procedure

For the first creation of the workspace, run:

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

The first `pwd` shows the local home directory. The last `pwd` should point to a
path ending in:

```text
fbellina2/hpc-lab-exercise
```

## Questions

- Why is the directory named after the WILSON username?
- Why should the lab-client workspace not be confused with the remote WILSON home?
- What does `$HOME` contain before and after changing directories?

::::{dropdown} Solution / expected checks
:color: success

The workspace exists on the lab client under a directory named `fbellina2`, and
the shell is inside `hpc-lab-exercise`. `$HOME` continues to refer to the local
account's home directory even after `cd` changes the current working directory.

::::
