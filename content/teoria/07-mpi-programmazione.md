# Programmare con MPI

:::{seealso} Fonti
- Slide della lezione 9, *distributed memory and MPI* (33 slide, copia locale in
  `materials/9. distributed memory and MPI.pdf`).
- Capitolo 6 del sito del corso,
  [*Distributed memory and MPI*](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/mpi.html),
  sezioni 6.1–6.8.
- Standard di riferimento: [MPI 5.0](https://www.mpi-forum.org/docs/mpi-5.0/mpi50-report.pdf)
  (MPI Forum, giugno 2025).

Il capitolo 6 ({ref}`mpi-memoria-distribuita`) dà il quadro generale; questo capitolo
entra nella programmazione, chiamata per chiamata. I frammenti di codice sono quelli
delle slide e del sito; gli output indicati sono quelli attesi secondo le fonti, non
run eseguiti da noi.
:::

:::{tip} Il capitolo in breve
**Il problema.** Su un cluster ogni nodo ha la sua memoria e nessun processo può
leggere le variabili di un altro. Se un dato serve altrove, qualcuno deve
**spedirlo** e qualcun altro **riceverlo**.

**La soluzione.** MPI è uno *standard* che definisce le funzioni per farlo: inviare e
ricevere fra due processi (*point-to-point*), muovere dati fra tutti i processi di un
gruppo (*collettive*), descrivere dati sparsi in memoria (*tipi derivati*). Lo stesso
codice funziona su un portatile e su migliaia di nodi.

**Il prezzo.** Ogni messaggio costa tempo (latenza + byte / banda) e il programmatore
deve decidere chi possiede ogni dato, accoppiare correttamente invii e ricezioni ed
evitare che i processi si aspettino a vicenda per sempre (*deadlock*).
:::

(t7-cluster)=
## Sistemi a memoria distribuita e cluster

**Memoria condivisa e distribuita.** Con la memoria condivisa (OpenMP) i thread
vedono un unico spazio di indirizzi. Con la memoria distribuita ogni processo ha il
suo spazio di indirizzi e accede direttamente solo alla propria memoria: un valore
prodotto da un processo arriva a un altro solo con una comunicazione esplicita (o con
un servizio esterno, per esempio un file condiviso). Il vantaggio è che la macchina
può crescere oltre i socket e la memoria di un nodo; il costo è che la rete è più
lenta della memoria locale e che il programma deve stabilire chi possiede ogni dato.

Un cluster HPC ha quattro elementi:

| Elemento | Cos'è | Da ricordare |
|---|---|---|
| **Nodo di calcolo** | server indipendente con il suo Linux, CPU multi-core, molta RAM, eventuali GPU e disco locale (*scratch*) | nessuna istruzione di load/store raggiunge la RAM di un altro nodo; esegue i job assegnati dallo scheduler |
| **Rete** (*interconnect*) | collega i nodi per il calcolo parallelo | conta latenza, banda, topologia (fat-tree, dragonfly, toro) e scalabilità; tecnologie tipiche InfiniBand, Slingshot, Ethernet 100–400G |
| **Nodi di login e di servizio** | ingresso via SSH, compilatori, moduli, invio dei job; servizi di autenticazione, monitoraggio, scheduling | **non** si usano per calcoli pesanti: sono condivisi fra tutti gli utenti |
| **Filesystem** | memoria di massa condivisa, visibile da tutti i nodi | filesystem paralleli (Lustre, GPFS/Storage Scale) dividono i file su più server; il disco locale serve per file temporanei o checkpoint, e i suoi dati non sono visibili dagli altri nodi |

Due processi sullo stesso nodo hanno comunque spazi di indirizzi separati. MPI usa
meccanismi a memoria condivisa dentro il nodo e la rete fra nodi, ma l'applicazione
chiama le **stesse funzioni** in entrambi i casi: è l'implementazione a scegliere il
canale di trasporto. Un esempio dai nostri log: ogni processo di HPL su WILSON stampa
`unable to open mca_btl_ofi ... (ignored)`, cioè Open MPI ha provato un canale (il
modulo `btl_ofi`), non ha trovato una libreria che gli serve e ne ha usato un altro,
senza che il programma se ne accorgesse.

(t7-decomposizione)=
### Possesso dei dati e decomposizione a blocchi

Prima di scrivere una chiamata MPI bisogna dividere il problema e assegnare ogni
pezzo a un processo. Il **proprietario** (*owner*) conserva e aggiorna il valore
ufficiale di un elemento; gli altri processi possono averne copie, che diventano
vecchie finché una comunicazione non le aggiorna. Servono due indici: l'indice
**locale** (posizione nell'array del processo) e l'indice **globale** (posizione nel
problema completo).

Per dividere $N$ elementi fra $P$ processi si scrive $N = qP + r$ con $0 \le r < P$:

- i primi $r$ processi ricevono $q + 1$ elementi, gli altri $q$;
- il processo $p$ inizia all'indice globale $pq + \min(p, r)$;
- indice globale = inizio del processo + indice locale.

Esempio del sito: $N = 10$, $P = 3$ dà $q = 3$, $r = 1$, quindi intervalli
$[0, 4)$, $[4, 7)$, $[7, 10)$ e array locali di 4, 3 e 3 elementi. Tenere esplicita
questa regola evita di perdere elementi quando $N$ non è divisibile per $P$. La
divisione decide anche le comunicazioni: una somma globale richiede una
**riduzione**, l'aggiornamento di una griglia richiede le copie dei **bordi** dei
vicini.

**Message passing: pro e contro** (slide 8). Vantaggi: scalabilità e controllo
esplicito, perché possesso e movimento dei dati sono scritti nel codice. Svantaggi:
complessità di comunicazione e sincronizzazione, perché bisogna accoppiare invii e
ricezioni, tenere validi i buffer e ordinare le operazioni in modo che tutti i
processi possano proseguire.

(t7-standard)=
## Lo standard MPI e le implementazioni

**Standard e librerie.** MPI (*Message Passing Interface*) non è un programma ma uno
**standard** dell'[MPI Forum](https://www.mpi-forum.org/) che definisce le funzioni
per la comunicazione fra processi: MPI-1 (1994), MPI-2 (1997), MPI-3 (2012), fino a
MPI 5.0 (giugno 2025). Lo standard definisce le interfacce per **C** e **Fortran**;
il C++ usa l'interfaccia C. Le **implementazioni** sono librerie che rispettano lo
standard: MPICH, Open MPI, Intel MPI e altre. Per Python esiste `mpi4py`, che si
appoggia a un'implementazione MPI installata.

In pratica:

1. si scrive il codice usando **solo** le funzioni dello standard
   (`#include <mpi.h>`, prefisso `MPI_`), così resta portabile;
2. si compila con il **wrapper** dell'implementazione scelta (`mpicc`), che aggiunge
   gli header e le librerie giusti;
3. si esegue con il **launcher** (`srun` su un cluster Slurm, `mpirun` altrove), che
   crea i processi;
4. compilazione ed esecuzione devono usare lo **stesso** ambiente (compilatore e
   MPI): su WILSON gli stessi moduli.

**Il modello di esecuzione.**

- Un'applicazione MPI è fatta di più processi del sistema operativo, ciascuno con il
  suo spazio di indirizzi (e, volendo, con i suoi thread).
- Un **communicator** definisce un gruppo di processi e un contesto di comunicazione
  separato. `MPI_COMM_WORLD` contiene tutti i processi lanciati insieme.
- Ogni processo ha un **rank** nel communicator, un intero da 0 a `size - 1`. Il rank
  identifica un partecipante alla comunicazione, non un core o un nodo fisso.
- Modello **SPMD** (*Single Program, Multiple Data*): tutti eseguono lo stesso
  programma su dati diversi, e il comportamento può dipendere dal rank (per esempio
  il rank 0 legge la configurazione, tutti calcolano un pezzo, una collettiva
  combina i risultati).
- Le variabili ordinarie sono **private** di ogni processo; la comunicazione è
  sempre esplicita.
- Il numero di processi si sceglie al lancio, è indipendente dal numero di thread
  OpenMP e deve stare nelle risorse concesse dallo scheduler.

(t7-hello)=
## Il primo programma: Hello MPI

Il launcher avvia i processi; ognuno inizializza MPI, chiede il suo rank e il numero
di processi, fa il suo lavoro e chiude MPI (slide 11).

```c
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);

    int world_rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    int world_size;
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    printf("Hello from rank %d of %d\n", world_rank, world_size);

    MPI_Finalize();
    return 0;
}
```

| Riga | Cosa fa |
|---|---|
| `#include <mpi.h>` | dichiarazioni di tutte le funzioni, costanti e tipi MPI |
| `MPI_Init(&argc, &argv)` | ogni processo prepara il suo ambiente MPI. **Non** crea i processi: li ha già creati il launcher |
| `MPI_Comm_rank(MPI_COMM_WORLD, &world_rank)` | scrive in `world_rank` il rank di *questo* processo |
| `MPI_Comm_size(MPI_COMM_WORLD, &world_size)` | scrive il numero totale di processi, uguale per tutti |
| `printf(...)` | ogni processo stampa la sua riga; `world_rank` e `world_size` sono copie private di ogni processo |
| `MPI_Finalize()` | chiude MPI; va chiamata da tutti i processi alla fine |

Con 4 processi si ottengono 4 righe, da `Hello from rank 0 of 4` a
`Hello from rank 3 of 4`, in un **ordine che cambia** da un run all'altro, perché i
processi girano indipendenti.

### Compilare ed eseguire su WILSON

```bash
module load GCC/13.2.0 OpenMPI/4.1.6     # stesso ambiente per compilare ed eseguire
mpicc -O2 hello_mpi.c -o hello_mpi       # slide; il sito usa -Wall -Wextra
srun --ntasks=4 --cpus-per-task=1 ./hello_mpi
```

- `mpicc` è un **wrapper**: chiama il compilatore C con i percorsi di header e
  librerie MPI. Con Open MPI, `mpicc --showme` stampa il comando completo, utile se
  la compilazione fallisce.
- Per le misure di prestazione si compila con `-O2` o `-O3` e si annotano compilatore
  e opzioni.
- `module spider OpenMPI/4.1.6` mostra quale modulo del compilatore rende visibile
  quella build di Open MPI: con un compilatore diverso si vede una build diversa.
- Con `srun` ogni **task** Slurm è un processo MPI; l'allocazione deve prevedere
  almeno 4 task. Se il job chiede già `--ntasks=4`, basta `srun ./hello_mpi`.
- Fuori da Slurm si usa `mpirun -np 4 ./hello_mpi`. **Non** va usato sul nodo di
  login per aggirare Slurm: il launcher crea processi, non dà accesso a risorse non
  assegnate.

### Inizializzazione, errori e chiusura

- Le comunicazioni avvengono fra `MPI_Init` e `MPI_Finalize`.
- Le funzioni MPI restituiscono un codice di errore; di default un errore grave di
  comunicazione interrompe tutto il job.
- Prima di `MPI_Finalize` vanno completate tutte le comunicazioni in sospeso:
  `MPI_Finalize` non completa le operazioni non bloccanti.
- `MPI_Finalize` è collettiva: tutti i processi devono arrivarci. Un `exit()` o un
  `return` anticipato su un solo rank, mentre gli altri comunicano ancora, può
  bloccare il job.
- `MPI_Abort(MPI_COMM_WORLD, codice)` chiede di terminare tutti i processi del
  communicator (in pratica, spesso tutto il job).
- Se più thread usano MPI si inizializza con `MPI_Init_thread` ({ref}`t7-ibrido`).

(t7-p2p)=
## Comunicazione point-to-point

**Idea.** Un messaggio va da **un** processo a **un altro**: uno chiama una *send*
indicando la destinazione, l'altro una *receive* indicando la sorgente. MPI accoppia
le due chiamate guardando la "busta" del messaggio: communicator, rank e un intero
chiamato **tag**.

```c
int MPI_Send(const void *buf, int count, MPI_Datatype type,
             int dest, int tag, MPI_Comm comm);

int MPI_Recv(void *buf, int count, MPI_Datatype type, int source,
             int tag, MPI_Comm comm, MPI_Status *status);
```

| Argomento | Significato |
|---|---|
| `buf` | **indirizzo** di inizio dei dati: `&data` per uno scalare, `values` per un array |
| `count` | numero di **elementi** del tipo indicato, non di byte |
| `type` | tipo MPI degli elementi: `MPI_INT`, `MPI_FLOAT`, `MPI_DOUBLE`, ... |
| `dest` / `source` | rank del destinatario / del mittente, nel communicator `comm` |
| `tag` | etichetta intera del messaggio |
| `comm` | communicator, di solito `MPI_COMM_WORLD` |
| `status` | dove la receive scrive mittente, tag e quantità ricevuta; `MPI_STATUS_IGNORE` se non serve |

La terna `buf`, `count`, `type` descrive la memoria del messaggio: `count = 4` con
`MPI_DOUBLE` sono quattro `double`. Chi riceve deve avere spazio sufficiente e un tipo
compatibile.

### Esempio: il rank 0 manda un intero al rank 1

```c
if (world_rank == 0) {
    int data = 100;
    MPI_Send(&data, 1, MPI_INT, 1, 0, MPI_COMM_WORLD);
} else if (world_rank == 1) {
    int received;
    MPI_Recv(&received, 1, MPI_INT, 0, 0,
             MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    printf("Rank 1 received %d from rank 0\n", received);
}
```

Il frammento va nel programma Hello al posto del `printf`, dopo le chiamate a
`MPI_Comm_rank` e `MPI_Comm_size`.

- Il rank 0 invia 1 `MPI_INT` al rank 1 con tag 0; il rank 1 riceve 1 `MPI_INT` dal
  rank 0 con tag 0. Gli altri rank saltano entrambi i rami.
- Output atteso, con almeno 2 processi: `Rank 1 received 100 from rank 0`.
- Con **un solo** processo il programma è sbagliato: il rank 1 non esiste.
- `MPI_Send` torna quando il buffer **si può riusare**; la receive non è
  necessariamente finita (MPI può aver copiato il messaggio in un buffer interno).
- `MPI_Recv` torna quando i dati ricevuti sono disponibili nel buffer.

### Accoppiamento dei messaggi e tag

Una receive accetta un messaggio se coincidono tre campi della busta:

1. **communicator**;
2. **sorgente**: il rank del mittente, oppure `MPI_ANY_SOURCE`;
3. **tag**: lo stesso tag, oppure `MPI_ANY_TAG`.

Tipo e `count` **non** servono a scegliere il messaggio: descrivono soltanto il
trasferimento. I tag permettono di distinguere messaggi diversi dallo stesso
mittente (per esempio un tag per i bordi della griglia e uno per i messaggi di
controllo). I caratteri jolly servono quando il lavoro può arrivare da chiunque, ma
rendono l'ordine meno prevedibile: per sapere cosa è arrivato si legge lo `status`.

```c
MPI_Status status;
MPI_Recv(buffer, capacity, MPI_DOUBLE, MPI_ANY_SOURCE, MPI_ANY_TAG,
         MPI_COMM_WORLD, &status);

int received_count;
MPI_Get_count(&status, MPI_DOUBLE, &received_count);
```

`status.MPI_SOURCE` e `status.MPI_TAG` dicono quale messaggio è stato accettato,
`MPI_Get_count` quanti `double` sono arrivati. Il buffer può essere più grande del
messaggio; un messaggio più grande del buffer invece viene troncato e dà errore.

**Ordine.** Se il rank 0 manda due messaggi al rank 1 che corrispondono alla stessa
receive, arriva prima il primo (*non-overtaking*). La regola vale per invii fatti in
sequenza da un thread; non esiste invece un ordine globale fra mittenti diversi, e
con `MPI_ANY_SOURCE` l'ordine dipende dai tempi.

(t7-deadlock)=
### Deadlock con le chiamate bloccanti

Due rank si scambiano `n` double, ognuno con il suo `sendbuf` e `recvbuf`:

```c
int peer = 1 - world_rank;      /* esattamente due rank: 0 <-> 1 */
MPI_Send(sendbuf, n, MPI_DOUBLE, peer, 0, MPI_COMM_WORLD);
MPI_Recv(recvbuf, n, MPI_DOUBLE, peer, 0,
         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
```

Entrambi i rank iniziano con una send. Se ogni send aspetta che l'altro abbia
preparato la receive, nessuno dei due arriva mai alla sua `MPI_Recv`: è un'attesa
circolare, cioè un **deadlock**. Con messaggi piccoli MPI può copiare il messaggio in
un buffer interno e il codice sembra funzionare; con messaggi più grandi, con
un'altra implementazione o con meno spazio di buffer si blocca. **Un test riuscito
con messaggi piccoli non dimostra che l'ordine sia sicuro.**

Soluzioni:

- `MPI_Sendrecv`, che esegue invio e ricezione in un'unica chiamata e lascia a MPI
  l'ordine, senza attesa circolare:

  ```c
  int peer = 1 - world_rank;      /* esattamente due rank */
  MPI_Sendrecv(sendbuf, n, MPI_DOUBLE, peer, 0,
               recvbuf, n, MPI_DOUBLE, peer, 0,
               MPI_COMM_WORLD, MPI_STATUS_IGNORE);
  ```

  I buffer di invio e ricezione sono separati; al ritorno i dati ricevuti sono
  disponibili e il buffer di invio è riutilizzabile. È comoda per gli scambi fra
  vicini (*shift*, halo).
- un ordine che dipende dal rank (per esempio i pari prima inviano e poi ricevono, i
  dispari il contrario);
- le chiamate non bloccanti ({ref}`t7-nonblocking`);
- una collettiva adatta.

**`MPI_PROC_NULL`.** Usato come sorgente o destinazione indica un vicino che non
esiste: la comunicazione si completa subito senza trasferire nulla. Serve ai bordi di
un dominio non periodico, dove tutti i processi possono eseguire lo stesso codice di
scambio. Una receive da `MPI_PROC_NULL` lascia il buffer invariato, quindi i valori
al bordo fisico vanno impostati dal programma.

(t7-nonblocking)=
## Comunicazione non bloccante

**Idea.** Separare l'**avvio** di una comunicazione dal suo **completamento**:
`MPI_Isend` e `MPI_Irecv` avviano l'operazione e restituiscono subito una *richiesta*
(`MPI_Request`); il completamento si chiede dopo. Nel frattempo possono essere attive
più comunicazioni e il programma può fare altro. "Non bloccante" non significa "fatto
in background": l'operazione va comunque completata.

| Chiamata | Cosa fa |
|---|---|
| `MPI_Isend(buf, count, type, dest, tag, comm, &req)` | avvia un invio |
| `MPI_Irecv(buf, count, type, source, tag, comm, &req)` | avvia una ricezione |
| `MPI_Wait(&req, &status)` | aspetta che la richiesta sia completata |
| `MPI_Test(&req, &flag, &status)` | controlla senza aspettare: `flag` vale vero se è completata |
| `MPI_Waitall(n, reqs, statuses)` | aspetta un array di richieste (anche `MPI_Waitany`, `MPI_Waitsome`) |

**Regole sui buffer**, finché la richiesta non è completata:

| Buffer | Leggere | Modificare | Liberare |
|---|---|---|---|
| di invio (`MPI_Isend`) | sì | **no** | **no** |
| di ricezione (`MPI_Irecv`) | **no** | **no** | **no** |

Il completamento è locale: un invio completato significa che il buffer si può
riusare, non che il destinatario abbia ricevuto. Dopo `MPI_Wait` (o `MPI_Test` con
esito vero) la richiesta diventa `MPI_REQUEST_NULL`. Perdere o sovrascrivere la
variabile della richiesta non completa l'operazione: si perde solo il modo di
aspettarla. Chiamare `MPI_Test` in un ciclo stretto è comunque un'attesa; serve quando
fra un controllo e l'altro c'è altro lavoro.

### Esempio: invio non bloccante

```c
MPI_Request req;
MPI_Isend(data, n, MPI_DOUBLE, 1, 0, MPI_COMM_WORLD, &req);
/* Lavoro indipendente: si può leggere data, non modificarlo né liberarlo. */
MPI_Wait(&req, MPI_STATUS_IGNORE);
```

Sul rank che invia `data` (`n` double) al rank 1, che deve avere una receive
corrispondente. Il calcolo fra `MPI_Isend` e `MPI_Wait` può sovrapporsi alla
comunicazione, ma la sovrapposizione e il guadagno dipendono dall'implementazione MPI
e dal sistema. `MPI_Wait` libera il buffer per il riuso.

### Esempio: scambio sicuro fra due rank

```c
MPI_Request requests[2];
int neighbour = 1 - world_rank;

MPI_Irecv(recvbuf, n, MPI_DOUBLE, neighbour, 0, MPI_COMM_WORLD, &requests[0]);
MPI_Isend(sendbuf, n, MPI_DOUBLE, neighbour, 0, MPI_COMM_WORLD, &requests[1]);

MPI_Waitall(2, requests, MPI_STATUSES_IGNORE);
```

Entrambi i rank prima avviano la ricezione, poi l'invio, poi aspettano tutte e due:
non c'è più l'attesa circolare del caso bloccante. Avviare prima le ricezioni dice
subito a MPI dove mettere i dati in arrivo, e lo schema si estende a più vicini.
Attenzione: aspettare l'invio (`MPI_Wait`) **prima** di avviare la ricezione
corrispondente ricrea la dipendenza bloccante.

### Sovrapporre comunicazione e calcolo

```c
post_halo_exchange(requests);   /* Irecv e Isend dei bordi        */
compute_interior();             /* non usa i bordi in arrivo      */
MPI_Waitall(number_of_requests, requests, MPI_STATUSES_IGNORE);
compute_boundary();             /* usa i bordi appena ricevuti    */
```

Le tre funzioni sono dell'applicazione. Mentre i bordi viaggiano si calcola
l'interno, che non dipende da loro; `compute_interior` non deve modificare i valori
in invio né leggere quelli in arrivo. Dopo `MPI_Waitall` si calcola il bordo.

(t7-confronto)=
### Bloccante e non bloccante a confronto

```{figure} figures/mpi-bloccante-non-bloccante.png
:name: fig-mpi-bloccante
:width: 100%

Lo stesso scambio fra due rank. A sinistra, con `MPI_Send` seguita da `MPI_Recv`,
ogni send aspetta una receive che l'altro rank non raggiungerà mai. A destra le
ricezioni e gli invii vengono solo avviati, il calcolo indipendente prosegue e
`MPI_Waitall` aspetta la fine di entrambi. Schema dell'ordine delle operazioni, non
una misura di tempi.
```

| | Bloccante (`MPI_Send`, `MPI_Recv`) | Non bloccante (`MPI_Isend`, `MPI_Irecv` + `MPI_Wait`) |
|---|---|---|
| Quando torna la chiamata | send: quando il buffer si può riusare; recv: quando i dati sono arrivati | subito, con una `MPI_Request` |
| Buffer dopo la chiamata | subito riutilizzabile (send) o pieno (recv) | intoccabile fino a `MPI_Wait` / `MPI_Test` (vedi la tabella sopra) |
| Rischio di deadlock | sì, se l'ordine delle chiamate crea un'attesa circolare | no per lo scambio in sé, se si avviano tutte le operazioni prima di aspettare |
| Più comunicazioni insieme | una alla volta | quante se ne vogliono, poi `MPI_Waitall` |
| Sovrapposizione con il calcolo | no | possibile, ma non garantita: dipende da implementazione e rete |
| Complessità | bassa | più alta: richieste da gestire e regole sui buffer |
| Quando usarla | scambi semplici con ordine sicuro, o `MPI_Sendrecv` | scambi con più vicini, halo, sovrapposizione calcolo/comunicazione |

**Quanto è "grande" un messaggio grande?** Dipende dall'implementazione. Nel
notebook {ref}`programmiamo-con-mpi` lo misuriamo: con Open MPI 5.0.11 sul Mac lo
scambio bloccante fra due processi funziona fino a 502 `double` (4016 byte) e si
blocca da 503 in su, perché sotto il limite *eager* di 4096 byte (intestazione
compresa) Open MPI copia il messaggio e lascia tornare la send. Alzando il limite con
`--mca btl_sm_eager_limit 16384` funziona anche con 1000 `double`. Su WILSON, o fra
nodi, la soglia può essere diversa: per questo l'ordine sicuro va garantito dal
codice, non dal test.

**Non bloccante non vuol dire più veloce.** Aggiunge gestione delle richieste e
dipendenze più complesse. Serve quando permette comunicazioni simultanee sicure,
sovrappone comunicazione e lavoro indipendente o espone uno schema che la libreria sa
ottimizzare. Va misurato sull'applicazione completa.

(t7-collettive)=
## Comunicazione collettiva

**Idea.** Un'operazione collettiva coinvolge **tutti** i processi di un communicator:
si dichiara *cosa* deve succedere (distribuire, raccogliere, sommare) e MPI sceglie
*come*, con algoritmi ad albero adatti alla dimensione dei messaggi, al numero di
processi e alla topologia della rete. Non si gestiscono coppie send/recv.

| Operazione | Scopo |
|---|---|
| `MPI_Bcast` | copia un dato dal processo radice (*root*) a tutti |
| `MPI_Scatter` | divide un array della radice in pezzi uguali, uno per processo |
| `MPI_Gather` | raccoglie un pezzo da ogni processo nella radice, in ordine di rank |
| `MPI_Allgather` | come gather, ma il risultato arriva a tutti |
| `MPI_Reduce` | combina i valori (somma, massimo, ...) e dà il risultato alla radice |
| `MPI_Allreduce` | come reduce, ma il risultato arriva a tutti |
| `MPI_Alltoall` | ogni processo scambia un pezzo con ogni altro |
| `MPI_Barrier` | aspetta che tutti i processi siano arrivati |

```{figure} figures/mpi-collettive.png
:name: fig-mpi-collettive
:width: 100%

Cosa contengono i buffer di 4 rank prima e dopo le collettive principali, con radice
0 e gli esempi di questa sezione. Le frecce indicano il cambio di stato, non i
messaggi che MPI scambia internamente. Gather **conserva** tutti i contributi,
reduce li **combina** in un solo valore.
```

**Regole.**

- Tutti i processi del communicator chiamano la collettiva, radice compresa, con la
  **stessa radice**, e le collettive vanno chiamate da tutti **nello stesso ordine**.
  Se un rank salta una collettiva o ne chiama un'altra, il programma è sbagliato e di
  solito si blocca.
- L'inizializzazione o l'uso del risultato possono stare in un ramo `if` che dipende
  dal rank; la chiamata collettiva no.
- Una collettiva **non è una barriera**: quando torna, il chiamante può usare i suoi
  buffer, ma non è detto che gli altri abbiano finito o siano entrati. Per
  sincronizzare si usa `MPI_Barrier`; mettere barriere attorno a ogni collettiva
  aggiunge costo senza aggiungere correttezza.

### Broadcast

```c
int value;
if (world_rank == 0) value = 42;
MPI_Bcast(&value, 1, MPI_INT, 0, MPI_COMM_WORLD);
printf("Rank %d has value %d\n", world_rank, value);
```

Prima della chiamata `value` vale 42 solo sul rank 0; dopo, tutti i rank hanno 42.
Tutti chiamano `MPI_Bcast`, anche la radice 0. È preferibile a un ciclo di send dalla
radice, che farebbe i trasferimenti uno dopo l'altro, mentre MPI può usare un albero.

### Scatter e gather

```c
/* Esattamente quattro rank. */
int sendbuf[4] = {10, 20, 30, 40};
int recvbuf;
MPI_Scatter(sendbuf, 1, MPI_INT, &recvbuf, 1, MPI_INT,
            0, MPI_COMM_WORLD);
printf("Rank %d got %d\n", world_rank, recvbuf);
```

Il rank $r$ riceve `sendbuf[r]`: 10, 20, 30, 40 ai rank 0–3. Il `count` è il numero
di elementi **per rank** (1), non la lunghezza dell'array. `sendbuf` conta solo sulla
radice: esiste anche sugli altri rank solo perché tutti eseguono le stesse
dichiarazioni.

Il gather fa il contrario:

```c
int gathered[4];
MPI_Gather(&recvbuf, 1, MPI_INT, gathered, 1, MPI_INT, 0, MPI_COMM_WORLD);
if (world_rank == 0)
    for (int i = 0; i < 4; ++i)
        printf("%d%c", gathered[i], i == 3 ? '\n' : ' ');
```

Il rank 0 stampa `10 20 30 40`. Il `count` di ricezione (1) è il contributo di ogni
rank, quindi la radice deve avere spazio per 4 interi. Solo la radice ha l'array
completo; con `MPI_Allgather` lo avrebbero tutti.

**Pezzi di dimensione diversa.** `MPI_Scatterv`, `MPI_Gatherv` e `MPI_Allgatherv`
prendono un array di conteggi e uno di spostamenti. È il caso della decomposizione a
blocchi con $N = 10$ e $P = 3$ ({ref}`t7-decomposizione`):

```c
/* Esattamente tre rank. */
int global_data[10];
int counts[3]        = {4, 3, 3};
int displacements[3] = {0, 4, 7};
int local_count = counts[world_rank];
int local_data[4];

if (world_rank == 0)
    for (int i = 0; i < 10; ++i) global_data[i] = i;

MPI_Scatterv(global_data, counts, displacements, MPI_INT,
             local_data, local_count, MPI_INT, 0, MPI_COMM_WORLD);
```

Il rank 0 riceve 0–3, il rank 1 4–6, il rank 2 7–9. Gli spostamenti sono in elementi,
non in byte; solo `counts`, `displacements` e `global_data` della radice contano. Con
un numero di processi qualsiasi gli array si calcolano da $N$ e $P$ con la regola
di {ref}`t7-decomposizione`, invece di scriverli a mano.

### Riduzioni

```c
double local_sum = world_rank + 1.0, global_sum;
MPI_Reduce(&local_sum, &global_sum, 1, MPI_DOUBLE,
           MPI_SUM, 0, MPI_COMM_WORLD);
```

Ogni rank contribuisce con `rank + 1`; con 4 rank la somma è $1 + 2 + 3 + 4 = 10$, ma
`global_sum` è valida **solo sulla radice** 0. Se il risultato serve a tutti:

```c
MPI_Allreduce(&local_sum, &global_sum, 1, MPI_DOUBLE,
              MPI_SUM, MPI_COMM_WORLD);
```

Altre operazioni: `MPI_PROD`, `MPI_MIN`, `MPI_MAX`, ... Con un `count` maggiore di 1
una sola chiamata riduce più quantità indipendenti: con `local_sums[3]` l'elemento
$k$ del risultato è la somma degli elementi $k$ di tutti i rank (un gather invece
conserverebbe tutti i $3P$ valori).

**Attenzione ai floating point.** La riduzione può sommare in un ordine diverso da
quello sequenziale, e la somma in virgola mobile non è associativa: il risultato può
cambiare leggermente con il numero di processi, l'algoritmo o l'implementazione. È lo
stesso fenomeno dell'[Esercizio 1](../esercizi/es01-basilea.md), dove l'ordine della
somma cambia il risultato in `float32`.

**Riduzioni non bloccanti.** Molte collettive hanno una forma non bloccante
(`MPI_Ibcast`, `MPI_Iallreduce`, ...) che restituisce una `MPI_Request`:

```c
MPI_Request request;
MPI_Iallreduce(&local_sum, &global_sum, 1, MPI_DOUBLE,
               MPI_SUM, MPI_COMM_WORLD, &request);
/* Lavoro indipendente: non modificare local_sum, non leggere global_sum. */
MPI_Wait(&request, MPI_STATUS_IGNORE);
```

### Scegliere la collettiva giusta

Le collettive descrivono lo schema di comunicazione e permettono alla libreria di
ottimizzarlo: meglio `MPI_Allreduce` che una reduce seguita da un broadcast, meglio
scatter e gather che cicli di send. Nessuna è gratis: `MPI_Alltoall` muove dati fra
ogni coppia di rank, e **riduzioni globali frequenti** limitano lo scaling per la
latenza e perché sincronizzano i processi veloci con quelli lenti. È quello che si
vede in HPCG nell'[Esercizio 5](../esercizi/es05-hpl-hpcg.md): nello strong scaling a
8 nodi le `MPI_Allreduce` dei prodotti scalari (`DDOT`) prendono il 77% del tempo.

(t7-communicator)=
## Communicator e topologie di processi

**Idea.** Un communicator è un **gruppo** di processi più un **contesto**: i rank
sono numerati dentro il gruppo, e i messaggi di un communicator non possono essere
accettati da receive di un altro. Un processo non ha un rank universale, ma un rank
per ogni communicator a cui appartiene; i rank di una send o di una receive si
leggono nel communicator passato a quella chiamata. `MPI_Comm_dup` crea un contesto
nuovo con gli stessi processi e rank, utile per isolare i messaggi di una libreria da
quelli dell'applicazione.

### Sottogruppi con `MPI_Comm_split`

```c
int MPI_Comm_split(MPI_Comm comm, int colour, int key, MPI_Comm *newcomm);
```

I processi con lo stesso `colour` finiscono nello stesso nuovo communicator;
all'interno i rank sono ordinati per `key` crescente (a parità, nell'ordine
originale). Esempio delle slide, con 4 rank divisi in pari e dispari:

```c
int colour = world_rank % 2, group_rank;
MPI_Comm group;
MPI_Comm_split(MPI_COMM_WORLD, colour, world_rank, &group);
MPI_Comm_rank(group, &group_rank);
/* Comunicazione dentro il gruppo. */
MPI_Comm_free(&group);
```

| Rank in `MPI_COMM_WORLD` | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `colour` | 0 | 1 | 0 | 1 |
| Rank nel gruppo | 0 | 0 | 1 | 1 |

- **Tutti** i processi del communicator originale chiamano `MPI_Comm_split`.
- Un processo con `colour = MPI_UNDEFINED` resta fuori e riceve `MPI_COMM_NULL`, su
  cui non deve fare nulla.
- Le collettive sul nuovo communicator coinvolgono solo i suoi membri: gruppi
  diversi (righe e colonne di una griglia, compiti diversi) lavorano senza
  interferire.
- Rank consecutivi non stanno per forza sullo stesso nodo: per raggruppare i
  processi che condividono memoria si usa `MPI_Comm_split_type` con
  `MPI_COMM_TYPE_SHARED`.
- Ogni communicator creato si libera con `MPI_Comm_free` dopo l'ultimo uso.

### Topologie cartesiane

Molti codici scientifici dividono un dominio regolare in 1D, 2D o 3D. Una topologia
cartesiana indirizza i processi con **coordinate logiche** invece che con aritmetica
sui rank:

```c
int dimensions[2] = {0, 0};                 /* 0 = sceglie MPI           */
MPI_Dims_create(world_size, 2, dimensions); /* 6 processi -> {3, 2}      */

int periods[2] = {0, 0};                    /* nessuna dimensione periodica */
int reorder = 1;                            /* MPI può rinumerare i rank   */
MPI_Comm cart;
MPI_Cart_create(MPI_COMM_WORLD, 2, dimensions, periods, reorder, &cart);

int cart_rank, coords[2];
MPI_Comm_rank(cart, &cart_rank);
MPI_Cart_coords(cart, cart_rank, 2, coords);

int left, right;
MPI_Cart_shift(cart, 1, 1, &left, &right);  /* vicini lungo la dimensione 1 */
```

- `MPI_Dims_create` bilancia i processi fra le direzioni (6 → 3 righe × 2 colonne,
  coordinate da (0, 0) a (2, 1)), senza conoscere la forma del dominio. Una voce
  positiva fissa quella dimensione.
- `MPI_Cart_create`: il prodotto delle dimensioni deve essere uguale al numero di
  processi; `periods[i] = 1` collega i due estremi della dimensione $i$. Con
  `reorder = 1` il rank cartesiano può essere diverso dal rank in `MPI_COMM_WORLD`.
- `MPI_Cart_shift(cart, dimensione, spostamento, &sorgente, &destinazione)` **trova**
  i vicini, non scambia dati. Al bordo di una dimensione non periodica il vicino
  mancante è `MPI_PROC_NULL`, quindi bordo e interno eseguono lo stesso codice.
- La topologia registra solo le relazioni logiche: non divide gli array e non sposta
  i processi fra i nodi.

(t7-datatype)=
## Tipi derivati e scambio degli halo

**Idea.** Ogni messaggio descrive i dati con `count` e un tipo. I tipi predefiniti
(`MPI_INT`, `MPI_FLOAT`, `MPI_DOUBLE`, ...) sono valori contigui di un tipo C. Un
**tipo derivato** descrive dati **non contigui** o strutturati, per esempio una
colonna di una matrice, senza doverli copiare a mano in un buffer.

Ciclo di vita: **costruire**, **`MPI_Type_commit`** prima di usarlo, **`MPI_Type_free`**
alla fine. Il commit prepara la descrizione, non alloca dati; un tipo si può riusare
con buffer diversi, per esempio a ogni iterazione di un ciclo. `MPI_Type_contiguous(3,
MPI_DOUBLE, &t)` raggruppa 3 double consecutivi: 1 elemento di `t` equivale a 3
`MPI_DOUBLE`.

### Inviare una colonna con `MPI_Type_vector`

In C una matrice `double a[4][6]` è memorizzata per righe (*row-major*): gli elementi
di una riga sono consecutivi, quelli di una colonna distano 6 double. Il rank 0 invia
la colonna 2 (slide 28):

```c
MPI_Datatype column;
MPI_Type_vector(4, 1, 6, MPI_DOUBLE, &column);
MPI_Type_commit(&column);
MPI_Send(&a[0][2], 1, column, 1, 0, MPI_COMM_WORLD);
MPI_Type_free(&column);
```

`MPI_Type_vector(count, blocklength, stride, oldtype, &newtype)`: 4 blocchi, ognuno
di 1 double, con l'inizio di un blocco a 6 double dal precedente. A partire da
`&a[0][2]` vengono presi `a[0][2]`, `a[1][2]`, `a[2][2]`, `a[3][2]`.

- Lo `stride` è in unità del tipo di base, **non in byte**.
- Serve un'unica allocazione contigua; un `double **` con righe allocate separatamente
  non ha uno stride costante.
- Il tipo descrive solo la memoria **locale**: il rank 1 può ricevere 4 double
  contigui con `MPI_Recv(col, 4, MPI_DOUBLE, ...)`.
- Per strutture con campi di tipo diverso esiste `MPI_Type_create_struct`; gli
  spostamenti dei campi si ottengono con `MPI_Get_address`, perché il compilatore può
  inserire byte di allineamento.

### Celle fantasma (halo)

Nella decomposizione di un dominio ogni rank possiede un blocco e alloca celle in più
ai bordi, le **celle fantasma** o **halo**, con copie dei valori dei vicini. Ogni
iterazione ha tre fasi:

1. scambiare i bordi con i vicini;
2. calcolare i nuovi valori dalla griglia vecchia e dagli halo aggiornati,
   scrivendoli in una griglia **separata**;
3. scambiare i ruoli delle due griglie e ripetere.

L'halo è un dato **duplicato**, non memoria condivisa: aggiornare un valore di bordo
non aggiorna la copia del vicino finché non si scambia un altro messaggio.

**Scambio in 1D.** Su una linea non periodica (`MPI_Cart_create` con 1 dimensione e
`MPI_Cart_shift` per `left` e `right`), `values[1]`…`values[local_size]` sono le
celle proprie, `values[0]` e `values[local_size + 1]` le celle fantasma:

```c
MPI_Request requests[4];
enum { TAG_TO_LEFT = 0, TAG_TO_RIGHT = 1 };

MPI_Irecv(&values[0],              1, MPI_DOUBLE, left,  TAG_TO_RIGHT, line, &requests[0]);
MPI_Irecv(&values[local_size + 1], 1, MPI_DOUBLE, right, TAG_TO_LEFT,  line, &requests[1]);
MPI_Isend(&values[1],              1, MPI_DOUBLE, left,  TAG_TO_LEFT,  line, &requests[2]);
MPI_Isend(&values[local_size],     1, MPI_DOUBLE, right, TAG_TO_RIGHT, line, &requests[3]);

MPI_Waitall(4, requests, MPI_STATUSES_IGNORE);
```

```{figure} figures/mpi-halo-1d.png
:name: fig-mpi-halo
:width: 100%

Scambio degli halo in 1D con 3 rank da 4 celle (`local_size = 4`): `u[1]`…`u[4]`
sono le celle proprie (qui con il loro indice globale), `u[0]` e `u[5]` le celle
fantasma. Ai due estremi il vicino è `MPI_PROC_NULL` e la cella fantasma tiene il
valore della condizione al contorno.
```

Il primo valore proprio va a sinistra, l'ultimo a destra. I tag indicano la
**direzione** del viaggio: l'halo sinistro riceve ciò che il vicino di sinistra ha
mandato verso destra. Ai bordi `left` o `right` vale `MPI_PROC_NULL`, quell'operazione
non trasferisce nulla e l'halo resta com'era: il valore va fissato dalla condizione
al contorno fisica.

**Scambio in 2D** (slide 29). Con `local_rows × local_columns` celle proprie e un
halo di una cella su ogni lato si allocano
`(local_rows + 2) × (local_columns + 2)` double, e l'elemento (riga, colonna) è
`grid[row * stride + column]` con `stride = local_columns + 2`. Righe superiore e
inferiore sono contigue; la colonna di bordo è strided:

```c
int stride = local_columns + 2;
MPI_Datatype column_type;
MPI_Type_vector(local_rows, 1, stride, MPI_DOUBLE, &column_type);
MPI_Type_commit(&column_type);
```

Nella figura della slide 29 il blocco proprio è 4 × 4, quindi `stride` = 6: la
colonna propria di destra è formata dagli elementi 10, 16, 22, 28 della griglia
locale, cioè `MPI_Type_vector(4, 1, 6, ...)`. Ogni freccia della figura porta 4
valori; gli angoli non vengono scambiati. Basta per uno stencil a 5 punti (centro e
4 vicini); uno stencil a 9 punti usa anche i vicini in diagonale, quindi servono gli
angoli: si inviano ai rank diagonali, oppure si fanno due fasi (prima le colonne, poi
le righe comprese le colonne di halo appena aggiornate). Tutti i valori scambiati
devono appartenere allo stesso passo temporale.

Un tipo derivato cambia la **descrizione** dei dati, non la quantità che passa in
rete: l'implementazione può comunque copiarli in un buffer temporaneo, e l'accesso
strided può essere più lento di quello contiguo. Sulle parti critiche conviene
confrontarlo con un impacchettamento esplicito, su messaggi di dimensione realistica.

(t7-prestazioni)=
## Prestazioni di un programma MPI

### Il costo di un messaggio

$$T_\text{messaggio} \simeq \alpha + \frac{n}{B}$$

con $\alpha$ la **latenza** (s), $n$ la dimensione del messaggio (byte) e $B$ la
**banda** effettiva (byte/s; una banda in GB/s va convertita in byte/s). I due
termini si equivalgono per $n = \alpha B$: messaggi molto più piccoli sono dominati
dalla latenza, molto più grandi dalla banda. Conseguenze:

- molti messaggi piccoli pagano molte volte la latenza: conviene raggrupparli,
  senza esagerare (si ritarda il lavoro utile e servono buffer temporanei);
- la comunicazione dentro un nodo costa di solito meno di quella in rete, quindi
  conta dove sono messi i rank;
- il modello ignora la contesa sulla rete e i cambi di protocollo con la dimensione
  dei messaggi; $\alpha$ e $B$ vanno misurati sul percorso reale.

### Superficie e volume

In un dominio regolare il calcolo cresce con il **volume** locale e lo scambio degli
halo con la **superficie**. Un dominio quadrato di lato $L$ ha $L^2$ celle e scambia
circa $4L$ valori: il rapporto comunicazione / calcolo va come $4/L$. Nello strong
scaling i sottodomini si rimpiccioliscono, $L$ cala e la comunicazione pesa sempre di
più (slide 30: domini locali più piccoli hanno più dati di bordo rispetto al lavoro
utile). Aggiungendo processi, a un certo punto ognuno ha troppo poco lavoro per
ammortizzare gli scambi: nessuna ottimizzazione della comunicazione compensa una
decomposizione che lascia a ogni processo troppo poco da fare. È ciò che si osserva
nello strong scaling dell'[Esercizio 5](../esercizi/es05-hpl-hpcg.md): HPL a
$N$ = 41280 è più lento a 8 nodi che a 4.

### Misurare il tempo

```c
double start = MPI_Wtime();
run_parallel_work();
double local = MPI_Wtime() - start, elapsed;
MPI_Reduce(&local, &elapsed, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
if (world_rank == 0) printf("Elapsed: %.6f s\n", elapsed);
```

- `MPI_Wtime` dà il tempo reale in secondi. Gli orologi sono **locali** a ogni
  processo e non sincronizzati: si misurano intervalli, non istanti.
- `MPI_MAX` riporta l'intervallo locale più lungo, che non coincide con "dal primo
  inizio all'ultima fine" se i rank entrano nella regione in tempi diversi.
- Una `MPI_Barrier` prima della misura serve solo se si vuole un inizio comune;
  cambia il comportamento e costa, quindi non va messa d'abitudine.
- Si ripetono le misure e si dichiara il metodo.

### Bilanciamento del carico e attese

Un rank con più lavoro fa aspettare gli altri nelle receive, nelle collettive o nelle
fasi successive. Una chiamata di comunicazione lunga può quindi rivelare uno
**squilibrio precedente**, non un trasferimento lento. Per capirlo si misurano
separatamente calcolo e comunicazione per ogni rank e si confrontano minimo, media e
massimo, non solo il tempo del rank 0. È il caso dei tempi di `MPI_Allreduce` di HPCG
nell'[Esercizio 5](../esercizi/es05-hpl-hpcg.md), con minimo e massimo molto diversi
fra i processi.

### Collocazione dei processi

La richiesta Slurm fissa nodi, task per nodo, CPU per task e binding, non solo il
numero totale di rank, e va annotata insieme a eseguibile, input, compilatore,
implementazione MPI e dimensione del problema. Rank che comunicano spesso traggono
vantaggio dallo stare vicini; rank limitati dalla banda di memoria dal distribuirsi
su più socket o nodi. Non esiste una disposizione ottima in generale: si misura (vedi
{ref}`disposizione-e-slurm`).

(t7-ibrido)=
## MPI + OpenMP

**Idea.** MPI fra i processi, OpenMP dentro ogni processo: tipicamente uno o pochi
rank per nodo, con thread che condividono la memoria del loro rank. Il vincolo è che
rank per nodo × thread per rank = CPU richieste a Slurm. Il quadro generale è in
{ref}`ibrido-mpi-openmp`.

```bash
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
srun --cpu-bind=cores ./hybrid_program
```

| Riga | Significato |
|---|---|
| `--nodes=2`, `--ntasks-per-node=2` | 2 rank su ciascuno dei 2 nodi, 4 rank in tutto |
| `--cpus-per-task=4` | 4 core per rank |
| `--hint=nomultithread` | solo core fisici, un hardware thread per core |
| `OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK` | tanti thread quanti core del rank |
| `srun --cpu-bind=cores` | lega ogni rank ai suoi core |

Risultato: 8 core fisici per nodo, 16 in tutto. Si compila con `mpicc -O2 -fopenmp`.
Il sito aggiunge `OMP_DYNAMIC=FALSE` (niente variazione automatica del numero di
thread), `OMP_PLACES=cores` e `OMP_PROC_BIND=close` (thread sui core, vicini fra
loro); partizione, tempo, memoria e moduli vanno aggiunti, e l'affinità reale va
controllata.

L'ibrido può ridurre il numero di messaggi e i dati duplicati, ma aggiunge
sincronizzazione fra thread, effetti NUMA e un livello di collocazione in più. Non è
detto che meno rank vadano più veloci: si confronta con il solo MPI **a parità di
core e nodi** (per esempio 2 rank × 4 thread contro 8 rank × 1 thread per nodo), con
lo stesso problema e la stessa regione misurata. È il confronto fatto su un nodo
nell'[Esercizio 5](../esercizi/es05-hpl-hpcg.md): per HPL vince 2 × 8, per HPCG
16 × 1.

### Supporto ai thread

Se il programma usa thread, `MPI_Init` si sostituisce con `MPI_Init_thread`, che
chiede un livello di supporto e restituisce quello concesso:

```c
int provided;
MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
if (provided < MPI_THREAD_FUNNELED)
    MPI_Abort(MPI_COMM_WORLD, 1);
```

| Livello | Significato |
|---|---|
| `MPI_THREAD_SINGLE` | un solo thread per processo |
| `MPI_THREAD_FUNNELED` | più thread, ma chiama MPI solo il thread che l'ha inizializzato |
| `MPI_THREAD_SERIALIZED` | più thread possono chiamare MPI, mai contemporaneamente |
| `MPI_THREAD_MULTIPLE` | più thread possono chiamare MPI contemporaneamente |

- I livelli sono in ordine crescente: per questo si controlla
  `provided < MPI_THREAD_FUNNELED`, perché l'implementazione può concedere meno del
  richiesto.
- `FUNNELED` basta a molti programmi OpenMP: il thread iniziale chiama MPI fra una
  regione parallela e l'altra, i thread fanno il calcolo locale.
- Una regione `#pragma omp single` può essere eseguita da un thread qualsiasi del
  team: una chiamata MPI lì dentro **non** rispetta `FUNNELED`. (Nota nostra, non
  nelle fonti: la soluzione più semplice è fare la chiamata fuori dalla regione
  parallela; dentro la regione, `#pragma omp master`, `masked` da OpenMP 5.1, la fa
  eseguire al thread principale del team.)
- `MULTIPLE` serve per chiamate MPI concorrenti da più thread, ma può costare in
  sincronizzazione: si chiede solo il livello necessario.

(t7-checklist)=
## Riepilogo

Cosa registrare in ogni misura MPI o ibrida (sito, sezione 6.8.8):

1. dimensione globale e locale del problema;
2. numero di nodi, rank e thread;
3. collocazione di rank e thread;
4. dimensione e frequenza dei messaggi;
5. compilatore, opzioni, libreria MPI e variabili d'ambiente rilevanti;
6. regione misurata, numero di ripetizioni e statistica riportata;
7. controlli di correttezza a ogni scala.

Lo speedup da solo non spiega un cambiamento di prestazioni: va messo in relazione con
il lavoro per rank, il volume di comunicazione, il numero di messaggi e collettive,
il bilanciamento e l'hardware disponibile.

:::{note} Domande di controllo
1. Perché `MPI_Init` non crea i processi? Chi li crea su WILSON?
2. Con quali tre campi MPI decide se un messaggio corrisponde a una receive? Il tipo
   di dato è fra questi?
3. Perché uno scambio con `MPI_Send` seguito da `MPI_Recv` su entrambi i rank può
   funzionare con 10 double e bloccarsi con un milione?
4. Dopo `MPI_Isend`, cosa si può fare con il buffer prima di `MPI_Wait`? E dopo
   `MPI_Irecv`?
5. Dopo `MPI_Reduce` con radice 0, quale valore ha `global_sum` sul rank 2?
6. Con 4 rank e `colour = world_rank % 2`, che rank ha il processo 3 nel nuovo
   communicator?
7. In `double a[4][6]`, perché la colonna si descrive con
   `MPI_Type_vector(4, 1, 6, MPI_DOUBLE, ...)`?
8. Se il lato $L$ del dominio locale si dimezza, come cambia il rapporto fra dati
   scambiati e celle aggiornate?
9. Perché una chiamata MPI dentro `#pragma omp single` non rispetta
   `MPI_THREAD_FUNNELED`?
:::
