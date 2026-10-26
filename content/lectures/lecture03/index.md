# Parallelismo e programmazione parallela

Il parallelismo divide il lavoro tra più unità di esecuzione. Per ottenere un programma corretto ed efficiente occorre identificare il lavoro indipendente, assegnare dati e risorse, coordinare le dipendenze e misurare i costi introdotti dalla collaborazione.

(motivazioni-e-decomposizione)=
## Perché parallelizzare e come dividere il lavoro

Problemi più grandi possono richiedere più memoria o tempo di quanto un singolo processore possa offrire. Aumentare il numero di unità di calcolo, però, non accelera automaticamente un programma: l'algoritmo deve esporre operazioni indipendenti e distribuire il lavoro in modo ragionevole.

La **decomposizione dei dati** assegna porzioni diverse dei dati a lavoratori che svolgono operazioni simili. La **decomposizione dei compiti** assegna operazioni differenti, talvolta come stadi di una pipeline. Una riduzione, come la somma di un array, richiede di calcolare risultati parziali e combinarli; non basta aggiornare una variabile condivisa senza coordinamento.

La concorrenza descrive attività che possono progredire nello stesso intervallo; il parallelismo descrive attività che vengono eseguite simultaneamente su unità diverse. Più attività software possono alternarsi su una sola CPU logica senza essere eseguite in parallelo.

(processi-thread-risorse)=
## Processo, thread, CPU logica e nodo

| Termine | Significato |
|---|---|
| Processo | Programma in esecuzione con il proprio spazio di indirizzamento |
| Thread | Flusso di esecuzione appartenente a un processo; thread dello stesso processo condividono memoria |
| CPU logica | Contesto hardware visibile al sistema operativo; può condividere un core fisico con un'altra CPU logica |
| Nodo | Computer del cluster che ospita processi, CPU e memoria |

Il numero di processi, thread e CPU logiche non è intercambiabile. Il sistema operativo assegna thread software alle CPU logiche disponibili; più thread possono essere eseguiti a turno sulla stessa CPU logica.

(shared-memory-openmp)=
## Shared-memory e OpenMP

**Shared-memory** significa memoria condivisa: i thread dello stesso processo possono accedere alle stesse aree di memoria. Le variabili condivise richiedono attenzione quando più thread le modificano.

**OpenMP** permette di usare più thread all'interno di ciascun processo, tipicamente tramite direttive nel codice. `OMP_NUM_THREADS` richiede un numero di thread, ma l'effettiva esecuzione dipende dalle risorse assegnate e dalla configurazione del runtime. Non implica che ogni thread abbia una CPU distinta.

Una *race condition* si verifica quando il risultato dipende dall'ordine temporale di accessi concorrenti. Per esempio, più thread che incrementano la stessa variabile senza sincronizzazione possono perdere aggiornamenti. Una riduzione o un'altra sincronizzazione appropriata protegge il risultato; lock e barriere, se usati troppo spesso, aggiungono costo.

Questo esempio crea un team OpenMP e stampa il numero dei thread una sola volta:

```c
#include <omp.h>
#include <stdio.h>

int main(void)
{
#pragma omp parallel
    {
#pragma omp single
        printf("Thread nel team: %d\n", omp_get_num_threads());
    }
    return 0;
}
```

(mpi-memoria-distribuita)=
## MPI e memoria distribuita

**MPI** è utile quando il calcolo viene distribuito tra più processi, anche sullo stesso nodo oppure su nodi diversi. I processi possiedono normalmente spazi di indirizzamento separati e comunicano tramite messaggi. Un **rank MPI** identifica un processo nel gruppo di comunicazione.

MPI non richiede necessariamente più nodi. La collocazione dei rank dipende dall'esecuzione e dalle risorse assegnate. Quando i dati sono distribuiti, il programma deve definire quali dati appartengono a ciascun processo e quali messaggi servono per scambiare informazioni.

