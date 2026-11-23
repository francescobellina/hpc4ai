# Esercitazione 3 — Tiny stories, many threads

:::{note} Consegna
I modelli linguistici generano il testo **un token alla volta**: ogni nuovo token
richiede un forward pass sull'intera rete, e il token prodotto diventa l'input del
passo successivo. L'esercizio usa [`llama2.c`](https://github.com/karpathy/llama2.c),
l'inferenza completa dell'architettura Llama 2 in un solo file C, con tre modelli
piccoli (15, 42 e 110 milioni di parametri) addestrati su
[TinyStories](https://arxiv.org/abs/2305.07759): continuano l'inizio di una storia,
ma non rispondono a domande.

- **Seriale** — misurare la velocità di generazione dei tre modelli e trovare dove il
  programma passa il tempo (per esempio con `gprof` o `perf`). Per ogni modello,
  stimare quanti dati il processore legge dalla memoria per generare un token e
  confrontare il traffico risultante con la banda del nodo.
- **OpenMP** — parallelizzare il forward pass partendo dalla funzione che domina il
  tempo, poi decidere se conviene parallelizzare anche altre parti. Verificare che,
  con decodifica greedy, il programma parallelo generi **esattamente lo stesso
  testo** del seriale.
- **Scaling** — misurare i token al secondo in funzione del numero di thread per i
  tre modelli su un nodo, con speedup ed efficienza rispetto al programma seriale.
  I tre modelli scalano allo stesso modo? Convertire la velocità in una **banda di
  memoria effettiva** con la stima del traffico e usarla per spiegare i risultati.
  Per ogni misura riportare modello, numero di token generati, disposizione dei
  thread e tipo di nodo.

**(Optional)** Generare una storia per ogni riga di `prompts.txt`, prima in seriale e
poi con MPI (assegnazione statica e dinamica dei prompt), misurando throughput e
sbilanciamento del carico.
:::

:::{seealso} Teoria di riferimento
- **1. Architetture** — {ref}`Latenza, banda e colli di bottiglia <latenza-banda>`
- **1. Architetture** — {ref}`Memoria condivisa, distribuita e NUMA <memoria-e-topologia>`
- **1. Architetture** — {ref}`Modello Roofline <modello-roofline>`
- **2. Calcolo parallelo** — {ref}`Prestazioni e scalabilità <prestazioni-scalabilita>` e {ref}`legge di Amdahl <t-amdahl>`
- **3. Performance e benchmarking** — {ref}`Timing e profiling <t-timing-profiling>`
- **4. Gestione delle risorse** — {ref}`Disposizione, affinità e Slurm <disposizione-e-slurm>`
- **5. OpenMP** — {ref}`Fork-join, direttive e clausole <t-openmp-forkjoin>`
:::

:::{tip} L'esercizio in breve
**Cosa vogliamo sapere.** Per scrivere un token il programma moltiplica ogni matrice
di pesi del modello per un vettore: legge tutti i pesi, una volta per token, e fa
due operazioni (una moltiplicazione e una somma) per ogni peso letto. Il lavoro per
token è quindi fisso e proporzionale alla dimensione del modello. Con $p$ thread
ogni thread calcola una parte delle righe. Nel caso ideale la velocità cresce come
$p$, finché i thread insieme chiedono più dati di quanti la memoria del nodo ne
possa dare: da lì in poi la velocità si ferma a (banda del nodo) / (byte per token).

**Cosa abbiamo trovato.** Il testo è identico al seriale in tutti i 92 run paralleli.
Il seriale **non** è limitato dalla memoria: legge i pesi a 3.4 GB/s per tutti e tre
i modelli, un quarto di quello che un solo core può ottenere (12.7 GB/s con triad).
Con 16 thread lo speedup è 5.2 (15M), 6.5 (42M) e 7.1 (110M): scala meglio il
modello più grande, perché ogni regione parallela ha più lavoro. Anche a 16 thread
la banda effettiva resta sotto la metà di quella del nodo (24 contro 51 GB/s): lo
scaling si ferma prima di arrivare al limite della memoria.
:::

## Parametri

| Parametro | Valore |
|---|---|
| Programma e modelli | `run.c` del corso (`/srv/data/wilson/project/hpc4ai/exercises/tiny_stories/`, SHA256 `2eebe23b…`), `stories15M.bin`, `stories42M.bin`, `stories110M.bin` letti dalla cartella condivisa, `tokenizer.bin` copiato |
| Generazione | prompt `"Once upon a time"`, `-t 0` (greedy), `-n 256` (massimo di passi); precisione `float32` come nel programma |
| Token generati | la storia finisce prima di 256 passi con il token di fine sequenza: 222 passi per il 15M e 243 per il 110M (chiamate a `forward` nel profilo); il 42M non è stato contato. Il programma divide per i passi meno uno, perché il timer parte dopo il primo |
| Compilazione | `GCC/13.2.0`; seriale `gcc -O3`; OpenMP `gcc -O3 -fopenmp`; profilo `-O3 -pg` e `-O3 -fno-inline -pg`; triad `gcc -O3 -fopenmp` |
| Allocazione | partizione `wilson`, `--constraint=sandy_bridge`, 1 nodo `--exclusive --mem=0`, `--cpus-per-task=16 --hint=nomultithread` |
| Nodi | baseline: `wnode01` (job `61832`); OpenMP: `wnode04` (job `62659`). Entrambi hanno la feature `sandy_bridge`; `lscpu` è stato stampato solo su `wnode01`: 2 × Intel Xeon E5-2650 @ 2.00 GHz (massimo 2.8 GHz), 8 core per socket, 2 hardware thread per core, L3 20 MiB per socket (40 MiB in tutto), 2 nodi NUMA (CPU 0–7 e 8–15 sono i core fisici dei due socket) |
| Run seriali | `srun --ntasks=1 --cpus-per-task=1 --cpu-bind=cores ./run …`, 3 ripetizioni per modello |
| Run OpenMP | `OMP_NUM_THREADS` = 1, 2, 4, 8, 16, `OMP_PLACES=cores`, `OMP_PROC_BIND=spread`, `srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores`, 3 ripetizioni per punto; in più 1 run con `OMP_PROC_BIND=close` a 4 e 8 thread (110M) |
| Banda del nodo | `triad.c` (kernel triad di STREAM, 3 array da $4 \times 10^7$ `double`, il migliore di 10 ripetizioni, byte contati come STREAM): da 1 a 16 thread `spread` su `wnode01`, 4 e 8 thread `close` su `wnode04` |

## Implementazione

**In breve.** Il profilo dice che quasi tutto il tempo è in `matmul`, il prodotto
matrice per vettore. Ogni riga del risultato è un prodotto scalare indipendente
dagli altri, quindi basta dividere le righe fra i thread. Il secondo candidato è il
ciclo sulle teste dell'attenzione, anch'esse indipendenti. Ci sono due versioni,
così si vede quanto vale il secondo passo.

| Programma | Differenza da `run.c` | SHA256 |
|---|---|---|
| `run_omp_mm.c` | `#pragma omp parallel for` su `matmul` | `0aedec5b…` |
| `run_omp.c` | in più `#pragma omp parallel for` sul ciclo delle teste in `forward` | `1876f69f…` |

```c
void matmul(float* xout, float* x, float* w, int n, int d) {
    // W (d,n) @ x (n,) -> xout (d,)
    int i;
    #pragma omp parallel for private(i)
    for (i = 0; i < d; i++) {          // ogni thread calcola righe diverse di xout
        float val = 0.0f;
        for (int j = 0; j < n; j++) {  // il prodotto scalare resta di un solo thread
            val += w[i * n + j] * x[j];
        }
        xout[i] = val;
    }
}
```

Nel ciclo delle teste ogni testa scrive solo la sua parte di `s->att` e di `s->xb`,
quindi anche lì non ci sono scritture condivise:

```c
int h;
#pragma omp parallel for private(h)
for (h = 0; h < p->n_heads; h++) {
    float* q = s->q + h * head_size;      // query della testa h
    float* att = s->att + h * p->seq_len; // punteggi della testa h
    ...                                   // prodotti q·k, softmax, somma pesata dei v
}
```

Gli altri pezzi del forward pass (`rmsnorm`, RoPE, residui, SwiGLU) sono cicli
corti su vettori di lunghezza `dim` o `hidden_dim`. Nel profilo senza inlining
`rmsnorm` sta sotto lo 0.3%, e tutto il resto di `forward`, attenzione compresa,
è l'1.6–2.3% del tempo (tabella {numref}`tab-es03-seriale`). Questi cicli non sono
stati parallelizzati: hanno troppo poco lavoro per ripagare un'altra regione
parallela. In ogni forward
pass `run_omp_mm` apre $7L + 1$ regioni parallele (7 matrici per layer e il
classificatore) e `run_omp` $8L + 1$, con $L$ numero di layer.

Tutto il lavoro su WILSON passa da [`codes/exec3/es03.sh`](../../codes/exec3/README.md):

```bash
bash -l es03.sh setup     # copia i file del corso, compila, job di baseline (seriale, profilo, triad)
bash -l es03.sh omp       # compila run_omp e run_omp_mm, prova breve, job OpenMP (omp_job.sh)
bash -l es03.sh collect   # sorgenti, output dei job, testi e sacct in un solo log
```

Il job OpenMP lancia ogni misura così, con lo stesso binario e cambiando solo
`OMP_NUM_THREADS`:

```bash
OMP_NUM_THREADS=$T OMP_PLACES=cores OMP_PROC_BIND=spread \
    srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
    ./run_omp "$DATA/stories$m.bin" -t 0 -n 256 -i "Once upon a time" > o.txt 2> e.txt
cmp -s o.txt "out_${m}_r1.txt" && echo identico || echo DIVERSO
```

Con `OMP_PLACES=cores` e `spread` i thread si distribuiscono sui due socket (con 2
thread, uno per socket); con `close` riempiono prima il socket 0. La disposizione
non è stata stampata con `--cpu-bind=verbose`, ma la banda di triad la conferma: con
`close` a 4 e 8 thread si ferma a 25.9 e 25.6 GB/s, circa metà dei 44.7 e 51.9
GB/s di `spread`, cioè un solo socket.

## Procedura di validazione

- **Decodifica deterministica.** Con `-t 0` il programma sceglie sempre il token più
  probabile. Le 3 ripetizioni seriali di ogni modello danno lo stesso testo (`cmp`
  nel job `61832`). Il testo della prima ripetizione, `out_<modello>_r1.txt`, è il
  riferimento.
- **Stesso testo in parallelo.** Ogni run del job `62659` confronta il proprio testo
  con il riferimento (`cmp`): 92 run su 92 sono identici (90 di scaling e 2 con
  `close`), come anche i 2 run del profilo senza inlining.
- **Perché è identico bit per bit.** OpenMP divide le righe di `matmul`, non le somme
  dentro una riga: ogni prodotto scalare è calcolato da un solo thread, con le
  somme nello stesso ordine del seriale, e lo stesso vale per ogni testa. Se si
  parallelizzasse il ciclo interno con una `reduction`, l'ordine delle somme in
  virgola mobile cambierebbe, e con esso, prima o poi, qualche token.
- **Stato del job.** Tutti i 96 step del job risultano `COMPLETED 0:0` e il file
  `.err` è vuoto. `sacct` segna il job come `FAILED 1:0` per un dettaglio dello
  script: l'ultima riga di `omp_job.sh`, `grep -c DIVERSO scaling.txt | sed …`, non
  trova righe `DIVERSO`, quindi `grep` esce con codice 1, e con `set -o pipefail`
  quel codice diventa l'esito dello script. Il `FAILED` dice cioè che nessun testo è
  diverso. Lo script è lasciato com'è, perché è quello che ha prodotto le misure.

## Risultati e plot

Log completi:
{download}`collect_20261123_100859.txt <../../../results/es03/collect_20261123_100859.txt>`
(sorgenti, script, output dei due job, testi generati, `sacct`) e
{download}`omp_20261123_095117.txt <../../../results/es03/omp_20261123_095117.txt>`
(compilazione delle versioni OpenMP e invio del job). Tabelle e figure sono prodotte
da [`codes/exec3/analyze_es03.py`](../../codes/exec3/README.md):

```bash
.venv/bin/python codes/exec3/analyze_es03.py results/es03/collect_20261123_100859.txt
```

### 1. Velocità seriale e profilo

**Idea.** Prima di parallelizzare, misurare quanto va veloce il programma del corso e
dove passa il tempo: la funzione in cima al profilo è quella da parallelizzare.

:::{table} Programma seriale (`run.c`, `gcc -O3`, 1 core): velocità e profilo `gprof`.
:name: tab-es03-seriale

| Modello | tok/s (3 run, `wnode01`) | Media | `gprof -O3`: `forward` | `gprof -O3 -fno-inline`: `matmul` | `forward` (self) | altre funzioni | tok/s con `-fno-inline -pg` (`wnode04`) |
|---|---|---|---|---|---|---|---|
| 15M | 58.13 / 58.68 / 58.68 | 58.50 | 99.48% | 96.85% | 1.57% | 1.58% | 58.01 |
| 42M | 20.68 / 20.77 / 20.68 | 20.71 | — | — | — | — | — |
| 110M | 7.81 / 7.82 / 7.81 | 7.81 | 99.81% | 97.61% | 2.26% | 0.13% | 7.79 |
:::

Il primo profilo (`-O3 -pg`) attribuisce il 99.5–99.8% del tempo a `forward`, e
anche `perf` sul 110M dà il 99.3% a `forward`. Con `-O3` il compilatore copia
`matmul` dentro `forward` (inlining), quindi nel profilo le due funzioni non si
distinguono. Il secondo profilo, compilato con `-fno-inline`, le separa: `matmul`
prende il 96.9% (15M) e il 97.6% (110M) del tempo, con 43 e 85 chiamate per token,
cioè $7L + 1$. Il binario senza inlining va alla stessa velocità di quello normale
(58.01 contro 58.50 tok/s, 7.79 contro 7.81): il profilo descrive quindi lo stesso
programma. Le ripetizioni differiscono meno dell'1%.

### 2. Traffico di memoria per token

**Idea.** A ogni token `matmul` legge ogni peso una volta. Se i pesi non stanno in
cache, i byte letti dalla memoria per token sono circa la dimensione dei pesi, e
$\text{banda effettiva} = \text{tok/s} \times \text{byte per token}$.

I byte letti per token si ricavano dalla configurazione nell'intestazione di ogni
`.bin` (stampata da `config.c`) e dall'ordine dei pesi in `memory_map_weights` di
`run.c`. La somma dei blocchi più i 28 byte dell'intestazione ridà esattamente la
dimensione del file per tutti e tre i modelli. Ogni token legge tutte le matrici dei
layer, i pesi di `rmsnorm`, il classificatore e una riga della tabella degli
embedding. In questi modelli il classificatore *è* la tabella degli embedding
(`vocab_size` positivo, pesi condivisi), letta per intero dall'ultima `matmul`. Non
legge le vecchie tabelle `freq_cis` del file (0.05–0.26 MB).

:::{table} Configurazione dei modelli (da `config.c`, job `62659`) e byte di pesi letti per token (`float32`).
:name: tab-es03-traffico

| Modello | `dim` | `hidden_dim` | Layer | Teste | Vocabolario | `seq_len` | File (byte) | Pesi letti per token | di cui classificatore | Key/value letti al passo 128 |
|---|---|---|---|---|---|---|---|---|---|---|
| 15M | 288 | 768 | 6 | 6 | 32000 | 256 | 60 816 028 | 60.77 MB | 36.9 MB (61%) | 1.78 MB |
| 42M | 512 | 1376 | 8 | 8 | 32000 | 1024 | 167 020 572 | 166.76 MB | 65.5 MB (39%) | 4.23 MB |
| 110M | 768 | 2048 | 12 | 12 | 32000 | 1024 | 438 381 596 | 438.12 MB | 98.3 MB (22%) | 9.51 MB |
:::

- **I pesi non stanno in cache.** Anche il modello più piccolo (60.8 MB) è più grande
  della L3 dell'intero nodo (40 MiB = 41.9 MB), quindi i pesi vanno riletti dalla
  memoria a ogni token. Per il 15M una parte potrebbe restare in cache fra un token
  e l'altro: in quel caso il traffico vero verso la DRAM è un po' minore della stima.
- **La key/value cache conta poco.** L'attenzione rilegge anche le key e i value dei
  passi precedenti: al passo 128 sono 1.8, 4.2 e 9.5 MB, il 2–3% dei pesi. La stima
  usa solo i pesi.

:::{table} Banda effettiva del programma seriale e banda del nodo misurata con triad (`wnode01`).
:name: tab-es03-banda-seriale

| | 15M | 42M | 110M | triad, 1 thread | triad, 16 thread |
|---|---|---|---|---|---|
| GB/s | 3.55 | 3.45 | 3.42 | 12.65 | 51.40 |
:::

Il seriale legge i pesi a circa 3.4–3.6 GB/s per tutti e tre i modelli: il 27–28%
di quello che un solo core ottiene con triad e il 7% della banda del nodo. Il programma
seriale quindi non è limitato dalla memoria: sul perché, vedi il commento 1.

### 3. Scaling con OpenMP

**Idea.** Lo stesso testo con più thread. Speedup $S_p = (\text{tok/s})_p /
(\text{tok/s})_\text{seriale}$ ed efficienza $E_p = S_p / p$, con il seriale della
tabella {numref}`tab-es03-seriale`. Il rapporto fra tok/s è uguale al rapporto fra
i tempi perché tutti i run dello stesso modello generano lo stesso testo, quindi lo
stesso numero di token.

:::{table} Scaling di `run_omp` (matmul + teste) e `run_omp_mm` (solo matmul) su `wnode04`, `spread`, media di 3 run. La dispersione (max − min) / media è sotto l'1.3%, tranne il 15M a 16 thread (2.1–2.5%).
:name: tab-es03-scaling

| Modello | $p$ | `run_omp` tok/s | $S_p$ | $E_p$ | `run_omp_mm` tok/s | $S_p$ | $E_p$ |
|---|---|---|---|---|---|---|---|
| 15M | 1 | 56.39 | 0.96 | 0.96 | 56.38 | 0.96 | 0.96 |
| 15M | 2 | 105.07 | 1.80 | 0.90 | 104.11 | 1.78 | 0.89 |
| 15M | 4 | 192.90 | 3.30 | 0.82 | 186.45 | 3.19 | 0.80 |
| 15M | 8 | 287.64 | 4.92 | 0.61 | 283.46 | 4.85 | 0.61 |
| 15M | 16 | 304.16 | 5.20 | 0.32 | 292.35 | 5.00 | 0.31 |
| 42M | 1 | 20.23 | 0.98 | 0.98 | 20.24 | 0.98 | 0.98 |
| 42M | 2 | 38.01 | 1.84 | 0.92 | 37.62 | 1.82 | 0.91 |
| 42M | 4 | 71.99 | 3.48 | 0.87 | 69.50 | 3.36 | 0.84 |
| 42M | 8 | 112.38 | 5.43 | 0.68 | 107.67 | 5.20 | 0.65 |
| 42M | 16 | 135.18 | 6.53 | 0.41 | 127.85 | 6.17 | 0.39 |
| 110M | 1 | 7.67 | 0.98 | 0.98 | 7.68 | 0.98 | 0.98 |
| 110M | 2 | 14.47 | 1.85 | 0.93 | 14.23 | 1.82 | 0.91 |
| 110M | 4 | 27.62 | 3.53 | 0.88 | 26.34 | 3.37 | 0.84 |
| 110M | 8 | 45.13 | 5.78 | 0.72 | 40.64 | 5.20 | 0.65 |
| 110M | 16 | 55.54 | 7.11 | 0.44 | 49.50 | 6.34 | 0.40 |
:::

```{figure} figures/es03-scaling.png
:name: fig-es03-scaling
:width: 100%

Sinistra: token al secondo contro numero di thread (assi logaritmici). Destra:
speedup rispetto al programma seriale `run.c` (job `61832`), con la retta ideale
$S_p = p$. Linee piene e cerchi: `run_omp`; linee tratteggiate e quadrati:
`run_omp_mm`. Media di 3 run per punto su `wnode04`, `OMP_PLACES=cores`,
`OMP_PROC_BIND=spread`.
```

- **I tre modelli non scalano allo stesso modo.** Fino a 4 thread le curve sono quasi
  sovrapposte ($E_4$ fra 0.80 e 0.88), poi si separano: a 16 thread lo speedup è 5.2
  per il 15M, 6.5 per il 42M e 7.1 per il 110M. Il 15M quasi non guadagna da 8 a 16
  thread (+5.7%).
- **Con 1 thread** il programma OpenMP è dall'1.8% al 3.6% più lento del seriale, di
  più per il modello piccolo. La causa non è stata isolata: in parte è il costo delle
  regioni parallele, che ci sono anche con 1 thread, in parte forse la differenza fra
  `wnode01` e `wnode04`. Il profilo su `wnode04` (58.01 e 7.79 tok/s) suggerisce
  però che i due nodi vadano alla stessa velocità.
- **Parallelizzare anche le teste** fa guadagnare a 16 thread il 4% (15M), il 6%
  (42M) e il 12% (110M) rispetto alla sola `matmul`. È poco perché l'attenzione è
  al più l'1.6–2.3% del tempo seriale (il tempo proprio di `forward`, che la
  comprende). Diventa visibile perché quella parte, rimasta
  seriale, pesa sempre di più quando il resto accelera.

