# Lab client and WILSON

This page adapts the operational sequence of the course warm-up **From the
client to WILSON** to this personal repository. The example username used in the
course material is replaced here by the confirmed WILSON username `fbellina2`.

Course reference:
<https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/from-client-to-wilson.html>

## Environments

1. **Lab client** — local terminal/VS Code, Git clone, local compilation or edits.
2. **WILSON** — remote HPC environment reached as `fbellina2@wilson.mib.infn.it`.

Always check the shell prompt before pressing Enter so that you know where the
command will run.

## 1. Create the local course workspace

Run these commands on the **lab client**, following the layout used by the course
exercise:

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

The first and last `pwd` calls should report different directories; the exercise
workspace ends in `fbellina2/hpc-lab-exercise`.

This course workspace is separate from the Git clone of `hpc4ai`. Keep that
distinction explicit in your notes.

## 2. Write and compile locally

The course warm-up uses a small OpenMP program. Keep the program filename and
compiler command exactly as specified by the exercise you are following. Do not
invent a different module, compiler, or flag just to fill the documentation.

## 3. Configure and run locally

The course exercise configures the local run, redirects output, and inspects the
result before moving to WILSON. Record the exact environment variable, command,
and output filename alongside the exercise when you perform it.

## 4. Transfer the source and connect to WILSON

The confirmed login command is:

```bash
ssh fbellina2@wilson.mib.infn.it
```

When the exercise asks you to transfer a source file from the lab client to
WILSON, use the real filename and destination given by the exercise:

```bash
scp <SOURCE_FILE> fbellina2@wilson.mib.infn.it:<REMOTE_DESTINATION>
```

The placeholders deliberately prevent an unverified remote path from being
hard-coded.

## 5. Prepare the software environment on WILSON

WILSON uses environment modules through Lmod. Useful inspection commands are:

```bash
module avail
module list
```

Load only the module names required by the course exercise or confirmed with
`module avail`/the laboratory instructions. Do not infer module versions.

## 6. Run remotely and save the result

Run the compile/program commands on WILSON exactly as required by the active
exercise. Save result filenames that are small and useful for reproducibility;
do not commit large raw output blindly.

## 7. Copy the result back to the lab client

Run the copy-back command from the **lab client** after leaving the remote shell
(or from another local terminal):

```bash
scp fbellina2@wilson.mib.infn.it:<REMOTE_RESULT> <LOCAL_DESTINATION>
```

Then preserve useful source, notes, and small results in the appropriate lecture
folder of the Git repository and synchronize them through GitHub:

```bash
cd hpc4ai
git status
git add -A
git commit -m "Record WILSON exercise results"
git push
```

## Important separation of responsibilities

```text
Mac <-> GitHub <-> lab PC     version control / synchronization
lab client <-> WILSON         ssh/scp + HPC execution for course exercises
```

Do not commit passwords, SSH private keys, access tokens, or authentication
files. Do not invent WILSON-specific remote paths, module names, scheduler
commands, or output values that have not been confirmed.
