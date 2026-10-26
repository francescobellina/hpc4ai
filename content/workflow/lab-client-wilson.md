# Guida operativa al cluster WILSON

Questa guida raccoglie le procedure WILSON che compaiono negli appunti e negli esercizi. Controlla sempre dove gira il comando: **client di laboratorio** e **WILSON** sono macchine distinte.

## Dati disponibili e limiti

Il repository conferma questi dati di accesso:

| Dato | Valore |
|---|---|
| Username | `fbellina2` |
| Host | `wilson.mib.infn.it` |
| Login | `fbellina2@wilson.mib.infn.it` |

Il repository cita un percorso Lmod e versioni GCC/OpenMPI negli esempi del corso. Non sono qui trattati come configurazione garantita: verifica sul cluster i moduli, i percorsi, la disponibilità dello scheduler, le partizioni e le istruzioni di esecuzione. Non sono presenti risultati di job WILSON verificati.

## Accesso, directory e trasferimento

Dal client raggiungibile:

```bash
ssh fbellina2@wilson.mib.infn.it
```

`ssh` apre una shell remota. Una volta collegato, usa `pwd` e `echo "$HOME"` per verificare la directory e l'ambiente effettivi. Il repository non fissa una directory di lavoro remota: usa quella indicata dall'esercizio o confermata in laboratorio.

Esegui `scp` sul client. Sostituisci i segnaposto con file e destinazioni dati dall'esercizio:

```bash
# Client -> WILSON; la destinazione vuota dopo ':' usa la home remota predefinita.
scp <FILE_LOCALE> fbellina2@wilson.mib.infn.it:<DESTINAZIONE_REMOTA>

# WILSON -> client.
scp fbellina2@wilson.mib.infn.it:<FILE_REMOTO> <DESTINAZIONE_LOCALE>
```

`exit` o `Ctrl+D` chiudono la sessione SSH. `scp` e `ssh` non trasferiscono automaticamente le variabili della shell: imposta `OMP_NUM_THREADS` nella sessione in cui esegui il programma.

## Moduli software

Negli appunti del corso compare questo percorso per l'albero `Core`; verifica che sia corretto e disponibile nella sessione WILSON prima di usarlo:

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module avail
module spider GCC/13.2.0
module spider OpenMPI/4.1.6
module list
```

Gli stessi appunti citano `GCC/13.2.0` e `OpenMPI/4.1.6`. Carica solo i moduli richiesti dall'esercizio e confermati da `module spider`:

```bash
module load GCC/13.2.0
module load OpenMPI/4.1.6
module list
```

| Comando | Funzione | Da adattare |
|---|---|---|
| `module use <PERCORSO>` | Aggiunge un albero di moduli alla ricerca | Percorso comunicato o verificato su WILSON |
| `module avail` | Elenca moduli direttamente disponibili | Nessuno |
| `module spider <NOME/VERSIONE>` | Cerca un modulo e i prerequisiti | Nome e versione richiesti dall'esercizio |
| `module load <NOME/VERSIONE>` | Attiva un modulo | Nome e versione confermati |
| `module list` | Mostra moduli attivi | Nessuno |

## Compilazione ed esecuzione

Questi comandi seguono gli esempi presenti nel repository. Sostituisci nomi dei file e output. Il compilatore e la versione dipendono dall'ambiente attivo.

| Caso | Esempio | Funzione |
|---|---|---|
| C sequenziale | `gcc -Wall -Wextra -o prog prog.c` | Compila un programma C |
| C OpenMP | `gcc -fopenmp -o prog prog.c` | Abilita le direttive OpenMP |
| C MPI | `mpicc -o prog prog.c` | Compila tramite il wrapper MPI |
| C MPI + OpenMP | `mpicc -fopenmp -o prog prog.c` | Compila codice che usa entrambi i modelli |
| Esecuzione | `./prog` | Avvia il programma nella directory corrente |

Per un test OpenMP breve, imposta il numero richiesto di thread nella shell corrente:

```bash
export OMP_NUM_THREADS=4
./prog
```

Il valore `4` è un esempio: adattalo alla richiesta di risorse e al programma. Per un solo comando si può usare `OMP_NUM_THREADS=4 ./prog`. La variabile configura il runtime OpenMP; non assegna risorse Slurm da sola.

Per un programma MPI, gli appunti usano `mpiexec -n`:

```bash
mpiexec -n <NUMERO_RANK> ./prog
```

`<NUMERO_RANK>` è il numero di processi MPI richiesti. Il lanciatore e le opzioni accettate vanno verificati per l'ambiente e l'esercizio. MPI può avviare più processi sullo stesso nodo o distribuirli su più nodi.

Esempio ibrido illustrativo con due processi e quattro thread per processo:

```bash
export OMP_NUM_THREADS=4
mpiexec -n 2 ./prog
```

Il totale è otto thread software. Conferma che risorse, launcher e affinità corrispondano all'esercizio; il comando non richiede di per sé due nodi.

## Job Slurm

Il materiale del corso indica Slurm e `srun` per i calcoli sui nodi di calcolo, ma non documenta una configurazione WILSON verificata. I seguenti nomi e script sono **esempi generici di Slurm**, non istruzioni ufficiali per WILSON. Conferma partizione, limiti, tempo, opzioni e metodo di lancio con il corso o il laboratorio. Non aggiungere `--partition`, `--constraint` o un numero di nodi senza indicazioni attendibili.

Un esempio OpenMP generico:

```bash
#!/usr/bin/env bash
#SBATCH --job-name=omp-demo
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:05:00
#SBATCH --output=omp-%j.out

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
srun ./prog
```

Un esempio MPI generico:

```bash
#!/usr/bin/env bash
#SBATCH --job-name=mpi-demo
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
#SBATCH --output=mpi-%j.out

