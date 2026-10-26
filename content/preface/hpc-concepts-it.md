# Concetti HPC — introduzione

Questa pagina è una guida al vocabolario. Risponde, in un unico punto e in
linguaggio semplice, ai termini che compaiono in ogni lezione, esercizio e
relazione di benchmark HPC: *core*, *cache*, *thread*, *processo*, *OpenMP*,
*MPI*, *memory bandwidth*, *O(n)*, *speedup* e simili.

Non è materiale del corso e non lo sostituisce. Leggila una volta adesso, così
nelle lezioni il vocabolario non va più spiegato; rileggila quando un termine
ti blocca.

L'ordine qui sotto è quello in cui i concetti dipendono l'uno dall'altro:
prima l'hardware, poi la gerarchia di memoria, poi il modello di costo
(complessità e banda), poi il parallelismo, poi i due strumenti (OpenMP e MPI).

---

## 1. La scala dell'hardware

**Core.** Unità di esecuzione indipendente dentro la CPU. Ha la sua pipeline,
i suoi registri e di solito le proprie cache L1 e L2 private. Un processore
moderno ne ha da pochi a oltre cento.

**Pipeline.** Il core non esegue le istruzioni una dopo l'altra: le fa passare
in una catena di stadi (lettura, decodifica, esecuzione, accesso alla memoria,
scrittura del risultato), così più istruzioni sono in volo nello stesso
istante, come auto su una linea di montaggio. I core moderni hanno decine di
stadi, più l'*esecuzione superscalare* (più istruzioni per ciclo di clock) e
l'*esecuzione out-of-order* (il core esegue ciò che è pronto, non ciò che
compare nel sorgente).

**Clock.** Un clock a 3 GHz batte ogni 0,33 ns. In quel tempo la luce percorre
circa 10 cm. Il modo più semplice per ricordare che la distanza fisica fra
core, cache e RAM è un parametro di prestazioni, non una curiosità.

**Thread hardware (SMT).** Un core può presentarsi al sistema operativo come
due CPU logiche. Le due condividono le unità di calcolo, quindi non raddoppiano
la potenza: aiutano a riempire i buchi lasciati dalle attese in memoria. Su
codici HPC numerici, limitati dalla memoria, il guadagno è spesso quasi
nullo.

**RAM (DRAM).** Memoria principale. Volatile, economica, grande e molto più
lenta della logica del core. Ogni bit è un condensatore che va rinfrescato.

**GPU.** Migliaia di core più semplici, progettati per eseguire la stessa
istruzione su molti dati insieme. Eccellenti per il calcolo data-parallel,
scarsi per codice pieno di rami.

| Livello | Dimensione tipica | Latenza approssimativa | Cicli a 3 GHz |
|---|---|---|---|
| Registri | pochi KB | < 1 ns | 1 |
| Cache L1 | 32-64 KB per core | ~1 ns | 4 |
| Cache L2 | 256 KB - 2 MB per core | ~3-5 ns | 12 |
| Cache L3 | da 8 MB a >100 MB, condivisa | ~10-20 ns | 40 |
| RAM | da decine a centinaia di GB | ~80-100 ns | 250-300 |
| SSD NVMe | centinaia di GB a TB | ~20-100 µs | decine di migliaia |
| Disco meccanico | TB | ~5-10 ms | milioni |

:::{figure} figures/cache-hierarchy.png
:name: fig-cache-hierarchy-it
:width: 55%

La gerarchia di memoria di una macchina moderna: L1 e L2 sono private di ogni
core, L3 è condivisa da tutti i core, e sotto ci sono RAM e memorizzazione
esterna.
*Immagine: Wikimedia Commons, "Multi-level Cache Hierarchy diagram" di
Ferry24.Milan, CC BY-SA 4.0, via Wikipedia "Memoria cache".*
:::

**Il muro della memoria.** La velocità dei core è cresciuta molto più in fretta
di quella della RAM. Un core moderno esegue centinaia di istruzioni nel tempo
che la RAM impiega per una sola risposta. La CPU è una pompa potentissima
collegata a un tubo stretto: tutto ciò che il calcolo fa con i dati passa da
quel tubo, e il tubo è il collo di bottiglia. Per questo la maggior parte dei
codici scientifici è **memory-bound**, non compute-bound.

