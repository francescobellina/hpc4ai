# Performance e benchmarking

Un programma può essere corretto e comunque inutilizzabile: troppo lento, troppo
avido di memoria, troppo dipendente da una macchina che non si possiede. Questo
capitolo spiega come si misura la prestazione, come si legge il numero ottenuto e
quali benchmark standard usano i centri di calcolo per confrontare i sistemi.

> I passaggi che completano o spiegano ciò che il materiale del corso dà per noto
> sono marcati *[integrazione]*.

### Notazione

I simboli ricorrenti, dichiarati una volta qui e poi usati senza ripeterli:

| Simbolo | Significato | Dove nasce |
|---|---|---|
| $T$ | tempo impiegato da un calcolo [s] | metriche |
| $B$ | banda di memoria sostenibile [byte/s] | roofline |
| $I$ | intensità operativa di un kernel [flop/byte] | roofline |
| $P_{\text{peak}}$ | prestazione di picco dell'hardware [flop/s] | picco teorico |
| $P_{\max}$ | prestazione massima consentita dal modello roofline [flop/s] | roofline |
| $N$ | lato della matrice densa $N\times N$ di HPL (numero di righe e colonne) | HPL |
| $p$ | numero di processi MPI impegnati in una run | HPL |
| $P$, $Q$ | lati della griglia $P\times Q$ di processi MPI ($p = P\cdot Q$) | HPL |
| $NB$ | lato del blocco $NB\times NB$ in cui è divisa la matrice | HPL |
| $M_{\text{tot}}$ | memoria totale disponibile per il job [byte] | HPL |
| $\beta$ | frazione di $M_{\text{tot}}$ usabile per la matrice | HPL |
| $N_x, N_y, N_z$ | dimensioni della griglia 3D **locale a un processo** in HPCG | HPCG |

Attenzione a non confondere $N$ (lato della matrice densa di HPL) con
$N_xN_yN_z$ (incognite per processo in HPCG): sono problemi diversi.


---

## Perché misurare

Il benchmarking serve a valutare hardware e software in condizioni specificate,
confrontare sistemi con misure controllate e riproducibili, individuare i colli
di bottiglia e guidare l'acquisto di nuovi sistemi.

L'idea da tenere ferma è che un numero da solo non significa nulla. "Questa
macchina fa 1.5 Tflop/s" è un'informazione vuota finché non si dice *su quale
codice, con quale input, con quale configurazione software*. Un benchmark è un
esperimento: ha un protocollo, un campione e un margine di errore; senza questi
tre elementi è solo un aneddoto.

Il valore pratico è doppio. Prima di ottimizzare, il benchmark dice **dove** finisce
il tempo: senza questa informazione si ottimizza la parte sbagliata del codice.
Prima di comprare, dice **quale** macchina conviene per il carico che si farà
davvero, che raramente è il carico del benchmark più pubblicizzato.

---

## Le metriche

### Tempo e flop/s

Il **time-to-solution** è il tempo che l'utente deve aspettare per avere il
risultato: non solo il calcolo, ma anche lettura dell'input, inizializzazione,
checkpoint e scrittura dell'output. È l'unica metrica che l'utente percepisce
direttamente.

I **flop/s** isolano invece il calcolo puro:

$$\text{flop/s} = \frac{\text{operazioni in virgola mobile}}{T},$$

dove $T$ è il tempo impiegato e la precisione va sempre dichiarata (in questo
capitolo: doppia precisione, `double`). Un solver che fa dieci iterazioni al
secondo ma impiega venti minuti a leggere l'input ha un ottimo flop/s e un pessimo
time-to-solution: sono due domande diverse, e la seconda è quella che conta per
chi aspetta.

### Banda e latenza

La **banda di memoria** è il tasso di trasferimento fra CPU e memoria (GB/s); la
**latenza** è il ritardo di una singola comunicazione o di un singolo accesso
(microsecondi sulla rete, nanosecondi in RAM).