Le comunicazioni **point-to-point** scambiano dati tra rank; le operazioni **collettive** coordinano un gruppo, per esempio per distribuire dati o combinare risultati. I partecipanti devono rispettare il protocollo e l'ordine richiesto. Attese incompatibili possono causare un deadlock, nel quale i processi aspettano eventi che non possono più verificarsi.

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

(disposizione-e-slurm)=
## Disposizione, affinità e Slurm

La **disposizione** descrive quanti processi e thread vengono avviati e su quali nodi. L'**affinità** limita le CPU logiche sulle quali un processo o thread può essere eseguito; non garantisce che vi resti in ogni istante. L'**oversubscription** si verifica quando si richiedono più flussi software di quante CPU logiche siano assegnate. Può essere intenzionale, ma spesso causa contesa e non è una scorciatoia per ottenere più capacità.

Slurm è uno scheduler: gestisce le richieste di risorse e decide quando e dove eseguire i job secondo la configurazione del cluster. Un programma dovrebbe allineare il numero di processi e thread alle risorse richieste. Opzioni, partizioni e politiche sono specifiche del sistema; per WILSON non vanno dedotte da esempi generici.

(prestazioni-scalabilita)=
## Prestazioni e scalabilità

Per un problema e una misura comparabili, lo **speedup** è $S_p=T_1/T_p$, dove $T_1$ è il tempo di riferimento e $T_p$ il tempo con $p$ unità di elaborazione. L'**efficienza** è $E_p=S_p/p$. Specifica sempre il problema, il baseline e cosa rappresenta $p$.

La legge di Amdahl per un problema fisso con frazione seriale $s$ dà il limite ideale:

$$S_p = \frac{1}{s + (1-s)/p}.$$

Comunicazione, sincronizzazione, sbilanciamento del carico e accesso concorrente alla memoria riducono ulteriormente il guadagno. Nello **strong scaling** la dimensione globale resta fissa mentre aumentano le risorse. Nel **weak scaling** cresce il problema per mantenere circa costante il lavoro per unità di elaborazione. Sono esperimenti diversi e vanno descritti separatamente.

La trattazione è una sintesi rielaborata del [capitolo originale Parallel computing](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/parallel-computing.html).

(schema-riepilogativo)=
## Schema riepilogativo

:::{note} Tre modelli di parallelismo
:class: parallel-summary

- **Shared memory = OpenMP** — thread dello stesso processo lavorano sulle aree di memoria condivise.
- **Distributed memory = MPI** — processi con spazi di memoria normalmente separati comunicano tramite messaggi.
- **Hybrid = MPI + OpenMP** — MPI coordina la comunicazione tra processi; OpenMP crea thread all'interno di ciascun processo.
:::

:::{figure} ../../figures/Modelli di parallelismo in HPC.png
:name: fig-parallelism-models
:alt: Confronto visivo tra OpenMP a memoria condivisa, MPI a memoria distribuita e modello ibrido MPI più OpenMP.
:width: 100%
:::

### I tre approcci a confronto

| Approccio | Quando si usa | Esempio |
|---|---|---|
| OpenMP — memoria condivisa | Per parallelizzare un programma all'interno di un nodo, usando più thread. | Elaborare un grande array con più thread. |
| MPI — memoria distribuita | Per distribuire il lavoro tra più processi, anche su nodi differenti. | Simulare un fenomeno fisico dividendo il dominio tra processi. |
| MPI + OpenMP — ibrido | Per usare MPI tra processi e OpenMP all'interno di ciascun processo. | Simulazioni scientifiche su cluster con molti nodi e core. |

**La regola pratica da ricordare:** OpenMP sfrutta il parallelismo all'interno di un processo; MPI distribuisce il lavoro tra processi; l'approccio ibrido combina i due. Non esiste un approccio sempre migliore: nei cluster si sceglie in base al programma e alle prestazioni misurate.