---

## 2. Cache memory

**La cache, in una frase.** *Una cache è una copia piccola e veloce di dati
tenuta vicino al core, per non dover andare a cercarli lontano.*

- **copia** — il contenuto vero sta in RAM; la cache tiene una copia di ciò che
  è stato usato di recente;
- **piccola** — da decine di KB (L1) a decine di MB (L3), contro i GB della RAM;
- **vicina** — più è vicino al core, più corto è il filo e minore la latenza.

**Cache line.** L'unità di trasferimento fra cache e RAM: di solito 64 byte. La
cache non porta un byte alla volta, porta tutta la linea, perché il costo
della richiesta è dominato dalla latenza e non dal payload (portare 64 byte
costa quasi quanto portarne 8), e perché i byte vicini serviranno subito dopo.

**Hit e miss.** Un *hit* è un accesso servito dalla cache; un *miss* è un
accesso che deve scendere di un livello. I miss hanno tre cause:
*compulsory* (primo accesso in assoluto), *capacity* (il working set non
ciesta) e *conflict* (il dato ci starebbe, ma il set era pieno).

**Tag, index, offset.** L'indirizzo viene spezzato in campi: *offset* (quale
byte dentro la linea), *index* (quale set controllare) e *tag* (quale blocco di
RAM si trova davvero lì). Esempio: una L1 da 32 KB con linee da 64 byte e
associatività 8 ha 32768 / (64 x 8) = 64 set, quindi 6 bit di index e 6 di
offset; il resto dell'indirizzo è il tag.

**Associatività.** Quanti posti può occupare un blocco dentro il suo set (le
*way*). *Direct-mapped* (1 way) è la più semplice ma collide spesso;
*set-associative* (8 o 12-16 way) è lo standard, perché tutte le way vengono
cercate in parallelo; *fully associative* si usa solo per strutture piccole
come il TLB.

:::{figure} figures/cache-operation.png
:name: fig-cache-operation-it
:width: 60%

Come la cache risponde a una richiesta: il processore manda un indirizzo, la
cache confronta i tag memorizzati e, in caso di miss, carica il blocco dalla
memoria principale.
*Immagine: Wikimedia Commons, "Cache operation diagram" di Ferry24.Milan,
CC BY-SA 4.0, via Wikipedia "Memoria cache".*
:::

**Località.** Due regolarità fanno funzionare la gerarchia:

- *località temporale*: un valore usato adesso tornerà probabilmente a breve;
- *località spaziale*: un valore usato adesso rende probabile l'uso dei vicini.

Il *prefetcher* hardware sfrutta questo: riconosce pattern regolari
(sequenziali o a passo costante) e carica i dati in anticipo. Gli accessi
casuali, come seguire puntatori sparsi, lo disattivano completamente.

**Politiche di scrittura.** *Write-through* porta la scrittura in RAM subito
(semplice, molto traffico); *write-back* la tiene in cache e marca la linea
*dirty*, riversandola solo quando la linea viene espulsa. Le cache moderne sono
write-back.

**False sharing.** Due core che scrivono su due variabili diverse ma che
finiscono nella stessa cache line invalidano la copia dell'altro a ogni
scrittura. Il programma è corretto ma lento. Il rimedio è separare le
variabili su linee diverse con il padding.

---

## 3. Latenza e banda di memoria

**Latenza**: il tempo per ottenere un dato, dalla richiesta alla risposta.
**Banda**: quanti byte al secondo si possono trasferire una volta partito il
flusso.

L'analogia dell'auto: la latenza è il tempo di viaggio da una città all'altra,
la banda è quante auto al secondo arrivano, cioè la larghezza dell'autostrada.

Per saturare una banda servono molte richieste in volo contemporaneamente. La
legge di Little (`L = lambda x W`: elementi in sistema = frequenza di arrivo x
tempo di permanenza) dà la regola pratica: byte in volo = latenza x banda. Con
100 ns di latenza e 50 GB/s di banda servono 100e-9 x 50e9 = 5000 byte in
volo, cioè circa 80 cache line.

