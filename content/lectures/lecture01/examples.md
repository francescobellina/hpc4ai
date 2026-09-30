# Examples

## Example: complete Git round trip

On the Mac:

```bash
cd /Users/francesco/Desktop/hpc4ai
git pull --ff-only
# edit files in VS Code
git add -A
git commit -m "Add lecture notes"
git push
```

Later, on the lab PC:

```bash
cd hpc4ai
git pull --ff-only
```

## Example: course local workspace on the lab client

The course warm-up creates a directory named after the WILSON account. With the
confirmed username:

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

Run these commands on the lab client, not on WILSON.

## Example: connect to WILSON

From the lab client:

```bash
ssh fbellina2@wilson.mib.infn.it
```

Once the prompt is on WILSON, environment-module inspection commands include:

```bash
module list
module avail
```

Use only module names actually specified by the course or visible on WILSON.

## Example: file-transfer pattern

From the lab client to WILSON:

```bash
scp <SOURCE_FILE> fbellina2@wilson.mib.infn.it:<REMOTE_DESTINATION>
```

Back to the lab client:

```bash
scp fbellina2@wilson.mib.infn.it:<REMOTE_RESULT> <LOCAL_DESTINATION>
```

The placeholders are intentional: the exact file and remote directory depend on
the current exercise.
