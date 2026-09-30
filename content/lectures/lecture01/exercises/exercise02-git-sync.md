# Exercise 1.2 — Complete a GitHub synchronization round trip

## Objective

Practice the sequence used to move work from one computer to the other via
GitHub.

## Procedure

On the current machine:

```bash
git status
git pull --ff-only
```

Make a small edit, then:

```bash
git add -A
git status
git commit -m "Practice repository synchronization"
git push
```

On the second machine:

```bash
git status
git pull --ff-only
```

## Questions

- Why should `pull` happen before editing?
- What is the difference between `commit` and `push`?

::::{dropdown} Solution / discussion
:color: success

A commit records a version locally. Push publishes local commits to GitHub.
Pull retrieves remote commits. Pulling before editing reduces divergence.

::::
