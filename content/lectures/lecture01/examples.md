# Esempi svolti

**Giro completo con Git.** Sul Mac:

```bash
cd /Users/francesco/dev/hpc4ai
git pull --ff-only
# modifica i file in VS Code
git add -A
git commit -m "Add lecture notes"
git push
```

Più tardi, sul PC di laboratorio:

```bash
cd hpc4ai
git pull --ff-only
```

**Workspace locale del corso sul client.** Il warm-up crea una directory col nome
dell'account WILSON:

```bash
cd
mkdir fbellina2
cd fbellina2
mkdir hpc-lab-exercise
cd hpc-lab-exercise
pwd
```

Esegui questi comandi sul client, non su WILSON.

**Connettersi a WILSON e ispezionare i moduli.**

```bash
ssh fbellina2@wilson.mib.infn.it
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module list
module avail
```

Usa solo nomi di moduli indicati dal corso o visibili su WILSON.

**Compilare ed eseguire OpenMP.**

```bash
gcc -fopenmp -o thread-count thread-count.c
OMP_NUM_THREADS=4
export OMP_NUM_THREADS
./thread-count
```

**Trasferimento file.**

```bash
# client -> WILSON
scp <FILE_SORGENTE> fbellina2@wilson.mib.infn.it:<DESTINAZIONE_REMOTA>

# WILSON -> client
scp fbellina2@wilson.mib.infn.it:<RISULTATO_REMOTO> <DESTINAZIONE_LOCALE>
```

I segnaposto sono intenzionali: file e directory remote dipendono dall'esercizio.