Sono cose diverse: la banda è la larghezza dell'autostrada, la latenza è il tempo
al casello. Un codice che fa molte comunicazioni piccole soffre la latenza anche
su una rete larghissima, e comprare più banda non lo aiuta. Questa distinzione
evita l'errore più comune quando si dimensiona un cluster: contare i GB/s e
dimenticare i microsecondi.

### Picco teorico contro prestazione sostenuta

La prestazione di **picco** è il massimo che l'hardware può erogare, dedotto dalle
specifiche (core, frequenza, operazioni per ciclo). La prestazione **sostenuta** è
quella che l'applicazione ottiene davvero.

Il picco è la velocità massima del motore, la sostenuta è la media nel traffico.
Un codice che raggiunge il 10% del picco non è necessariamente scritto male:
potrebbe essere limitato dalla memoria. Per questo il rapporto

$$E = \frac{\text{sostenuta}}{\text{picco}}$$

si interpreta solo dopo aver capito qual è il collo di bottiglia; confrontare il
picco di una macchina con la sostenuta di un'altra è un errore di categoria.

### Intensità operativa e modello roofline *[integrazione]*

Il ponte fra le metriche precedenti è l'**intensità operativa** di un kernel:

$$I = \frac{\text{flop}}{\text{byte trasferiti}}\quad [\text{flop/byte}],$$

e il modello roofline dice che la prestazione massima è

$$P_{\max} = \min\bigl(P_{\text{peak}},\; I \cdot B\bigr),$$

con $B$ banda sostenibile. Il punto di passaggio, $I^{*} = P_{\text{peak}}/B$, si
chiama *ridge point*.

Un esempio con i numeri di un processore attuale: con $B \approx 205$ GB/s e
$P_{\text{peak}} = 768$ GFLOP/s, $I^{*} \approx 3.7$ flop/byte. Un prodotto
matrice-vettore ($I \approx 0.25$) sta a sinistra: è **memory-bound**, e nessuna
ottimizzazione del calcolo lo salverà. Una fattorizzazione LU a blocchi
($I \sim N/3$), cioè la scomposizione $A = LU$ con $L$ triangolare inferiore e $U$
triangolare superiore, sta a destra: è **compute-bound**, lì i flop contano. Tutta
la differenza fra HPL e HPCG nasce da qui.

---

## Misurare in modo affidabile

Cinque regole, in ordine di importanza.

**Prima si valida, poi si cronometra.** Un codice che salta metà delle iterazioni
è rapidissimo. HPL e HPCG stessi accettano un risultato solo se il residuo passa
la soglia: senza validazione il numero non è una prestazione, è il tempo di
esecuzione di qualcosa.

**Si misura il tempo trascorso.** Il tempo CPU sommato su più thread può superare
l'elapsed e con $n$ thread al 100% vale circa $n \cdot$ elapsed. Se è molto
minore, i thread stanno aspettando: I/O, lock, comunicazione o memoria. L'elapsed
resta la misura che conta per l'utente; il rapporto fra i due è un primo
indicatore di quanto il parallelismo stia funzionando.

**Si definisce l'intervallo.** Programma intero o fase selezionata? Setup e I/O
inclusi o esclusi? Due misure con intervalli diversi non sono confrontabili, e lo
scarto può superare l'effetto che si vuole misurare.

**Si ripete.** Almeno tre o cinque run, riportando un valore tipico (mediana o
media) e la sua variabilità (min–max oppure deviazione standard). Su un cluster la
variabilità viene da frequenze turbo, vicini rumorosi, rete e file system: una
differenza del 5% fra due configurazioni, con run che variano del 15%, non è una
differenza.

**Si registra l'ambiente.** Input, compilatore e moduli, hardware, layout di
processi e thread. Un risultato senza questi dati non è riproducibile, quindi non
è un benchmark. Metà del lavoro di misura è tenere questo registro.

---

## Timing e profiling

Il timing risponde a *quanto* dura il programma; il profiling a *dove* va il
tempo. Sono due domande diverse e servono entrambe: il profiling senza timing
ottimizza alla cieca, il timing senza profiling non dice dove intervenire.

Lo strumento standard su Linux è `perf`:

```bash
perf record -e cpu-clock:u -F 99 -g ./program   # campiona a 99 Hz, con call graph
perf report --stdio                              # profilo per funzione
```

`-e cpu-clock:u` campiona solo il tempo utente, `-F 99` fissa la frequenza di
campionamento e `-g` registra lo stack di chiamate. Due accorgimenti: girare su un
nodo di calcolo, non sul login node, e compilare con ottimizzazione e simboli di
debug (`-O2 -g`, meglio con `-fno-omit-frame-pointer`), altrimenti il profilo è
piatto o illeggibile.

Il report distingue due colonne. **Self** conta i campioni caduti dentro la
funzione; **Children** include anche le funzioni da essa chiamate. `main` ha Self
quasi nullo e Children quasi al 100%: non è lei il problema. Si ottimizza guardando
dove Self è alto, cioè dove si fa il lavoro vero.

Le percentuali sono sempre relative alla run in esame. Se si elimina una funzione
che occupava metà del tempo, quella che stava al 30% passa al 60% di una run più
corta: le percentuali si ridistribuiscono a somma 100%. Dopo una modifica si
confrontano quindi i **tempi elapsed**, non i punti percentuali: un guadagno si
misura in secondi.

---

## Il tetto teorico in doppia precisione

Il picco di un nodo si calcola con

$$P_{\text{peak}} = N_{\text{socket}} \cdot N_{\text{core/socket}} \cdot
N_{\text{ops/cycle}} \cdot f_{\text{clock}},$$

dove $N_{\text{socket}}$ è il numero di processori, $N_{\text{core/socket}}$ i core
per processore, $N_{\text{ops/cycle}}$ le operazioni in virgola mobile per ciclo
per core e $f_{\text{clock}}$ la frequenza di clock, tipicamente quella base.

### Esempio: due AMD EPYC 7313

I dati sono 2 socket, 16 core per socket, 3 GHz, e 16 operazioni per ciclo in
doppia precisione, giustificate dalla presenza di **due unità FMA AVX2 da 256
bit** per core, dove FMA sta per *fused multiply-add*. Da dove esce il 16 *[integrazione: il conto che il materiale del
corso non mostra]*:

- AVX2 ha registri da 256 bit, cioè 4 `double`;
- una FMA calcola $a\cdot b + c$: una istruzione, due operazioni (moltiplicazione
  e addizione), quindi $4 \times 2 = 8$ flop;
- due unità FMA per core: $2 \times 8 = 16$ flop per ciclo.

$$\Rightarrow\quad P_{\text{peak}} = 2 \cdot 16 \cdot 16 \cdot 3\cdot 10^{9}
= 1536\ \text{GFLOP/s} \approx 1.5\ \text{TFLOP/s}.$$

Due avvertenze. La prima: quei 16 flop/ciclo si ottengono solo con FMA
indipendenti; ogni FMA ha una latenza di circa quattro cicli, quindi una catena di
dipendenze seriale scende a 4 flop/ciclo e servono più accumulatori indipendenti
(unrolling) per saturare le due unità. La seconda: senza fusione
moltiplicazione-addizione il picco si dimezza. Un controllo di coerenza utile è
il ridge point: 8 canali DDR4-3200 per socket danno circa 205 GB/s, quindi
$1536/410 \approx 3.7$ flop/byte sul nodo a due socket.

### Esercizio: il Raspberry Pi 5

Il procedimento è sempre lo stesso; cambia dove si leggono i dati.

1. `lscpu` riporta modello, core, frequenza e flag ISA:
   ```bash
   lscpu | grep -Ei 'model name|^cpu\(s\)|mhz|flags'
   ```
   Deve comparire `asimddp` (Advanced SIMD double precision): senza quel flag la
   doppia precisione vettoriale non esiste e il conto va rifatto.
2. Si cerca $N_{\text{ops/cycle}}$ del core: è un dato di microarchitettura, non
   lo dice `lscpu`. Per un Cortex-A76 *[integrazione]*: due unità NEON da 128 bit,
   cioè 2 `double` per unità, con FMA → $2 \cdot 2 \cdot 2 = 8$ flop/ciclo.
