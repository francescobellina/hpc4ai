# Architetture di calcolo

Per capire le prestazioni di un programma HPC bisogna considerare insieme il lavoro aritmetico, i dati e l'hardware che li elabora. Questo capitolo introduce i componenti essenziali di un nodo e spiega perché il modo in cui si accede ai dati può limitare il calcolo.

:::{seealso} Fonte principale
Capitolo 1 del corso, [*Computing architectures*](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/computing-architectures/index.html). Questa pagina riordina le note già scritte secondo la struttura di quel capitolo.
:::

(cpu-e-nodi)=
## CPU, core e nodi

Una **CPU** è il processore installato in un socket. Contiene uno o più **core**: unità capaci di eseguire flussi di istruzioni indipendenti. Il sistema operativo può esporre più **CPU logiche** per core con la tecnologia SMT. Una CPU logica non è un core aggiuntivo: condivide risorse di calcolo con gli altri thread hardware dello stesso core.

Un **processo** è un programma in esecuzione con il proprio spazio di indirizzamento. Un **thread** è un flusso di esecuzione dentro un processo. Più thread dello stesso processo possono condividere la memoria, ma non diventano per questo core o CPU logiche.

Un **nodo** è un computer del cluster: può contenere più CPU, core e memoria RAM. Un cluster collega più nodi tramite una rete e li rende disponibili per calcoli paralleli. Non assumere numero di core, RAM, rete o acceleratori di un sistema specifico senza verificarne la documentazione.

### La scala dell'hardware

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

## Memoria e movimento dei dati

(gerarchia-memoria)=
### Gerarchia della memoria

Il processore lavora su dati che devono essere trasferiti fino alle unità di esecuzione. La memoria è organizzata per bilanciare velocità, capacità e costo:

| Livello | Ruolo | Caratteristica generale |
|---|---|---|
| Registri | Operandi immediati delle istruzioni | Molto piccoli e veloci |
| Cache L1, L2 e L3 | Copie temporanee dei dati usati dal processore | Più vicine e rapide della RAM, ma di capacità minore |
| RAM | Dati e codice attivi | Molto più capiente, ma con accesso più lento |
| Storage | File persistenti | Capiente; non sostituisce la RAM durante il normale accesso alle variabili |

La disposizione concreta delle cache varia tra processori: alcuni livelli sono privati di un core, altri condivisi tra più core. La tabella descrive una gerarchia tipica, non le specifiche di WILSON.

Una **cache line** trasferisce un blocco di byte, non un singolo valore. Quando un programma riusa presto lo stesso dato sfrutta la **località temporale**; quando visita indirizzi vicini sfrutta la **località spaziale**. Per esempio, percorrere in ordine gli elementi contigui di un array tende a usare meglio le linee di cache di accessi casuali o con grandi salti.

(t-cache)=
### Cache

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

(latenza-banda)=
### Latenza, banda e colli di bottiglia

La **latenza** è il tempo necessario per ottenere un dato. La **banda passante** è la quantità di dati trasferibile nell'unità di tempo. Una banda elevata non implica che la risposta alla singola richiesta arrivi con bassa latenza.

Un programma è **memory-bound** quando la velocità è limitata soprattutto dal trasferimento dei dati; è **compute-bound** quando è limitata soprattutto dal calcolo. Lo stesso programma può avere limiti diversi su macchine diverse o in fasi diverse.

L'intensità aritmetica mette in relazione le operazioni e il traffico di memoria:

$$I = \frac{N_{\mathrm{flop}}}{Q} \qquad [\mathrm{flop/byte}],$$

dove $N_{\mathrm{flop}}$ è il numero di operazioni floating-point e $Q$ il numero di byte trasferiti. Il risultato dipende dall'implementazione e dal livello di memoria considerato.

### Latenza e banda in pratica

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

(memoria-e-topologia)=
### Memoria condivisa, distribuita e NUMA

In un nodo, i thread di uno stesso processo possono accedere allo spazio di memoria condiviso. In un cluster, la RAM di un nodo non è automaticamente accessibile a un processo su un altro nodo: i programmi distribuiti devono trasferire dati attraverso la rete. MPI è una possibile interfaccia per questa comunicazione; il capitolo sul parallelismo ne descrive il modello.