export OMP_NUM_THREADS=1
srun -n "${SLURM_NTASKS}" ./prog
```

Per un job ibrido, si richiedono più task MPI e più CPU per task; per esempio, `--ntasks=2` con `--cpus-per-task=4` e `OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"`. Il totale dei thread OpenMP è $P \times T$, con $P$ rank e $T$ thread per rank. Questa combinazione non impone due nodi: la collocazione va richiesta e verificata separatamente.

| Comando Slurm generico | Funzione | Argomenti da adattare |
|---|---|---|
| `sbatch <SCRIPT>` | Invia uno script batch | Script e risorse approvate |
| `squeue -u "$USER"` | Controlla i job dell'utente | Utente, se necessario |
| `scancel <JOB_ID>` | Cancella un job | ID mostrato dal sistema |
| `srun <COMANDO>` | Avvia un comando nelle risorse assegnate | Numero di task, comando e opzioni previste dal sito |

Gli esempi non attestano che ogni comando o flag sia abilitato su WILSON. Per le esercitazioni, il materiale raccomanda controlli molto brevi sul nodo di login e l'uso di Slurm per i calcoli reali; segui le istruzioni aggiornate del corso.

## Controlli e diagnostica

Questi strumenti sono comandi Linux generici; verifica la loro disponibilità e le regole d'uso sul sistema. I processi di calcolo vanno controllati dentro l'allocazione pertinente.

| Comando o metodo | Cosa controlla | Nota |
|---|---|---|
| `hostname` | Nome del nodo corrente | Eseguilo nel processo o job da verificare |
| `lscpu` | CPU logiche e informazioni CPU visibili | Non sostituisce i dati dell'allocazione Slurm |
| `ps -eLf` | Processi e thread visibili | Può elencare più del proprio job; adattare filtri e PID |
| `taskset -pc <PID>` | Maschera CPU consentita per il PID | Il PID può identificare un processo o un thread; dipende da come lo si rileva |
| `scontrol show job <JOB_ID>` | Dettagli dell'allocazione Slurm | Comando generico; accesso e campi dipendono dal sito |
| `sched_getaffinity` nel programma | CPU consentite al processo/thread rilevato | L'interpretazione dipende dal metodo e dal PID usato |

Una maschera indica CPU consentite, non necessariamente la CPU usata in ogni istante. Distingui l'affinità del processo da quella del singolo thread e confronta i dati con l'allocazione effettiva.

## Errori frequenti

| Sintomo | Controllo |
|---|---|
| `module` o un compilatore non trovato | Verifica shell remota, `module use` solo se il percorso è confermato, moduli attivi e nome/versione con `module spider` |
| Il programma OpenMP usa un numero inatteso di thread | Verifica che `OMP_NUM_THREADS` sia impostata nella stessa shell e che il programma entri in una regione parallela |
| Il job richiede un numero di CPU diverso dai thread OpenMP | Allinea `OMP_NUM_THREADS` a `--cpus-per-task` quando previsto dall'esercizio e controlla le risorse allocate |
| MPI avvia un numero inatteso di processi | Confronta il numero di rank richiesto con `mpiexec -n` o con i task Slurm e verifica l'output del programma |
| Il comando di lancio o un'opzione viene rifiutato | Usa il launcher e le opzioni indicate per l'ambiente WILSON effettivo; gli esempi generici non attestano il supporto locale |
| Il job non è visibile o è terminato | Controlla `squeue -u "$USER"`, lo stato del job e i file di output indicati nello script |

## Riepilogo

1. Accedi dal client con `ssh`; controlla host e directory remota.
2. Verifica moduli e versioni con `module spider` prima di caricarli.
3. Compila con il wrapper e le opzioni richieste dal programma.
4. Imposta `OMP_NUM_THREADS` coerentemente con le risorse assegnate.
5. Usa Slurm per job reali solo seguendo le istruzioni WILSON confermate.
6. Registra comando, moduli, dimensione del problema, risorse e output verificato.

Non salvare password, chiavi private, token o file di autenticazione nel repository.