### 4. Banda effettiva e limite della memoria

**Idea.** Se lo scaling si fermasse per la banda di memoria, a 16 thread la banda
effettiva dovrebbe arrivare vicino a quella del nodo misurata con triad (51 GB/s).

```{figure} figures/es03-banda.png
:name: fig-es03-banda
:width: 100%

Banda effettiva di `run_omp` (tok/s × pesi letti per token, tabella
{numref}`tab-es03-traffico`) contro il numero di thread, confrontata con la banda
triad del nodo. Rombi vuoti: triad `spread` su `wnode01`; rombi pieni: triad
`close` su `wnode04`. Cerchi vuoti: `run_omp` 110M con `close` (1 run). La banda
effettiva è un limite inferiore del traffico verso la memoria, perché trascura key,
value e attivazioni (2–3%).
```

:::{table} Banda effettiva di `run_omp` (GB/s), in totale e per thread.
:name: tab-es03-banda

| $p$ | 15M | 42M | 110M | 110M per thread | triad `spread` (`wnode01`) | triad `close` (`wnode04`) |
|---|---|---|---|---|---|---|
| 1 | 3.4 | 3.4 | 3.4 | 3.36 | 12.65 | — |
| 2 | 6.4 | 6.3 | 6.3 | 3.17 | 26.28 | — |
| 4 | 11.7 | 12.0 | 12.1 | 3.02 | 44.68 | 25.91 |
| 8 | 17.5 | 18.7 | 19.8 | 2.47 | 51.88 | 25.64 |
| 16 | 18.5 | 22.5 | 24.3 | 1.52 | 51.40 | — |
:::