3. Si applica la formula.

Con 4 core a 2.4 GHz:

$$P_{\text{peak}} = 1 \cdot 4 \cdot 8 \cdot 2.4\cdot10^{9}
= 76.8\ \text{GFLOP/s}.$$

Se la frequenza effettiva è diversa il risultato scala linearmente. Il senso
dell'esercizio non è il numero in sé ma il fatto che senza picco non esiste
efficienza: sul Pi 5, con poca banda e cache piccole, un HPL al 5–10% del picco è
normale, non un fallimento.

---

## Il panorama dei benchmark

Nessun benchmark descrive un sistema, perché ognuno stressa una risorsa diversa.

| Benchmark | Cosa misura | Risorsa dominante |
|---|---|---|
| **HPL** | algebra lineare densa: risolve $Ax=b$ | calcolo |
| **STREAM** | benchmark sintetico: banda di memoria sostenuta | memoria |
| **HPCG** | calcolo sparso: accessi in memoria e comunicazione | memoria e latenza |
| **Graph500** | attraversamento di grafi, carico data-intensive | accessi irregolari |
| **MLPerf HPC** | suite per il machine learning scientifico su HPC | mix calcolo, rete, I/O |

**HPL** misura il massimo flop/s raggiungibile su dati densi e regolari: utile per
la classifica e per verificare che il sistema regga il carico termico. **STREAM**
misura quanto in fretta si spostano i dati, che spesso è il vero limite dei codici
reali. **HPCG** misura un carico sparso e iterativo, rappresentativo di molta
fisica computazionale. **Graph500** misura attraversamenti di grafi, dove conta la
latenza più della banda e la metrica è in TEPS (traversed edges per second, archi
attraversati al secondo); i kernel sono BFS (breadth-first search, visita in
ampiezza) e SSSP (single-source shortest paths, cammini minimi da una sorgente).
**MLPerf HPC** misura pipeline scientifiche con machine learning, quindi
precisione mista, data loading e comunicazione collettiva.

La conseguenza pratica è che un sistema primo in HPL può essere mediocre in HPCG o
in Graph500. Il benchmark giusto dipende dal carico che si vuole far girare, e i
numeri vanno letti insieme.

---

## HPL

### Che cos'è, da dove viene

**LINPACK** è una libreria Fortran per analizzare e risolvere sistemi lineari, da
tempo sostituita da **LAPACK**. Il *benchmark* LINPACK misura la prestazione di un
sistema risolvendo un sistema denso $n \times n$, cioè $Ax=b$. **HPL** è
l'implementazione portabile per memoria distribuita, scritta in C, e la famiglia
LINPACK è alla base della classifica **TOP500**.

