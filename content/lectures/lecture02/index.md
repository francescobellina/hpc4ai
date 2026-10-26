# Architetture dei calcolatori per HPC

Per capire le prestazioni di un programma HPC bisogna considerare insieme il lavoro aritmetico, i dati e l'hardware che li elabora. Questo capitolo introduce i componenti essenziali di un nodo e spiega perché il modo in cui si accede ai dati può limitare il calcolo.

(cpu-e-nodi)=
## CPU, core e nodi

Una **CPU** è il processore installato in un socket. Contiene uno o più **core**: unità capaci di eseguire flussi di istruzioni indipendenti. Il sistema operativo può esporre più **CPU logiche** per core con la tecnologia SMT. Una CPU logica non è un core aggiuntivo: condivide risorse di calcolo con gli altri thread hardware dello stesso core.

Un **processo** è un programma in esecuzione con il proprio spazio di indirizzamento. Un **thread** è un flusso di esecuzione dentro un processo. Più thread dello stesso processo possono condividere la memoria, ma non diventano per questo core o CPU logiche.

Un **nodo** è un computer del cluster: può contenere più CPU, core e memoria RAM. Un cluster collega più nodi tramite una rete e li rende disponibili per calcoli paralleli. Non assumere numero di core, RAM, rete o acceleratori di un sistema specifico senza verificarne la documentazione.

(gerarchia-memoria)=
## Gerarchia della memoria

Il processore lavora su dati che devono essere trasferiti fino alle unità di esecuzione. La memoria è organizzata per bilanciare velocità, capacità e costo:

| Livello | Ruolo | Caratteristica generale |
|---|---|---|
| Registri | Operandi immediati delle istruzioni | Molto piccoli e veloci |
| Cache L1, L2 e L3 | Copie temporanee dei dati usati dal processore | Più vicine e rapide della RAM, ma di capacità minore |
| RAM | Dati e codice attivi | Molto più capiente, ma con accesso più lento |
| Storage | File persistenti | Capiente; non sostituisce la RAM durante il normale accesso alle variabili |

La disposizione concreta delle cache varia tra processori: alcuni livelli sono privati di un core, altri condivisi tra più core. La tabella descrive una gerarchia tipica, non le specifiche di WILSON.

Una **cache line** trasferisce un blocco di byte, non un singolo valore. Quando un programma riusa presto lo stesso dato sfrutta la **località temporale**; quando visita indirizzi vicini sfrutta la **località spaziale**. Per esempio, percorrere in ordine gli elementi contigui di un array tende a usare meglio le linee di cache di accessi casuali o con grandi salti.

(latenza-banda)=
## Latenza, banda e colli di bottiglia

La **latenza** è il tempo necessario per ottenere un dato. La **banda passante** è la quantità di dati trasferibile nell'unità di tempo. Una banda elevata non implica che la risposta alla singola richiesta arrivi con bassa latenza.

Un programma è **memory-bound** quando la velocità è limitata soprattutto dal trasferimento dei dati; è **compute-bound** quando è limitata soprattutto dal calcolo. Lo stesso programma può avere limiti diversi su macchine diverse o in fasi diverse.

L'intensità aritmetica mette in relazione le operazioni e il traffico di memoria:

$$I = \frac{N_{\mathrm{flop}}}{Q} \qquad [\mathrm{flop/byte}],$$

dove $N_{\mathrm{flop}}$ è il numero di operazioni floating-point e $Q$ il numero di byte trasferiti. Il risultato dipende dall'implementazione e dal livello di memoria considerato.

(modello-roofline)=
### Modello Roofline

Se il picco aritmetico è $P_{\max}$ e la banda sostenibile è $B$, il modello Roofline fornisce il limite:

$$P \leq \min(P_{\max}, B I).$$

Il punto di passaggio tra i limiti è la *ridge point*, $I_{\mathrm{ridge}}=P_{\max}/B$. A sinistra del punto il modello indica un limite di banda; a destra indica un limite di calcolo. È un modello, non una previsione né una misura: dipendenze, accessi irregolari, parallelismo insufficiente e overhead possono mantenere il programma sotto il limite.

Un esempio puramente ipotetico usa $P_{\max}=1.5\ \mathrm{Tflop/s}$ e $B=100\ \mathrm{GB/s}$: la ridge point è $15\ \mathrm{flop/byte}$. Questi numeri illustrano il calcolo e non descrivono WILSON.

Il [notebook Roofline](notebooks/performance-models.ipynb) permette di esplorare questo modello con parametri ipotetici. I valori prodotti dal notebook non sono benchmark verificati di un sistema reale.

(memoria-e-topologia)=
## Memoria condivisa, distribuita e NUMA

In un nodo, i thread di uno stesso processo possono accedere allo spazio di memoria condiviso. In un cluster, la RAM di un nodo non è automaticamente accessibile a un processo su un altro nodo: i programmi distribuiti devono trasferire dati attraverso la rete. MPI è una possibile interfaccia per questa comunicazione; il capitolo sul parallelismo ne descrive il modello.

Nei sistemi **NUMA** la memoria è condivisa nello spazio di indirizzi, ma il costo di accesso dipende dalla vicinanza tra core e memoria. Collocare thread e dati senza considerare la topologia può aumentare la latenza o ridurre la banda disponibile.

Acceleratori come le GPU possono fornire molte unità di calcolo e memoria propria. Sono utili quando il problema espone lavoro adatto e il trasferimento dei dati è giustificato. La loro disponibilità e configurazione dipendono dal sistema; questo testo non assume che WILSON ne disponga.

(implicazioni-esercizi)=
## Implicazioni per gli esercizi

Prima di ottimizzare, chiediti dove sono i dati, con quale regolarità vengono visitati e quale risorsa limita la fase misurata. Migliorare la località può ridurre i trasferimenti; aggiungere thread non aiuta se la banda di memoria è già satura. Confronta sempre il modello con misure riproducibili e documenta dimensione del problema, hardware e configurazione usata.

La trattazione è una sintesi rielaborata del [capitolo originale Computing architectures](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/computing-architectures/index.html).
