# Calcolo parallelo

Il parallelismo divide il lavoro tra più unità di esecuzione. Per ottenere un programma corretto ed efficiente occorre identificare il lavoro indipendente, assegnare dati e risorse, coordinare le dipendenze e misurare i costi introdotti dalla collaborazione.

:::{seealso} Fonte principale
Capitolo 2 del corso, [*Parallel computing*](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/parallel-computing.html). Questa pagina riordina le note già scritte secondo la struttura di quel capitolo.
:::

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

### Core, thread, processi in dettaglio

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

(prestazioni-scalabilita)=
## Prestazioni e scalabilità

Per un problema e una misura comparabili, lo **speedup** è $S_p=T_1/T_p$, dove $T_1$ è il tempo di riferimento e $T_p$ il tempo con $p$ unità di elaborazione. L'**efficienza** è $E_p=S_p/p$. Specifica sempre il problema, il baseline e cosa rappresenta $p$.

La legge di Amdahl per un problema fisso con frazione seriale $s$ dà il limite ideale:

$$S_p = \frac{1}{s + (1-s)/p}.$$

Comunicazione, sincronizzazione, sbilanciamento del carico e accesso concorrente alla memoria riducono ulteriormente il guadagno. Nello **strong scaling** la dimensione globale resta fissa mentre aumentano le risorse. Nel **weak scaling** cresce il problema per mantenere circa costante il lavoro per unità di elaborazione. Sono esperimenti diversi e vanno descritti separatamente.

La trattazione è una sintesi rielaborata del [capitolo originale Parallel computing](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/parallel-computing.html).

(t-amdahl)=
### Speedup, Amdahl e Gustafson

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

(schema-riepilogativo)=
## Schema riepilogativo

:::{note} Tre modelli di parallelismo
:class: parallel-summary

- **Shared memory = OpenMP** — thread dello stesso processo lavorano sulle aree di memoria condivise.
- **Distributed memory = MPI** — processi con spazi di memoria normalmente separati comunicano tramite messaggi.
- **Hybrid = MPI + OpenMP** — MPI coordina la comunicazione tra processi; OpenMP crea thread all'interno di ciascun processo.
:::

:::{figure} figures/modelli-parallelismo.png
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

(benchmarking-del-parallelismo)=
## Misurare ciò che si è parallelizzato

Un programma parallelo va misurato, non solo eseguito: speedup, efficienza e scalabilità dicono se i core aggiunti vengono davvero usati. La dispensa [Performance e benchmarking](03-performance-benchmarking.md) tratta metriche, misure affidabili, profiling e i benchmark standard (HPL, STREAM, HPCG), con gli esempi di configurazione su WILSON e Raspberry Pi 5.
