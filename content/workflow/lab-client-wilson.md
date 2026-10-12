# Guida al laboratorio: client e WILSON

Adatta il warm-up del corso **From the client to WILSON** al workflow personale di
questo repository, con l'username WILSON confermato `fbellina2`.

| Ambiente | Ruolo |
|---|---|
| Client di laboratorio (Raspberry Pi 5) | terminale locale, clone Git, compilazione o modifiche locali |
| WILSON | ambiente HPC remoto, `fbellina2@wilson.mib.infn.it` |

Prima di premere Invio, controlla il prompt per sapere dove girerà il comando. Il
client usa l'account condiviso `student`: spazio temporaneo, non privato e non
salvato.

## Flusso

1. **Workspace locale** (sul client):
   ```bash
   cd
   mkdir fbellina2
   cd fbellina2
   mkdir hpc-lab-exercise
   cd hpc-lab-exercise
   ```
   Il workspace è separato dal clone Git di `hpc4ai`.

2. **Compila ed esegui in locale**:
   ```bash
   gcc -fopenmp -o thread-count thread-count.c
   OMP_NUM_THREADS=4 ./thread-count > local-output.txt
   ```

3. **Trasferisci il sorgente e connettiti**:
   ```bash
   scp thread-count.c fbellina2@wilson.mib.infn.it:
   ssh fbellina2@wilson.mib.infn.it
   ```

4. **Prepara l'ambiente software su WILSON**:
   ```bash
   module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
   module spider GCC/13.2.0
   module load GCC/13.2.0
   ```

5. **Esegui da remoto e salva**. `scp`/`ssh` non trasferiscono le variabili di
   shell: `OMP_NUM_THREADS` va ridefinita sulla shell remota.
   ```bash
   gcc -fopenmp -o thread-count thread-count.c
   OMP_NUM_THREADS=4 ./thread-count > wilson-output.txt
   head -n 5 wilson-output.txt
   exit
   ```

6. **Riporta il risultato sul client**:
   ```bash
   scp fbellina2@wilson.mib.infn.it:hpc-lab-exercise/wilson-output.txt .
   ```
   Poi conserva sorgenti, note e risultati piccoli nel repository e sincronizza con
   GitHub (`git add -A`, `git commit`, `git push`).

Non committare password, chiavi SSH, token o file di autenticazione. Non inventare
path remoti, nomi di moduli, comandi dello scheduler o valori non confermati.

## Riferimento rapido

| Attività | Comando | Dove |
|---|---|---|
| Connettersi a WILSON | `ssh -l fbellina2 wilson.mib.infn.it` | client |
| Copiare su WILSON | `scp file fbellina2@wilson.mib.infn.it:` | client |
| Riportare dal cluster | `scp fbellina2@wilson.mib.infn.it:file .` | client |
| Cambiare password | `passwd` | WILSON |
| Aggiungere l'albero Core | `module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core` | WILSON |
| Cercare un modulo | `module spider NOME` | WILSON |
| Caricare GCC | `module load GCC/13.2.0` | WILSON |
| Compilare OpenMP | `gcc -fopenmp -o prog prog.c` | client o WILSON |
| Impostare i thread | `OMP_NUM_THREADS=4` + `export` | client o WILSON |

Vedi anche [Riferimento Linux](../reference/linux.md), [Riferimento Lmod](../reference/lmod.md)
e [Riferimento Python](../reference/python.md).