- **La memoria non è satura.** A 16 thread il 110M legge 24.3 GB/s, il 47% della
  banda triad del nodo; il 15M si ferma a 18.5 GB/s.
- **Ogni thread va più piano quando sono tanti**: da 3.4 GB/s per thread con 1 thread a
  2.5 con 8 e 1.5 con 16 (110M).
- **`close` contro `spread` (110M, 1 run ciascuno).** Con 4 thread `close` fa 26.61
  tok/s contro 27.62 di `spread` (−3.7%). Con 8 thread fa 47.27 contro 45.13
  (+4.7%), cioè 20.7 GB/s, l'81% dei 25.6 GB/s che triad ottiene con 8 thread
  `close` sullo stesso socket. Con 8 thread su un solo socket, quindi con metà
  della banda disponibile, il programma va *più* veloce che con i thread sparsi su
  due socket: anche questo dice che a 8 thread il limite non è la banda.

## Commenti

1. **Perché il seriale non è limitato dalla memoria.** Il seriale legge i pesi a
   3.4–3.6 GB/s per tutti e tre i modelli, contro i 12.65 GB/s che un core ottiene
   con triad. Il limite sembra il ciclo interno di `matmul`, `val += w[i*n+j] *
   x[j]`. Senza opzioni come `-ffast-math`, il compilatore non può cambiare l'ordine
   delle somme in virgola mobile, quindi ogni somma aspetta il risultato della
   precedente. Lo abbiamo verificato compilando lo stesso ciclo sul Mac con GCC 16
   (`-O3 -fopt-info-vec-all`): il compilatore vettorizza le moltiplicazioni ma
   tiene le somme in fila (*in-order (fold-left) reduction*). Non è lo stesso
   compilatore né la stessa architettura di WILSON, ma la regola sull'ordine delle
   somme è la stessa. Su Sandy Bridge una somma `float` ha una latenza di 3 cicli
   ([A. Fog, *Instruction tables*](https://www.agner.org/optimize/instruction_tables.pdf)),
   quindi al massimo un peso ogni 3 cicli: a 2.8 GHz sono 0.93 miliardi di pesi al
   secondo, cioè 3.7 GB/s. Misuriamo 3.4–3.55 GB/s, cioè 3.2–3.3 cicli per peso se
   il core gira a 2.8 GHz. È compatibile con questa spiegazione solo se il core è in
   turbo vicino al massimo, cosa che non abbiamo misurato (manca un `perf stat` del
   seriale). Il seriale è quindi limitato dalla **latenza delle somme**, non dalla
   banda. Questo spiega perché con pochi thread lo scaling è quasi ideale: ogni
   thread aggiunge una catena di somme indipendente, e la memoria ha ancora banda
   libera.
2. **Il testo identico non è un caso**: dipende da come è diviso il lavoro (righe sì,
   somme dentro una riga no). Lo stesso vincolo, l'ordine delle somme fissato,
   impedisce anche di accelerare il singolo thread con più accumulatori o con
   `-ffast-math`: il programma diventerebbe più veloce, ma i token potrebbero
   cambiare e la validazione della consegna non sarebbe più possibile.
3. **Perché il modello piccolo scala peggio.** A ogni regione parallela i thread
   partono, si dividono le righe e si aspettano alla barriera finale. Questo costo
   non dipende dalla dimensione delle matrici, il lavoro sì. Nel 15M a 16 thread un
   token dura 3.3 ms per 49 regioni, circa 67 µs per regione, quasi come a 8 thread
   (71 µs): aggiungere thread non accorcia più le regioni. Nel 110M una regione dura
   in media 186 µs e c'è ancora lavoro da dividere. In più, nel 15M il 61% dei pesi
   è il classificatore, una sola matrice per token, e le 42 matrici dei layer sono
   piccole (la più piccola ha 288 × 288 pesi, 0.33 MB, 18 righe per thread a 16
   thread).
4. **Perché nessun modello arriva al limite della memoria.** La legge di Amdahl con
   la parte seriale del profilo (3.2% per il 15M e 2.4% per il 110M fuori da
   `matmul`) permetterebbe a `run_omp_mm` uno speedup fino a 10.9 e 11.8 a 16
   thread. Le misure si fermano a 5.0 e 6.3, quindi la parte seriale spiega solo una
   parte della perdita. La frazione seriale sperimentale di Karp–Flatt,
   $e = (1/S_p - 1/p)/(1 - 1/p)$, calcolata su $S_p$ rispetto a 1 thread, cresce da
   0.06 a 4 thread a 0.10 a 16 thread (110M, `run_omp_mm`). Vuol dire che c'è un
   costo che aumenta con il numero di thread, non una parte seriale fissa.
   Candidati compatibili con i dati, non misurati uno per uno:
   - le barriere delle regioni parallele;
   - la frequenza più bassa con tutti i core attivi: nell'esercizio 5 abbiamo
     misurato 2.40 GHz con 16 core, contro un massimo di 2.8;
   - la posizione dei pesi in memoria. Il file è mappato con `mmap` e le pagine
     stanno dove il sistema le ha caricate nella page cache, non vicino al thread
     che le usa (non c'è first touch). I thread di uno dei due socket potrebbero
     quindi leggerle da remoto. Il confronto `close`/`spread` a 8 thread va in
     questa direzione, ma è un solo run.
5. **Cosa servirebbe per chiudere la spiegazione** (non fatto): `perf stat` per i
   cicli per peso e la frequenza; più ripetizioni con `close`; un run con
   `numactl --interleave=all`, o con i pesi copiati in memoria allocata e
   inizializzata in parallelo, per isolare l'effetto NUMA.

## Checkpoint

- Seriale: 58.50 / 20.71 / 7.81 tok/s (15M / 42M / 110M); `matmul` è il 96.9–97.6%
  del tempo; 60.8 / 166.8 / 438.1 MB di pesi per token, letti a circa 3.4 GB/s.
- OpenMP su `matmul` e sulle teste: testo identico al seriale in 92 run su 92.
- A 16 thread lo speedup è 5.2 / 6.5 / 7.1 e l'efficienza 0.32 / 0.41 / 0.44; la
  banda effettiva arriva al massimo a 24.3 GB/s, contro 51.4 GB/s di triad.
- Parte optional (storie con MPI) non svolta.