Il benchmark di banda di riferimento è la *triad* di STREAM, `a = b + s*c`: si
leggono due array e se ne scrive un terzo. L'implementazione di riferimento
è in [reference](../reference/linux.md); per NumPy si contano di solito
3 x 8 byte per elemento.

**NUMA.** Su macchine multi-socket la RAM è collegata a un socket. Accedere
alla memoria dell'altro socket è più lento, quindi conta dove gira un thread.

---

## 4. Complessità, O(...)

La notazione Big-O descrive come cresce il costo quando cresce la dimensione
`n` dell'input. Ignora le costanti e i termini di ordine inferiore: non dice
quanto è veloce un programma, ma come scala.

| Notazione | Crescita | Esempio |
|---|---|---|
| O(1) | costante | leggere un elemento di un array per indice |
| O(log n) | si dimezza a ogni passo | ricerca binaria |
| O(n) | un passaggio sui dati | somma di un array |
| O(n log n) | ordinamento efficiente tipico | merge sort, heapsort |
| O(n^2) | tutte le coppie | confronto di ogni coppia di punti |

Due precisazioni che contano per l'HPC:

1. Big-O ignora la gerarchia di memoria. Un algoritmo O(n) con accessi casuali
   può essere più lento di uno O(n log n) con accessi sequenziali, perché la
   cache lavora molto meglio sul secondo.
2. Le costanti contano. Un O(n^2) con costante piccola può battere un
   O(n log n) per valori piccoli di `n`.

Esempio dalla fisica: le interazioni a coppie in una simulazione di `N`
particelle costano O(N^2). Per questo esistono le *neighbor list* e i
*cut-off*: riducono il lavoro a circa O(N) per interazioni a corto raggio.

---

## 5. Core, thread, processi

**Processo.** Un programma in esecuzione, con il proprio spazio di indirizzi.
Due processi non vedono la memoria l'uno dell'altro se non la scambiano
esplicitamente (pipe, socket, messaggi MPI). Crearne uno è relativamente
costoso; l'isolamento è il prezzo.

**Thread.** Un flusso di esecuzione dentro un processo. Tutti i thread di un
processo condividono la memoria, ma ciascuno ha il proprio stack e i propri
registri. Creare un thread è economico; la memoria condivisa è il prezzo,
perché un accesso concorrente non sincronizzato produce *race condition*.

**Scheduler e affinity.** Il sistema operativo assegna i thread software ai
thread hardware. Spostare un thread su un altro core ne invalida i dati in
cache, quindi nei codici HPC i thread vengono spesso fissati su core precisi
(*thread affinity*, controllata in OpenMP con `OMP_PROC_BIND` e `OMP_PLACES`).

**Memoria condivisa e memoria distribuita.**

- *memoria condivisa*: i thread di un processo lavorano sugli stessi dati.
  Modello: **OpenMP**.
- *memoria distribuita*: processi su nodi diversi, ognuno con la propria RAM,
  che scambiano dati con messaggi. Modello: **MPI**.

**Il GIL.** In CPython un lock globale permette a un solo thread alla volta di
eseguire bytecode Python. I thread quindi non accelerano il calcolo Python
puro; le librerie scritte in C (NumPy) rilasciano il GIL e ne traggono
beneficio.

---

## 6. Misurare le prestazioni parallele

**Concorrenza** riguarda la struttura: più attività avanzano nello stesso
intervallo, magari su un solo core, alternandosi. **Parallelismo** riguarda
l'esecuzione: più attività girano davvero nello stesso istante, su più core.

**Speedup** `S(p) = T1 / Tp` (tempo seriale diviso tempo parallelo).
**Efficienza** `E(p) = S(p) / p`: quanto del parallelismo teorico viene
sfruttato. Efficienza del 50% su 64 core significa ottenere l'equivalente di
32.

**Legge di Amdahl** (problema fisso). Se una frazione `f` è parallelizzabile:

```text
S(p) = 1 / ((1 - f) + f/p)
```

Quando `p` cresce, lo speedup tende a `1 / (1 - f)`: la parte seriale domina.
Con il 5% di codice seriale lo speedup massimo è 20, qualunque sia il numero
di core.