Nei sistemi **NUMA** la memoria è condivisa nello spazio di indirizzi, ma il costo di accesso dipende dalla vicinanza tra core e memoria. Collocare thread e dati senza considerare la topologia può aumentare la latenza o ridurre la banda disponibile.

Acceleratori come le GPU possono fornire molte unità di calcolo e memoria propria. Sono utili quando il problema espone lavoro adatto e il trasferimento dei dati è giustificato. La loro disponibilità e configurazione dipendono dal sistema; questo testo non assume che WILSON ne disponga.

(modello-roofline)=
## Modelli di prestazione

### Modello Roofline

Se il picco aritmetico è $P_{\max}$ e la banda sostenibile è $B$, il modello Roofline fornisce il limite:

$$P \leq \min(P_{\max}, B I).$$

Il punto di passaggio tra i limiti è la *ridge point*, $I_{\mathrm{ridge}}=P_{\max}/B$. A sinistra del punto il modello indica un limite di banda; a destra indica un limite di calcolo. È un modello, non una previsione né una misura: dipendenze, accessi irregolari, parallelismo insufficiente e overhead possono mantenere il programma sotto il limite.

Un esempio puramente ipotetico usa $P_{\max}=1.5\ \mathrm{Tflop/s}$ e $B=100\ \mathrm{GB/s}$: la ridge point è $15\ \mathrm{flop/byte}$. Questi numeri illustrano il calcolo e non descrivono WILSON.

Il [notebook Roofline](notebooks/performance-models.ipynb) permette di esplorare questo modello con parametri ipotetici. I valori prodotti dal notebook non sono benchmark verificati di un sistema reale.

(t-complessita)=
### Complessità, O(...)

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

(t-aritmetica)=
## Aritmetica in virgola mobile

In virgola mobile il risultato di un'operazione è
$\operatorname{fl}(x) = x(1+\delta)$ con $|\delta| \le \varepsilon$, dove
$\varepsilon$ è la **epsilon di macchina**. In singola precisione (binary32,
`float32`) il significando ha $p = 24$ bit e

$$\varepsilon = 2^{-(p-1)} = 2^{-23} \approx 1.19 \times 10^{-7},$$

cioè circa 7 cifre decimali; in doppia precisione (binary64, `float64`)
$\varepsilon = 2^{-52} \approx 2.22 \times 10^{-16}$.

Due sorgenti di errore competono in una somma finita:

- **Errore di troncamento** — si scartano i termini oltre $N$. Per la serie di
  Basilea $\pi^2/6 - S(N) \approx \int_N^\infty x^{-2}\,dx = 1/N$: cala come
  $1/N$.
- **Errore di arrotondamento** — ogni addizione arrotonda al rappresentabile più
  vicino. Nel caso peggiore cresce come $N\varepsilon$. L'effetto pratico è che
  **aggiungere un termine molto piccolo a una somma grande perde quei bit**.

Da qui la **dipendenza dall'ordine di somma**: sommare prima i termini piccoli
(ordine inverso, da $N$ a $1$) mantiene la precisione relativa; sommarli da ultimi
(ordine diretto, da $1$ a $N$) li perde quando $1/n^2 < \varepsilon\, S$.

(implicazioni-esercizi)=
## Implicazioni per gli esercizi

Prima di ottimizzare, chiediti dove sono i dati, con quale regolarità vengono visitati e quale risorsa limita la fase misurata. Migliorare la località può ridurre i trasferimenti; aggiungere thread non aiuta se la banda di memoria è già satura. Confronta sempre il modello con misure riproducibili e documenta dimensione del problema, hardware e configurazione usata.

La trattazione è una sintesi rielaborata del [capitolo originale Computing architectures](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/computing-architectures/index.html).

(benchmark-e-misure)=
## Misurare le prestazioni

Il modello Roofline dice dove *dovrebbe* stare un programma; per sapere dove sta davvero servono misure riproducibili. La dispensa [Performance e benchmarking](03-performance-benchmarking.md) copre metriche (time-to-solution, flop/s, banda, latenza, picco contro sostenuto), regole per misure affidabili, profiling con `perf`, picco teorico in doppia precisione e i benchmark HPL, STREAM, HPCG, Graph500 e MLPerf HPC.