La domanda a cui risponde è la più semplice possibile: quanto veloce fai algebra
lineare densa, con dati che stanno in memoria e comunicazione regolare? Il fatto
che sia una domanda semplice spiega sia la fortuna di HPL (confrontabile da
trent'anni su qualsiasi architettura) sia i suoi limiti, che vedremo alla fine.

HPL si compila contro **MPI** (Message Passing Interface, la libreria standard per
comunicare fra processi su nodi diversi) e **BLAS** (Basic Linear Algebra
Subprograms, le routine di algebra lineare di base). Una BLAS ottimizzata per
l'hardware è la norma (OpenBLAS, MKL, BLIS), perché il punteggio dipende più da
quella che dalla CPU. Su WILSON si usa `module spider HPL` per trovare i moduli di
compilatore e MPI richiesti **prima** di caricare HPL. L'eseguibile `xhpl` legge un
file di input di 31 righe, `HPL.dat`, dalla directory corrente.

### I parametri: N, NB, P, Q

| Parametro | Significato | Effetto |
|---|---|---|
| `N` | dimensione della matrice $N\times N$ | più $N$ significa più flop e più memoria |
| `NB` | dimensione del blocco | kernel più grandi e meno overhead, ma più memoria |
| `P`, `Q` | griglia $P\times Q$ di processi MPI | topologia della comunicazione |

Due regole di configurazione. La prima: **`N` multiplo di `NB`** (per esempio
`NB = 192`). La seconda:

$$P \cdot Q \cdot \texttt{OMP\_NUM\_THREADS} = \text{numero di core richiesti},$$

perché $P \times Q$ è il numero di processi MPI e ogni processo può usare più
thread OpenMP (la libreria per parallelizzare con thread dentro un nodo). Se il
prodotto non coincide con i core che il job ottiene, si spreca hardware o si fa
**oversubscription**, cioè si mettono più thread sui core di quanti ce ne siano e
le prestazioni peggiorano invece di migliorare.

La matrice viene divisa in blocchi $NB \times NB$ e distribuita **block-cyclic**
sulla griglia di processi: il blocco di indici $(i,j)$ va al processo
$(i \bmod P,\ j \bmod Q)$. È un mosaico di piastrelle distribuite a giro, come si
danno le carte a un tavolo di $P\cdot Q$ giocatori: ogni processo ottiene una
sotto-griglia regolare di blocchi, distanziati di $P\cdot NB$ righe e $Q\cdot NB$
colonne.

Perché ciclico e non a blocchi: con una distribuzione puramente a blocchi, durante
la fattorizzazione il processo che possiede il pannello corrente lavora da solo
mentre gli altri aspettano (load imbalance). Con la block-cyclic il pannello
attraversa a turno tutti i processi di una riga o colonna e il carico si bilancia.
Una griglia sbilanciata, per esempio $P \times 1$, crea invece un collo di
bottiglia di comunicazione; `NB` troppo piccolo aumenta l'overhead e troppo grande
spreca memoria. Sono i due parametri che spiegano la maggior parte della differenza
fra un HPL al 40% e uno al 70% del picco.

### Quanta memoria serve: scegliere N

La matrice occupa $8N^{2}$ byte, perché ogni `double` pesa 8 byte. Il resto della
memoria serve a pannelli, pivot (gli scambi di righe che rendono stabile la
fattorizzazione) e buffer di broadcast (la copia del pannello inviata a tutti i
processi), quindi si lascia un margine:

$$N = \sqrt{\beta \cdot \frac{M_{\text{tot}}}{\texttt{sizeof(double)}}},
\qquad \beta = 0.8,$$

dove $M_{\text{tot}}$ è la memoria disponibile e $\beta$ la frazione usabile. Il
valore ottenuto si arrotonda **per difetto a un multiplo di `NB`**, ed è questo
arrotondamento che spiega perché i numeri delle configurazioni reali sono un po'
più bassi del valore esatto della formula.

### Tre configurazioni concrete

| Sistema | P × Q | thread | NB | N | memoria matrice | % memoria |
|---|---|---|---|---|---|---|
| WILSON (primo check) | 2 × 2 | 4 | 192 | 12288 | 1.125 GiB | caso piccolo |
| nodo 2×8 core, 64 GiB | 2 × 2 | 4 | 192 | 82560 | 50.8 GiB | 79.4% |
| Raspberry Pi 5, 4 GiB | 1 × 1 | 4 | 192 | 20352 | 3.09 GiB | 77.2% |

I conti, per crederci e per rifarli su un'altra macchina:

- **WILSON**: $12288 = 64 \times 192$ ✓ e $8N^{2} = 8 \cdot 1.5095\cdot10^{8}
  = 1.208\cdot10^{9}$ B $= 1.125$ GiB ✓. Il layout richiede $2\cdot2\cdot4 = 16$
  core.
- **nodo 64 GiB**: la formula dà $N = \sqrt{0.8 \cdot 64\,\text{GiB}/8} = 82898$,
  arrotondato a $82560 = 430\times192$. Allora
  $8N^{2} = 5.453\cdot10^{10}$ B $= 50.8$ GiB, cioè il 79.4% dei 64 GiB:
  coerente con $\beta = 0.8$.
- **Pi 5**: la formula dà $20724$, arrotondato a $20352 = 106\times192$. Allora
  $8N^{2} = 3.314\cdot10^{9}$ B $= 3.09$ GiB, il 77.2% dei 4 GiB.

Il lavoro di una LU è circa $\tfrac{2}{3}N^{3}$ flop *[integrazione]*: da
$1.2\cdot10^{12}$ flop nel caso piccolo di WILSON a $3.8\cdot10^{14}$ sul nodo da
64 GiB, fino ai $5.6\cdot10^{12}$ del Pi 5, che a pochi GFLOP/s significa
decine di minuti. Questi conti spiegano la maggior parte dei fallimenti: con $N$
troppo grande si esaurisce la memoria a metà fattorizzazione, con $N$ troppo
piccolo domina la comunicazione e il flop/s crolla. Da qui la regola di validare
sempre il caso piccolo prima di aumentare $N$.

### Strong scaling e memory scaling

Sia $p = P\cdot Q$ il numero di processi MPI, con il numero di thread per processo
fissato.
Ci sono due modi di crescere.

Nello **strong scaling** si tiene $N$ fisso e si aumenta $p$: il problema è sempre
lo stesso e si vuole solo andare più veloci. L'efficienza prima o poi crolla,
perché i tempi di comunicazione non diminuiscono con $p$.

Nel **memory scaling** si aumenta $N$ insieme a $p$, in modo che la memoria per
processo resti circa costante:

$$\text{memoria per processo} = \frac{8N^{2}}{p} \approx \text{costante},
\qquad \text{lavoro per processo} = \frac{\tfrac{2}{3}N^{3}}{p} \propto \sqrt{p}.$$

La seconda relazione si ricava in due righe: se $N \propto p^{1/2}$ allora
$N^{3} \propto p^{3/2}$ e dividendo per $p$ resta $p^{1/2}$.

Qui sta il punto concettuale: **questo non è weak scaling classico**. Il weak
scaling canonico mantiene costante il *lavoro* per processo, cioè $N \propto
p^{1/3}$. HPL non può farlo, perché memoria e lavoro scalano come $N^{2}$ e
$N^{3}$: tenere costante la memoria lascia crescere il lavoro. La conseguenza
pratica è che le run memory-scaled più grandi possono durare molto più a lungo, e
il costo va stimato da run piccole invece di scoprirlo alla fine.

### I limiti

Un solo numero non descrive un sistema completo: la TOP500 riduce CPU, GPU, rete,
I/O e memoria a un flop/s. Inoltre HPL ha intensità operativa alta, con
$\mathcal{O}(N^{3})$ calcolo su $\mathcal{O}(N^{2})$ memoria: è compute-bound per
costruzione e quindi poco rappresentativo dei carichi scientifici memory-bound.

Il picco richiede una grande frazione della memoria di sistema, perché $N$ deve
essere grande: GB o TB di RAM solo per la matrice. Sui sistemi più grandi una run
può durare giorni, e la campagna di tuning di $N$, `NB`, $P$ e $Q$ può essere più
lunga della run stessa. Infine il punteggio dipende dal software: una BLAS
migliore o un compilatore migliore lo cambiano, il che è utile per valutare
l'ecosistema ma pericoloso se lo si legge come capacità pura dell'hardware.

---

## HPCG

### Perché esiste

HPCG risolve un sistema lineare **sparso** (una matrice in cui quasi tutti gli
elementi sono nulli), derivante da un'equazione di Laplace 3D discretizzata con uno
**stencil a 27 punti**: per aggiornare il valore in un nodo della griglia si usano i
valori dei 26 nodi vicini più il nodo stesso. Il metodo è il **gradiente
coniugato**, un algoritmo iterativo che appartiene alla famiglia dei **sottospazi
di Krylov**, cioè dei sottospazi generati applicando ripetutamente la matrice al
residuo. È progettato per complementare HPL: il pattern di accesso alla memoria è
completamente diverso, e molto più realistico. Anche top500.org pubblica una lista
HPCG accanto a quella HPL.

L'intuizione è che HPL premia chi ha unità FMA veloci, HPCG premia chi sa
alimentarle di dati: è il test del traffico accanto al test del motore.

### Il problema e il pattern di accesso *[integrazione]*

$$\nabla^{2} u = f \;\;\longrightarrow\;\;
\sum_{k\in\{-1,0,1\}^{3}} c_k\, u_{i+k} = f_i .$$

I 27 coefficienti per riga corrispondono al nodo stesso, ai 6 vicini lungo gli assi
e ai 20 vicini sulle diagonali. La matrice è sparsa, simmetrica e definita positiva,
e il gradiente coniugato costruisce la soluzione nel sottospazio
$\mathcal{K}_m = \mathrm{span}\{r_0, Ar_0, \dots, A^{m-1}r_0\}$, dove $r_0 = b -
Ax_0$ è il residuo iniziale. Ogni iterazione
costa un prodotto matrice-vettore, che legge 27 coefficienti per circa 2 flop ed è
quindi memory-bound, più due riduzioni globali, che sono comunicazione collettiva
e quindi latenza.

Il contrasto con HPL è netto: HPL legge $\mathcal{O}(N^{2})$ dati e li riusa
molto, HPCG legge dati sparsi e li riusa poco. Banda e latenza diventano il
limite, e il flop/s scende all'ordine dell'1–5% del picco.

### `hpcg.dat` e il tempo fisso

```text
HPCG benchmark input file
Sandia National Laboratories; University of Tennessee, Knoxville
104 104 104
60
```

Le prime due righe sono libere e servono solo come commento. La terza contiene
`NX NY NZ`, la dimensione del problema **locale a ciascun processo** MPI; la
quarta la durata in secondi, **1800 s** per i risultati ufficiali e **60 s** per un
test.

Il tempo è quindi fissato dall'input, e si confrontano i **flop/s validati**, non
il tempo: se due sistemi girano per 60 s, il più veloce ha fatto più iterazioni, non
è arrivato prima. Con durata fissa i flop/s misurano il throughput su un lavoro
validato, e restano confrontabili fra macchine diverse anche con dimensioni di
problema diverse.

Poiché la dimensione è locale per processo, a parità di `NX NY NZ` raddoppiare i
processi raddoppia il problema globale: è uno scenario di **weak scaling per
costruzione**, con lavoro e memoria per processo costanti. I vincoli sono
$N_x, N_y, N_z \ge 16$ e multipli di 8, per allineamento SIMD (l'unità che
elabora più numeri per istruzione) e per le cache.

### La regola del 25% della memoria

La memoria usata è circa

$$M \approx 896\ \text{B} \times N_x N_y N_z \quad \text{per processo},$$

e il target è almeno il **25% della memoria di sistema**. Due esempi:

| Dimensione locale | Memoria per processo |
|---|---|
| $104 \times 104 \times 104$ | $\approx 0.94$ GiB |
| $160 \times 160 \times 160$ | $\approx 3.42$ GiB |

Verifica: $104^{3} = 1{,}124{,}864$ incognite, per $896$ B fa
$1.008\cdot10^{9}$ B $= 0.94$ GiB; $160^{3} = 4{,}096{,}000$ incognite fanno
$3.670\cdot10^{9}$ B $= 3.42$ GiB. La costante 896 B *[integrazione]* tiene conto
dei 27 coefficienti (216 B), degli indici, dei vettori di lavoro e delle strutture
del **multigrid**, la tecnica di precondizionamento che risolve il problema su
griglie via via più grossolane per accelerare la convergenza.

Perché solo un quarto della memoria? Perché HPCG non fa blocking aggressivo e non
ne ha bisogno: lasciarne libero il 75% evita swap e pressione sulle cache. Un HPCG
dimensionato come HPL avrebbe una dimensione locale enorme, un set di lavoro che
non entra in cache e prestazioni falsate verso il basso, quindi il 25% è la
convenzione che rende i numeri confrontabili.

---

## Microbenchmark e miniapplication

Sotto i grandi benchmark stanno strumenti più piccoli, utili in fasi diverse del
lavoro.

I **microbenchmark** catturano una sola caratteristica di prestazione. Gli OSU
Micro-Benchmarks, per esempio, misurano latenza e banda delle primitive di
comunicazione, comprese quelle MPI: se so che un `MPI_Allreduce` su 64 rank costa
20 µs, allora 10 000 riduzioni globali costano 0.2 s di pura comunicazione. Sono
il cronometro sul singolo gesto, e si usano per costruire un modello di costo,
capire se il collo di bottiglia è la rete o il calcolo, o confrontare due reti
prima di rifare la run vera.

Le **miniapplication** sono versioni ridotte di applicazioni scientifiche reali,
con codice collaudato, che riportano il time-to-solution su una dimensione
standard: **miniFE** per gli elementi finiti, **Grid** per il lattice QCD. Sono il
quarto d'ora di partita con le stesse regole del campionato: mantengono
allocazione, pattern di accesso, comunicazione e struttura del solver, ma girano in
pochi minuti. Servono a valutare un sistema su un carico quasi reale senza portare
a scala l'applicazione vera, e a decidere quale risorsa migliorare prima di
comprare.

---

## Tabella riassuntiva

| Benchmark | Cosa misura | Collo di bottiglia che evidenzia |
|---|---|---|
| **HPL** | flop/s su LU densa $N\times N$ | calcolo FP, qualità delle BLAS, griglia $P\times Q$ |
| **STREAM** | banda di memoria sostenuta | banda, canali di memoria, NUMA |
| **HPCG** | flop/s validati su CG con stencil 27 punti | banda e latenza di memoria, riduzioni globali |
| **Graph500** | TEPS su BFS e SSSP | latenza e accessi irregolari, scalabilità della rete |
| **MLPerf HPC** | throughput su training scientifico a scala | precisione, I/O dei dati, comunicazione collettiva |
| **OSU microbench** | latenza e banda di singole primitive MPI | rete, implementazione MPI, topologia |
| **miniFE, Grid** | time-to-solution su carico FEM e QCD realistico | comportamento end-to-end memory-bound |

Regola operativa: **HPL alto e HPCG alto** indicano una macchina bilanciata;
**HPL alto e HPCG basso** troppi pochi byte per flop; **HPCG alto e HPL basso**
buona banda ma calcolo vettoriale debole.

---

## Autoverifica

**Perché il picco teorico non è la prestazione?**
Perché richiede FMA indipendenti e dati in cache a ogni ciclo. Un codice
memory-bound è limitato da $I\cdot B$, non dai flop. Il rapporto sostenuta/picco
si interpreta solo dopo aver identificato il collo di bottiglia.

**Tempo trascorso contro tempo CPU: cosa indica il loro rapporto?**
L'elapsed è il tempo reale, il tempo CPU è la somma su tutti i thread. Un rapporto
vicino al numero di thread indica parallelismo effettivo; molto minore indica
attese per I/O, lock, comunicazione o memoria.

**Perché in HPL si sceglie $N = \sqrt{\beta M/8}$ con $\beta = 0.8$?**
La matrice occupa $8N^{2}$ byte. Il 20% lasciato libero serve a pannelli, pivot e
buffer di broadcast; con $N$ più grande si esaurisce la memoria a metà
fattorizzazione.

**Differenza fra scaling a memoria costante e weak scaling classico?**
Nel primo $N \propto p^{1/2}$: la memoria per processo resta costante e il lavoro
per processo cresce come $\sqrt{p}$. Nel weak scaling classico $N \propto p^{1/3}$
e il lavoro per processo resta costante. HPL non può fare il secondo perché
memoria e lavoro scalano come $N^{2}$ e $N^{3}$.

**Perché HPCG dà numeri molto più bassi di HPL, e perché serve comunque?**
HPCG è memory-bound: 27 coefficienti per prodotto matrice-vettore, riduzioni
globali a ogni iterazione, set di lavoro che non entra in cache. Misura il carico
tipico di molta fisica computazionale, che HPL non rappresenta: i due numeri
insieme descrivono il sistema, uno da solo no.