**Legge di Gustafson** (il problema cresce con i processori): `S(p) = (1 - f) + f p`,
quasi lineare. Le due leggi rispondono a domande diverse: "quanto è più veloce
questo problema?" e "quanto problema più grande posso risolvere?".

**Strong e weak scaling.** *Strong*: stesso problema, più processori, si misura
il tempo di esecuzione. *Weak*: il problema cresce con i processori in modo
che il lavoro per processore resti costante; idealmente il tempo resta
costante.

**Overhead.** Il parallelismo non è gratis: creazione e gestione di thread o
processi, sincronizzazione (barriere, lock), squilibrio del carico (durate
diverse dei task) e comunicazione.

---

## 7. OpenMP

Una API per il parallelismo a memoria condivisa in C, C++ e Fortran. Il
programma parte come un solo thread (il *master*); in una regione parallela
viene creato un *team* di thread, e il master si ricongiunge a loro alla fine.
È il modello **fork-join**.

Direttive principali: `parallel`, `parallel for`, `critical`, `atomic`,
`barrier`, `single`, `master`, `task`.

Clausole principali: `private(x)`, `shared(x)`, `firstprivate(x)`,
`reduction(op:x)`, `schedule(static|dynamic|guided, chunk)`, `default(none)`.

La `reduction` è il modo corretto di sommare o di prendere un massimo in
parallelo: ogni thread accumula in una copia privata e le copie vengono
combinate alla fine. Senza, gli aggiornamenti concorrenti della stessa
variabile sono una race condition.

```bash
gcc -fopenmp -o prog prog.c
OMP_NUM_THREADS=4 ./prog
```

Anche il false sharing compare qui: contatori tenuti vicini in un array sono
condivisi fra thread; separarli su linee diverse con il padding.

Vedi [reference/openmp](../reference/openmp.md).

---

## 8. MPI

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

---

## 9. Glossario rapido

| Termine | Significato |
|---|---|
| Core | Unità di esecuzione indipendente dentro la CPU |
| Thread hardware (SMT) | CPU logica offerta da un core, che condivide le unità di calcolo |
| Processo | Programma in esecuzione, con il proprio spazio di indirizzi |
| Thread | Flusso di esecuzione dentro un processo, con memoria condivisa |
| Cache | Copia piccola e veloce dei dati tenuta vicino al core |
| Cache line | Blocco di memoria trasferito tutto insieme, di solito 64 byte |
| Hit / miss | Accesso servito dalla cache / accesso che deve scendere di livello |
| Associatività | Numero di posti che un blocco può occupare nel suo set |
| Tag, index, offset | Campi in cui l'indirizzo viene spezzato per cercare in cache |
| Località | Tendenza a riusare dati recenti e dati vicini |
| Prefetching | Caricamento anticipato quando il pattern di accesso è prevedibile |
| False sharing | Variabili indipendenti nella stessa cache line, contese dai core |
| TLB | Cache delle traduzioni da indirizzo virtuale a fisico |
| NUMA | Memoria la cui latenza dipende dal socket a cui è collegata |
| Latenza | Tempo per ottenere un singolo dato |
| Banda | Byte trasferiti al secondo |
| Complessità O(f) | Come cresce il costo quando cresce la dimensione dell'input |
| Speedup, efficienza | `T1/Tp`; speedup diviso per il numero di processori |
| Legge di Amdahl | Limite allo speedup imposto dalla parte seriale del codice |
| Strong / weak scaling | Stesso problema con più processori / problema che cresce con loro |
| Squilibrio del carico | Distribuzione diseguale del lavoro fra thread o processi |
| Concorrenza / parallelismo | Attività che avanzano insieme / attività che girano nello stesso istante |
| SIMD | Una istruzione applicata a più dati in un colpo solo |
| GIL | Lock di CPython che serializza il bytecode Python fra thread |
| Race condition | Accesso concorrente non sincronizzato, risultato non deterministico |
| Reduction | Combinazione sicura di valori parziali (somma, massimo) a fine regione |
| Fork-join | Modello in cui un master crea un team di thread e poi si ricongiunge |
| Barrier | Punto in cui tutti i thread o i processi attendono gli altri |
| Rank | Identificativo di un processo MPI |
| Communicator | Gruppo di processi MPI che possono comunicare |
| Collective | Operazione MPI che coinvolge tutti i processi del communicator |
| SPMD | Modello in cui tutti i processi eseguono lo stesso programma su dati diversi |
| Deadlock | Stallo in cui processi o thread si aspettano a vicenda per sempre |
| Halo / celle fantasma | Copie dei bordi ricevute dai vicini |

