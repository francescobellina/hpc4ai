# Memoria distribuita e MPI

:::{seealso} Fonte principale
Capitolo 6 del corso, [*Distributed memory and MPI*](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/mpi.html). Questa pagina riordina le note già scritte secondo la struttura di quel capitolo.
:::

(mpi-memoria-distribuita)=
## MPI e memoria distribuita

**MPI** è utile quando il calcolo viene distribuito tra più processi, anche sullo stesso nodo oppure su nodi diversi. I processi possiedono normalmente spazi di indirizzamento separati e comunicano tramite messaggi. Un **rank MPI** identifica un processo nel gruppo di comunicazione.

MPI non richiede necessariamente più nodi. La collocazione dei rank dipende dall'esecuzione e dalle risorse assegnate. Quando i dati sono distribuiti, il programma deve definire quali dati appartengono a ciascun processo e quali messaggi servono per scambiare informazioni.

Le comunicazioni **point-to-point** scambiano dati tra rank; le operazioni **collettive** coordinano un gruppo, per esempio per distribuire dati o combinare risultati. I partecipanti devono rispettare il protocollo e l'ordine richiesto. Attese incompatibili possono causare un deadlock, nel quale i processi aspettano eventi che non possono più verificarsi.

(t-mpi-spmd)=
### SPMD, comunicazioni e deadlock

Uno standard per programmi fatti di processi che non condividono memoria.
Ogni processo ha la propria RAM, e l'unico modo per ottenere dati da un altro
processo è riceverli in un messaggio. Lo stesso programma gira su un portatile
e su migliaia di nodi di un supercomputer.

Il modello di esecuzione è **SPMD** (Single Program, Multiple Data): tutti i
processi eseguono lo stesso programma e si distinguono per il proprio *rank*
(da 0 a `size - 1`).

Oggetti principali:

- **communicator**: il gruppo di processi autorizzati a comunicare
  (`MPI_COMM_WORLD` sono tutti; `split` crea sottogruppi);
- **point-to-point**: `Send` e `Recv` fra due rank;
- **collective**: operazioni che coinvolgono tutto il communicator —
  `broadcast`, `scatter`, `gather`, `reduce`, `all-reduce`, `alltoall`,
  `barrier`.

Le collective sono implementate con algoritmi ad albero, quindi scalano in modo
logaritmico e sono molto più veloci di scambi point-to-point scritti a mano.

**Bloccanti e non bloccanti.** `Send`/`Recv` tornano solo quando il buffer è
riutilizzabile; `Isend`/`Irecv` tornano subito e vengono completate dopo con
`Wait`. Le non bloccanti sono il modo per sovrapporre comunicazione e calcolo.

**Deadlock.** Se due processi fanno entrambi `Send` prima di entrambi `Recv`,
e i messaggi sono abbastanza grandi da usare il protocollo rendezvous, ciascuno
aspetta un ricevente che è a sua volta bloccato in una `Send`. Si usa
`Sendrecv`, oppure si rende asimmetrico l'ordine (i rank pari inviano, i
dispari ricevono).

**Halo / celle fantasma.** Nelle simulazioni su griglia ogni processo possiede
una regione e ha bisogno dei bordi dei vicini. I bordi scambiati sono l'*halo*,
le copie sono le *celle fantasma*. È il pattern di comunicazione più comune nei
codici fluidodinamici, elettromagnetici e di dinamica molecolare.

```bash
mpirun -n 4 python mpi_demo.py   # aggiungere --oversubscribe se gli slot sono limitati
```

Vedi [reference/mpi](../reference/mpi.md).

(ibrido-mpi-openmp)=
## Programmazione ibrida MPI + OpenMP

**Hybrid** significa ibrido: vengono combinati due livelli di parallelismo. MPI avvia processi; ciascun processo può usare OpenMP per creare thread. Con $P$ processi MPI e $T$ thread OpenMP per processo:

$$\text{Numero totale di thread} = \text{numero di processi MPI} \times \text{thread OpenMP per processo} = P \times T.$$

Per esempio, due processi MPI con quattro thread OpenMP ciascuno producono otto thread software totali. Questo conteggio non è il numero di CPU logiche e non prova che gli otto thread stiano eseguendo nello stesso istante. I processi possono stare sullo stesso nodo o su nodi differenti secondo la disposizione assegnata.

Di seguito, **output ipotetico**: serve a illustrare un processo MPI con quattro thread sullo stesso nodo, non è un risultato verificato su WILSON.

```text
Node: node01  MPI rank: 0  Thread: 0  CPUs: 0-3
Node: node01  MPI rank: 0  Thread: 1  CPUs: 0-3
Node: node01  MPI rank: 0  Thread: 2  CPUs: 0-3
Node: node01  MPI rank: 0  Thread: 3  CPUs: 0-3
```

- `Node`: il nodo sul quale è in esecuzione il processo.
- `MPI rank`: l'identificativo del processo MPI.
- `Thread`: l'identificativo del thread all'interno del processo.
- `CPUs`: le CPU logiche consentite secondo il metodo di rilevamento usato dal programma.

Le CPU consentite non sono necessariamente quelle utilizzate dal thread in ogni istante. `CPUs` può descrivere l'affinità del processo oppure quella del singolo thread, secondo l'implementazione. Una maschera uguale su più righe non dimostra che tutti i thread siano fissati sulla stessa CPU.

Se due processi fossero collocati su nodi distinti, ogni nodo avrebbe normalmente una numerazione locale delle CPU. Perciò `CPU 0` su un nodo non indica la stessa CPU fisica di `CPU 0` su un altro nodo.

### Riepilogo: memoria condivisa, distribuita, ibrido

Due modelli di memoria, e la loro combinazione:

- **Memoria condivisa (thread)** — più thread in un unico spazio di indirizzi,
  dentro un solo processo. In OpenMP il numero di thread è controllato da
  `OMP_NUM_THREADS`.
- **Memoria distribuita (processi)** — i rank MPI sono processi separati, anche su
  nodi diversi, avviati con `mpiexec` o `srun` e comunicanti via messaggi.
- **Ibrido** — più rank per nodo, ciascuno con più thread OpenMP. Con $P$ rank e
  $T$ thread per rank si ottengono $P \times T$ linee di attività.

L'**affinità di CPU** (maschera dei core assegnati) determina dove girano
davvero thread e processi; va verificata, non solo richiesta.
