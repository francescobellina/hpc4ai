# Exercise 1.3 — Transfer, connect, and document a WILSON session

## Objective

Practice the boundary between the laboratory client and WILSON without storing
credentials or inventing cluster-specific settings.

## 1. Connect from the lab client

```bash
ssh fbellina2@wilson.mib.infn.it
```

Before running further commands, check the shell prompt and confirm that the
session is remote.

## 2. Inspect the software environment on WILSON

```bash
module list
module avail
```

Load only modules explicitly required by the active course exercise. Do not guess
module names or versions.

## 3. Transfer a source file when required

Run `scp` on the lab client using the actual source file and destination required
by the exercise:

```bash
scp <SOURCE_FILE> fbellina2@wilson.mib.infn.it:<REMOTE_DESTINATION>
```

## 4. Run and save the remote result

Compile/run on WILSON according to the current exercise. Record the commands,
software environment, and result filename in your notes.

## 5. Copy the result back

From the lab client:

```bash
scp fbellina2@wilson.mib.infn.it:<REMOTE_RESULT> <LOCAL_DESTINATION>
```

Then place only useful source, notes, or small curated results in the Git
repository and synchronize them through GitHub.

## Important

Do **not** add passwords, SSH private keys, GitHub tokens, or authentication
files to this repository. A username and hostname are not sufficient to
authenticate and are safe to document; credentials remain outside Git.

::::{dropdown} Solution / expected outcome
:color: success

The session clearly distinguishes lab-client and WILSON commands, uses the login
`fbellina2@wilson.mib.infn.it`, records only confirmed software configuration,
and transfers only the files required by the exercise. No credentials are stored
in Git.

::::