---

## 10. Domande di controllo

::::{dropdown} 1. Perché la cache trasferisce linee da 64 byte e non byte singoli?

Il costo di una richiesta alla RAM è dominato dalla latenza, non dal payload:
portare 64 byte costa quasi quanto portarne 8. Inoltre i byte vicini a quello
richiesto serviranno quasi subito (località spaziale), quindi non sono
sprecati.

:::

::::{dropdown} 2. Una cache L1 da 32 KB ha linee da 64 byte e associatività 8. Quanti set, e quanti bit di index?

32768 / (64 x 8) = 64 set, quindi 6 bit di index (2^6 = 64) e 6 bit di offset;
i bit restanti dell'indirizzo sono il tag.

:::

::::{dropdown} 3. Un hit dura 1 ns, il miss rate è 3%, la penalità di miss è 100 ns. Qual è il tempo medio di accesso?

AMAT = 1 + 0,03 x 100 = 4 ns.

:::

::::{dropdown} 4. Che differenza c'è tra latenza e banda? Quanti byte devono essere in volo con 100 ns di latenza e 50 GB/s di banda?

La latenza è il tempo per ottenere un dato; la banda è quanti byte al secondo
passano una volta partito il flusso. Byte in volo = latenza x banda =
100e-9 x 50e9 = 5000 byte, cioè circa 80 cache line.

:::

::::{dropdown} 5. Perché sommare una matrice per colonne può essere molto più lento che per righe?

Gli elementi di una matrice sono memorizzati per righe, quindi sommare per
righe usa tutta la linea da 64 byte caricata. Sommare per colonne salta di
`n x 8` byte a ogni passo, e ogni elemento richiede una linea diversa. Se
`n x 8` è una potenza di 2 (per esempio n = 512), tutti gli elementi di una
colonna finiscono nello stesso set e si accumulano i conflict miss.

:::

::::{dropdown} 6. Se il 10% di un programma è seriale, qual è lo speedup massimo?

Legge di Amdahl: S(infinito) = 1 / 0,1 = 10. Nessun numero di processori può
fare meglio.

:::

::::{dropdown} 7. Perché i thread Python non accelerano il calcolo Python puro, mentre NumPy sì?

Il GIL permette a un solo thread alla volta di eseguire bytecode Python, quindi
i thread si alternano invece di lavorare insieme. NumPy esegue il ciclo in C e
rilascia il GIL durante il calcolo, così più thread lavorano davvero in
parallelo.

:::

::::{dropdown} 8. Cosa succede se più thread OpenMP incrementano la stessa variabile senza `reduction`?

Si verifica una race condition: alcuni incrementi si perdono, e il risultato
è sbagliato e diverso da un'esecuzione all'altra. Con `reduction` ogni thread
accumula in una copia privata e le copie vengono sommate alla fine.

:::

::::{dropdown} 9. Perché due processi MPI che fanno entrambi `Send` prima di entrambi `Recv` possono bloccarsi?

Con messaggi grandi il protocollo rendezvous attende che il ricevente sia
pronto, ma entrambi i processi sono bloccati in `Send`, quindi nessuno riceve
mai. Si risolve con `Sendrecv`, oppure rendendo asimmetrico l'ordine fra rank
pari e dispari.

:::

::::{dropdown} 10. Un algoritmo O(n^2): quanto più lento quando n raddoppia?

Quattro volte più lento, perché (2n)^2 = 4n^2.

:::

---

## Come proseguire

- [Lecture 2 — performance models (Roofline)](../lectures/lecture02/index.md):
  come capire se un kernel è limitato dal calcolo o dalla memoria.
- [Lecture 3](../lectures/lecture03/index.md): OpenMP e MPI in pratica.
- [Reference: OpenMP](../reference/openmp.md), [reference: MPI](../reference/mpi.md),
  [reference: compilation](../reference/compilation.md).
