# Esercitazione 4 — Profiling e ottimizzazione della data preparation

:::{note} Consegna
Dalla traccia del corso (*Exercises for the report*, sezione 4). Il programma
`preprocess.c` genera un dataset sintetico memorizzato in formato row-major
($N$ osservazioni per $D$ feature, `data[i*d+j]`), calcola media e varianza di
popolazione di ogni feature, standardizza i valori e calcola uno score lineare per
osservazione.

1. **Leggere e prevedere**: prima di eseguire il programma, prevedere quale funzione
   richiederà più tempo, considerando quante volte ogni funzione attraversa i dati,
   le operazioni svolte e l'ordine di accesso alla memoria.
2. **Compilare, verificare e misurare**: compilare con
   `-O2 -g -fno-inline -fno-omit-frame-pointer`, usare un core fisico e 1 GiB in
   un'allocazione Slurm, eseguire il check piccolo `1024 32 1 check` e misurare tre
   volte il processo completo su `65536 256 5` con `/usr/bin/time`, registrando
   tempi, mediana e checksum.
3. **Trovare l'hotspot**: raccogliere un profilo `perf record` dell'originale,
   individuare l'hotspot dalla colonna `Self` e confrontarlo con la previsione;
   prima di modificare il sorgente, stimare con la legge di Amdahl lo speedup massimo
   se l'hotspot diventasse arbitrariamente veloce.
4. **Migliorare**: in una copia del sorgente, riordinare i cicli del calcolo delle
   statistiche in modo che il ciclo interno visiti le feature di una stessa
   osservazione, con una somma corrente per feature e due passate (prima tutte le
   medie, poi tutte le varianze); niente thread, stessa matematica, stessi flag.
5. **Validare e confrontare**: ripetere il check piccolo, confrontare il checksum del
   problema completo entro una tolleranza assoluta di $10^{-8}$ più una relativa di
   $10^{-10}$, ripetere le tre misure e un secondo profilo; calcolare lo speedup come
   rapporto delle mediane, dire se l'hotspot ha perso importanza e cosa investigare
   dopo, confrontare lo speedup con la stima di Amdahl e spiegare perché la stima è
   approssimata quando la frazione viene da un profilo campionato in user-space.
:::

:::{note} Richiami teorici e modello della pipeline
Per ogni feature $j \in \{0, \dots, D-1\}$ il programma calcola media e varianza di
popolazione su due passaggi:

$$\mu_j = \frac{1}{N}\sum_{i=0}^{N-1} X_{ij}, \qquad v_j = \frac{1}{N}\sum_{i=0}^{N-1}(X_{ij}-\mu_j)^2,$$

standardizza in-place ogni elemento con $\hat{X}_{ij} = (X_{ij}-\mu_j)/\sqrt{v_j+\epsilon}$
($\epsilon = 10^{-12}$) e calcola uno score lineare per osservazione
$s_i = \sum_{j=0}^{D-1} w_j \hat{X}_{ij}$ con pesi fissi $w_j = 1/(j+1)$, accumulando
$\sum_i s_i^2$ nel checksum finale.

- **Layout row-major e cache line**: due elementi adiacenti della stessa riga
  (`j` e `j+1`) distano 8 byte; due elementi della stessa colonna (`i` e `i+1`)
  distano $D \times 8$ byte. Con $D = 256$ il passo per colonna è **2048 byte**:
  ogni cache line da 64 B caricata fornisce un solo `double` utile (8 B su 64 B,
  fattore di amplificazione del traffico $64/8 = 8\times$).
- **Legge di Amdahl**: se una frazione $f$ del tempo viene accelerata di un fattore
  $p$, lo speedup complessivo è
  $$S(p) = \frac{1}{(1-f) + f/p} \;\le\; S_{\max} = \frac{1}{1-f}.$$
:::

## Parametri

:::{table} Parametri sperimentali e configurazione su WILSON (job di riferimento `61207`).
:name: tab-es04-params

| Parametro | Valore |
|---|---|
| Directory di lavoro | `/srv/data/wilson/students/home/fbellina2/profiling-data-preparation` |
| Sorgente originale | `preprocess.c`, identico alla copia condivisa `/srv/data/wilson/project/hpc4ai/exercises/profiling-data-preparation/preprocess.c` (`cmp`); SHA256 `084c5538…` |
| Sorgente modificato | `preprocess_rows.c`, SHA256 `819b8f0a…` (copia in [`codes/exec4/`](../codes/exec4/README.md)) |
| Dimensione benchmark | $N = 65536$ osservazioni, $D = 256$ feature ($16\,777\,216$ `double` = 128 MiB per matrice), 5 ripetizioni |
| Dimensione validazione | `1024 32 1 check` (piccola) e `65536 256 1 check` (dimensione piena) |
| Ripetizioni | 3 run per versione per il timing; `perf stat -r 3`; `perf record` a 5 ripetizioni (comando della consegna) e a 30 |
| Dati sintetici | deterministici: `((i*17 + j*13) % 1009) / 1009.0 + (j % 11)`, nessun seed |
| Compilatore | `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)` di sistema; `module list`: `No modules loaded` |
| Flag di compilazione | `-O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra -lm` |
| Nodo | `wnode25`: 2 × Intel Xeon E5-2683 v4 @ 2.10 GHz, 16 core per socket, HT attivo; L1d 32 KiB e L2 256 KiB per core, L3 40 MiB per socket; cache line 64 B |
| Risorse Slurm | partizione `lab4`, 1 nodo, 1 task, 1 CPU, `--hint=nomultithread --mem=1G`; ogni misura con `srun --cpu-bind=cores` |
| Strumenti | `perf` 5.14.0, GNU time 1.9, `time` di bash |
| Job Slurm | `61207` (riferimento, 9 novembre 2026); `61199` (ripetizione indipendente con gli stessi sorgenti) |
| Memoria | `original` (128 MiB) + `data` (128 MiB) + `scores` (512 KiB) + `mean`, `scale`, `weights` ($3 \times 2$ KiB) $\approx 256.5$ MiB; max RSS misurato 264224 KB $\approx$ 258 MiB |
:::

## Implementazione

### Struttura del programma e delle due versioni

Il programma alloca due matrici da 128 MiB (`original` e `data`). `generate_data`
popola `original` **una sola volta** fuori dal ciclo delle ripetizioni. Ad ogni
ripetizione (`repeat = 0 .. repeats-1`) il `main` ricopia `original` in `data` con
`memcpy` affinché ogni passata rielabori lo stesso input non standardizzato, poi
invoca in sequenza `compute_statistics`, `standardize`, `compute_scores` e aggiorna
`checksum += scores[i] * scores[i]`.

:::{table} Anatomia delle funzioni di `preprocess.c` e `preprocess_rows.c`.
:name: tab-es04-funzioni

| Funzione | Righe (`preprocess.c`) | Chiamate | Ordine cicli (esterno → interno) | Passo su `data[i*d+j]` | Traffico teorico per rip. ($N=65536, D=256$) |
|---|---|---|---|---|---|
| `generate_data` | 25–31 | 1 (fuori ciclo) | `i` → `j` (per riga) | +8 B (contiguo) | 128 MiB scrittura (una tantum) |
| `memcpy(data, original)` | 142 | 1 per rip. | streaming AVX | +8 B (contiguo) | 128 MiB R + 128 MiB W = **256 MiB** |
| `compute_statistics` (**originale**) | 34–50 | 1 per rip. | `j` → `i` (2 passaggi per colonna) | **+2048 B (strided)** | $2 \times 128\text{ MiB} \times 8 = \mathbf{2048\text{ MiB}}$ |
| `compute_statistics` (**per righe**) | 34–54 | 1 per rip. | `i` → `j` (2 passaggi per riga) | **+8 B (contiguo)** | $2 \times 128\text{ MiB} = \mathbf{256\text{ MiB}}$ |
| `standardize` | 53–59 | 1 per rip. | `i` → `j` (per riga) | +8 B (contiguo) | 128 MiB R + 128 MiB W = **256 MiB** |
| `compute_scores` | 62–71 | 1 per rip. | `i` → `j` (per riga) | +8 B (contiguo) | 128 MiB R = **128 MiB** |
| `validate` (solo con `check`) | 74–107 | 1 a fine run | `j` → `i` poi `i` → `j` | misto | escluso dai run di benchmark |
:::

### Previsione dell'hotspot dalla lettura del sorgente

Sommando la tabella, una ripetizione dell'originale muove circa
$256 + 2048 + 256 + 128 = 2688$ MiB, di cui 2048 MiB (76%) in `compute_statistics`:
è l'unica funzione che attraversa la matrice per colonne, due volte, con un passo
di 2048 B che spreca 56 dei 64 byte di ogni cache line. Le altre fasi fanno
un'aritmetica comparabile (una o due operazioni per elemento) ma su accessi
contigui. La previsione è quindi che `compute_statistics` domini il tempo, con una
quota dell'ordine di quella del traffico ($\approx 3/4$) se il programma è limitato
dalla memoria.

### Come cambia `compute_statistics` da `preprocess.c` a `preprocess_rows.c`

L'unica funzione modificata in [`codes/exec4/preprocess_rows.c`](../codes/exec4/README.md)
è `compute_statistics`; il `diff -u` registrato nel log del job conferma che il resto
del file differisce solo per un commento e due righe vuote.

- **Versione originale (`preprocess.c`, accesso per colonne / feature-first)**:
  il ciclo esterno fissa la feature `j` e due cicli interni separati scorrono le
  osservazioni `i = 0 .. n-1` accumulando prima nella variabile scalare `sum` e poi
  in `squared_sum`. Poiché `data[i*d+j]` avanza con `i`, due letture consecutive
  saltano `d` `double` (2048 byte).

```c
/* preprocess.c — ciclo esterno su j, cicli interni su i (stride = d*8 = 2048 B) */
static void compute_statistics(const double *data, size_t n, size_t d,
                               double *mean, double *scale)
{
    for (size_t j = 0; j < d; ++j) {
        double sum = 0.0;
        for (size_t i = 0; i < n; ++i)
            sum += data[i*d+j];
        mean[j] = sum / (double)n;

        double squared_sum = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double delta = data[i*d+j] - mean[j];
            squared_sum += delta * delta;
        }
        scale[j] = 1.0 / sqrt(squared_sum / (double)n + 1e-12);
    }
}
```

- **Versione ottimizzata (`preprocess_rows.c`, accesso per righe / observation-first)**:
  si scambiano i cicli `i` e `j` in ciascuno dei due passaggi. Al posto degli
  accumulatori scalari `sum` e `squared_sum` si usano direttamente i vettori
  `mean[0..d-1]` e `scale[0..d-1]` (2 KiB ciascuno, residenti in cache L1):
  1. si azzera `mean[j]`;
  2. per ogni osservazione `i`, il ciclo interno su `j` legge `data[i*d+j]` in
     indirizzi consecutivi (+8 B) e aggiorna `mean[j]`;
  3. si divide `mean[j]` per `n` completando **tutte** le medie prima del secondo
     passaggio;
  4. si azzera `scale[j]`, si accumulano per riga gli scarti quadratici
     `delta * delta` in `scale[j]` e infine si trasforma `scale[j]` in
     $1/\sqrt{\text{scale}[j]/n + 10^{-12}}$.

```c
/* preprocess_rows.c — ciclo esterno su i, ciclo interno su j (contiguo, +8 B) */
static void compute_statistics(const double *data, size_t n, size_t d,
                               double *mean, double *scale)
{
    for (size_t j = 0; j < d; ++j)
        mean[j] = 0.0;
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < d; ++j)
            mean[j] += data[i*d+j];
    for (size_t j = 0; j < d; ++j)
        mean[j] /= (double)n;

    for (size_t j = 0; j < d; ++j)
        scale[j] = 0.0;
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < d; ++j) {
            double delta = data[i*d+j] - mean[j];
            scale[j] += delta * delta;
        }
    for (size_t j = 0; j < d; ++j)
        scale[j] = 1.0 / sqrt(scale[j] / (double)n + 1e-12);
}
```

:::{tip} Equivalenza al bit e ruolo dei flag di compilazione
- **Stesso ordine di somma per ogni feature**: per una feature `j` fissata, entrambe
  le versioni sommano i contributi nell'ordine $i = 0, 1, \dots, N-1$. Non essendo
  riordinate le addizioni in virgola mobile di una stessa feature, `mean[j]`,
  `scale[j]` e il checksum finale restano **identici al bit**.
- **Flag**: `-O2` attiva l'ottimizzazione standard; `-g` conserva i simboli;
  `-fno-inline` impedisce a `gcc` di fondere le funzioni statiche dentro `main`
  (altrimenti scomparirebbero dal report di `perf`); `-fno-omit-frame-pointer`
  permette a `perf record -g` di ricostruire il call graph.
:::

### Compilazione ed esecuzione su WILSON

Tutte le misure provengono da un unico job, lanciato con
[`codes/exec4/es04_all.sh`](../codes/exec4/README.md) dal login node
(`bash es04_all.sh`). Lo script compila sul login node con il `gcc` di sistema,
invia le misure con `sbatch --wait` e registra ogni comando con il suo output nel
log del job. Estratto della compilazione:

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ pwd
/srv/data/wilson/students/home/fbellina2/profiling-data-preparation
[fbellina2@wilson profiling-data-preparation]$ gcc --version
gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)
Copyright (C) 2021 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
[fbellina2@wilson profiling-data-preparation]$ cmp preprocess.c /srv/data/wilson/project/hpc4ai/exercises/profiling-data-preparation/preprocess.c
preprocess.c identico alla copia condivisa del corso
[fbellina2@wilson profiling-data-preparation]$ module list
No modules loaded
[fbellina2@wilson profiling-data-preparation]$ gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess.c -lm -o preprocess
[fbellina2@wilson profiling-data-preparation]$ gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess_rows.c -lm -o preprocess_rows
```

Le direttive Slurm del job corrispondono all'allocazione richiesta dalla consegna
(un core fisico, 1 GiB); ogni misura è un passo `srun --cpu-bind=cores`:

```bash
#SBATCH --partition=lab4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=1G
#SBATCH --time=00:15:00
```

## Procedura di validazione

La modalità `check` esegue `validate(data, n, d, scores)` dopo la pipeline e
verifica che su ogni feature $|\mu_j| \le 10^{-8}$ e $|v_j - 1| \le 10^{-8}$, e che
ogni score coincida con il ricalcolo diretto $\sum_j \hat{X}_{ij}/(j+1)$ entro una
tolleranza relativa di $10^{-10}$. La verifica è eseguita sul caso piccolo
(`1024 32 1 check`) e sulla dimensione piena (`65536 256 1 check`):

```{code-block} text
:class: terminal

[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess 1024 32 1 check
Observations: 1024; features: 32; repeats: 1
Checksum: 8173.5024171285777
Validation: PASS (max |mean| 2.418e-14; max variance error 1.217e-11)
[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess_rows 1024 32 1 check
Observations: 1024; features: 32; repeats: 1
Checksum: 8173.5024171285777
Validation: PASS (max |mean| 2.418e-14; max variance error 1.217e-11)
[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess 65536 256 1 check
Observations: 65536; features: 256; repeats: 1
Checksum: 452271.54382956069
Validation: PASS (max |mean| 1.147e-14; max variance error 1.211e-11)
[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess_rows 65536 256 1 check
Observations: 65536; features: 256; repeats: 1
Checksum: 452271.54382956069
Validation: PASS (max |mean| 1.147e-14; max variance error 1.211e-11)
```

Per il problema completo la consegna richiede $|a-b| \le 10^{-8} + 10^{-10}|a|$
fra i checksum delle due versioni. Con $a = b = 2261357.7191473623$ si ha
$|a-b| = 0 \le 2.26 \times 10^{-4}$: criterio superato, con checksum identici al bit
anche a 30 ripetizioni e su una dimensione diversa.

:::{important} Riepilogo di validazione e checksum su tutte le configurazioni (job `61207`)
:name: tab-es04-validation

| Configurazione (`N D repeats`) | Checksum `preprocess` | Checksum `preprocess_rows` | Esito `check` | Errore max (`|mean|` / `var`) |
|---|---|---|---|---|
| `1024 32 1 check` | `8173.5024171285777` | `8173.5024171285777` | `PASS` | `2.418e-14` / `1.217e-11` |
| `65536 256 1 check` | `452271.54382956069` | `452271.54382956069` | `PASS` | `1.147e-14` / `1.211e-11` |
| `65536 256 5` (benchmark) | `2261357.7191473623` | `2261357.7191473623` | — | $\lvert a-b \rvert = 0$, entro tolleranza |
| `65536 256 30` (profili) | `13568146.314903667` | `13568146.314903667` | — | identico a 17 cifre |
| `100000 256 5` | `3450862.5211855676` | `3450862.5211855676` | — | identico a 17 cifre |
:::

## Risultati e plot

Il log completo del job di riferimento, con tutti i comandi e gli output citati in
questa sezione, è {download}`es04_61207.txt <../../../results/es04/es04_61207.txt>`;
la ripetizione indipendente è {download}`es04_61199.txt <../../../results/es04/es04_61199.txt>`.

### 1. Tempi di esecuzione

Per ogni versione sono state eseguite 3 run di `65536 256 5`, alternando le due
versioni nello stesso job. Ogni run è misurata insieme dal `time` di bash
(risoluzione 1 ms) e da GNU time (`/usr/bin/time`, risoluzione 10 ms, più tempo
`user`, `sys` e memoria massima). Prima coppia di run:

```{code-block} text
:class: terminal

[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores bash -c "TIMEFORMAT='bash time: %R s'; time /usr/bin/time -f 'GNU time: %e s elapsed, %U s user, %S s sys, %M KB max RSS' ./preprocess 65536 256 5"    # run 1
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
GNU time: 1.90 s elapsed, 1.82 s user, 0.05 s sys, 264224 KB max RSS
bash time: 1.902 s
[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores bash -c "TIMEFORMAT='bash time: %R s'; time /usr/bin/time -f 'GNU time: %e s elapsed, %U s user, %S s sys, %M KB max RSS' ./preprocess_rows 65536 256 5"    # run 1
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
GNU time: 0.49 s elapsed, 0.42 s user, 0.06 s sys, 264084 KB max RSS
bash time: 0.497 s
```

:::{table} Tempi di esecuzione di `65536 256 5` (job `61207`, `wnode25`). Tempi totali dal `time` di bash; `user` e `sys` da GNU time.
:name: tab-es04-tempi

| Versione | Run 1 (s) | Run 2 (s) | Run 3 (s) | Mediana (s) | `user` (s) | `sys` (s) |
|---|---|---|---|---|---|---|
| `preprocess` (originale) | 1.902 | 1.901 | 1.902 | **1.902** | 1.82–1.83 | 0.05 |
| `preprocess_rows` (per righe) | 0.497 | 0.497 | 0.498 | **0.497** | 0.42–0.43 | 0.05–0.06 |
:::

Lo speedup complessivo, rapporto delle mediane, è
$S = 1.902 / 0.497 = \mathbf{3.83\times}$ (tempo −73.9%). La variabilità fra le run
è al più 0.2%, trascurabile rispetto all'effetto. Controlli indipendenti:

- GNU time misura 1.90 s e 0.49 s in tutte le run: il rapporto 3.88× differisce
  solo per l'arrotondamento di 0.497 s a 0.49 s;
- `perf stat -r 3` misura $1.9004 \pm 0.0019$ s e $0.4950 \pm 0.0004$ s, cioè 3.84×;
- il job indipendente `61199` dà mediane 1.904 s e 0.498 s, cioè 3.82×.

La tabella richiesta dalla traccia del corso riassume i valori ufficiali:

:::{important} Tabella di sintesi del corso — prima e dopo il riordino dei cicli
:name: tab-es04-course-table3

| Version | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | Main hotspot (`Self` %) |
|---|---|---|---|---|---|
| Original (`preprocess`) | 1.902 | 1.901 | 1.902 | **1.902** | `compute_statistics` — **83.61%** (86.62% a 30 rip.) |
| Row traversal (`preprocess_rows`) | 0.497 | 0.497 | 0.498 | **0.497** | `compute_statistics` — **31.91%** (38.14% a 30 rip.) |
:::

### 2. Profili di campionamento (`perf record` / `perf report`)

Con il comando della consegna (5 ripetizioni, 99 Hz) il profilo originale raccoglie
183 campioni, quello ottimizzato solo 47: ogni campione vale circa il 2% del
profilo. Per questo i due profili sono stati ripetuti anche a 30 ripetizioni
(1069 e 236 campioni). Estratto dei profili della consegna in forma piatta
(`--no-children`, colonna `Self`); i report completi con il call graph sono nel log.

```{code-block} text
:class: terminal

[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores perf record -e cpu-clock:u -F 99 -g -o es04_run_20261109_103054/perf-before.data ./preprocess 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
[ perf record: Woken up 1 times to write data ]
[ perf record: Captured and wrote 0.017 MB es04_run_20261109_103054/perf-before.data (183 samples) ]
[fbellina2@wnode25 profiling-data-preparation]$ perf report --stdio --no-children -g none -i es04_run_20261109_103054/perf-before.data
# To display the perf.data header info, please use --header/--header-only options.
#
#
# Total Lost Samples: 0
#
# Samples: 183  of event 'cpu-clock:u'
# Event count (approx.): 1848484830
#
# Overhead  Command     Shared Object  Symbol
# ........  ..........  .............  ....................................
#
    83.61%  preprocess  preprocess     [.] compute_statistics
     4.92%  preprocess  libc.so.6      [.] __memmove_avx_unaligned_erms_rtm
     4.92%  preprocess  preprocess     [.] standardize
     4.37%  preprocess  preprocess     [.] compute_scores
     2.19%  preprocess  preprocess     [.] generate_data
```

```{code-block} text
:class: terminal

[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores perf record -e cpu-clock:u -F 99 -g -o es04_run_20261109_103054/perf-after.data ./preprocess_rows 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
[ perf record: Woken up 1 times to write data ]
[ perf record: Captured and wrote 0.007 MB es04_run_20261109_103054/perf-after.data (47 samples) ]
[fbellina2@wnode25 profiling-data-preparation]$ perf report --stdio --no-children -g none -i es04_run_20261109_103054/perf-after.data
# To display the perf.data header info, please use --header/--header-only options.
#
#
# Total Lost Samples: 0
#
# Samples: 47  of event 'cpu-clock:u'
# Event count (approx.): 474747470
#
# Overhead  Command          Shared Object    Symbol
# ........  ...............  ...............  ....................................
#
    31.91%  preprocess_rows  preprocess_rows  [.] compute_statistics
    19.15%  preprocess_rows  libc.so.6        [.] __memmove_avx_unaligned_erms_rtm
    19.15%  preprocess_rows  preprocess_rows  [.] compute_scores
    19.15%  preprocess_rows  preprocess_rows  [.] standardize
    10.64%  preprocess_rows  preprocess_rows  [.] generate_data
```

:::{table} Profili `perf` prima e dopo il riordino ($N=65536, D=256$). Tra parentesi i campioni; tempi per ripetizione dal profilo a 30 rip. (`Self` × `Event count` / 30, con `Event count` di `cpu-clock` in ns).
:name: tab-es04-perf-compare

| Simbolo | Self 5 rip. prima (183) | Self 5 rip. dopo (47) | Self 30 rip. prima (1069) | Self 30 rip. dopo (236) | Tempo prima (s/rip.) | Tempo dopo (s/rip.) | Rapporto |
|---|---|---|---|---|---|---|---|
| `compute_statistics` | **83.61%** (153) | **31.91%** (15) | **86.62%** (926) | **38.14%** (90) | 0.3118 | 0.0303 | **10.29×** |
| `compute_scores` | 4.37% (8) | 19.15% (9) | 4.68% (50) | 22.03% (52) | 0.0168 | 0.0175 | 0.96× |
| `standardize` | 4.92% (9) | 19.15% (9) | 4.68% (50) | 21.61% (51) | 0.0168 | 0.0172 | 0.98× |
| `__memmove_avx_unaligned_erms_rtm` (`memcpy`) | 4.92% (9) | 19.15% (9) | 3.65% (39) | 16.53% (39) | 0.0131 | 0.0131 | 1.00× |
| `generate_data` (una volta) | 2.19% (4) | 10.64% (5) | 0.37% (4) | 1.69% (4) | 0.040 tot. | 0.040 tot. | 1.0× |
| **Totale user-space** (`Event count`) | 1.85 s | 0.47 s | 10.80 s | 2.38 s | 0.360 | 0.080 | **4.53×** |
:::

:::{tip} Le fasi non toccate hanno gli stessi campioni
Nel profilo a 30 ripetizioni `compute_statistics` scende da **926 a 90 campioni**,
mentre `compute_scores` (50 → 52), `standardize` (50 → 51), `memcpy` (39 → 39) e
`generate_data` (4 → 4) restano invariati entro il rumore di campionamento. Le fasi
non modificate impiegano lo stesso tempo assoluto: la loro percentuale `Self` sale
di circa 4.5× solo perché il tempo user-space totale scende da 10.80 s a 2.38 s.
:::

### 3. Contatori hardware con `perf stat`

Per verificare l'effetto sulla gerarchia di memoria sono stati raccolti i contatori
hardware su `65536 256 5`, mediati su 3 esecuzioni:

```{code-block} text
:class: terminal

[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores perf stat -r 3 -e cycles,instructions,cache-references,cache-misses ./preprocess 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623

 Performance counter stats for './preprocess 65536 256 5' (3 runs):

     5,456,196,883      cycles:u                                                                ( +-  0.05% )
     2,818,087,193      instructions:u                   #    0.52  insn per cycle              ( +-  0.00% )
       211,219,906      cache-references:u                                                      ( +-  0.00% )
       189,639,566      cache-misses:u                   #   89.78% of all cache refs           ( +-  0.00% )

           1.90042 +- 0.00188 seconds time elapsed  ( +-  0.10% )
[fbellina2@wnode25 profiling-data-preparation]$ srun --cpu-bind=cores perf stat -r 3 -e cycles,instructions,cache-references,cache-misses ./preprocess_rows 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623

 Performance counter stats for './preprocess_rows 65536 256 5' (3 runs):

     1,291,681,655      cycles:u                                                                ( +-  0.05% )
     2,739,436,322      instructions:u                   #    2.12  insn per cycle              ( +-  0.00% )
        68,663,184      cache-references:u                                                      ( +-  0.02% )
        38,628,690      cache-misses:u                   #   56.26% of all cache refs           ( +-  0.03% )

          0.494999 +- 0.000439 seconds time elapsed  ( +-  0.09% )
```

:::{table} Contatori hardware `perf stat -r 3` su `65536 256 5` (medie di 3 esecuzioni; variabilità ≤ 0.1%).
:name: tab-es04-perf-stat

| Metrica | Originale (`preprocess`) | Per righe (`preprocess_rows`) | Variazione | Rapporto |
|---|---|---|---|---|
| `cycles:u` | `5,456,196,883` | `1,291,681,655` | **−76.3%** | 4.22× meno cicli |
| `instructions:u` | `2,818,087,193` | `2,739,436,322` | **−2.8%** | ~1.03× (quasi identico) |
| IPC (`insn per cycle`) | **0.52** | **2.12** | — | **4.11×** |
| `cache-references:u` | `211,219,906` | `68,663,184` | **−67.5%** | 3.08× meno riferimenti |
| `cache-misses:u` | `189,639,566` | `38,628,690` | **−79.6%** | **4.91× meno miss** |
| Miss rate (`misses / refs`) | **89.78%** | **56.26%** | −33.5 punti | — |
| `seconds time elapsed` | **1.9004 s** | **0.4950 s** | **−74.0%** | **3.84×** |
:::

Con `-r` `perf stat` non stampa i tempi `user` e `sys`, che sono presi da GNU time
nella {numref}`tab-es04-tempi`.

### 4. Legge di Amdahl contro speedup misurato

La frazione $f$ è la quota `Self` di `compute_statistics` nel profilo originale.
Considerando i campioni indipendenti, il suo errore statistico è
$\sigma_f = \sqrt{f(1-f)/n}$ con $n$ campioni.

:::{important} Confronto tra stime di Amdahl, modelli e misure
:name: tab-es04-amdahl

| Grandezza / Modello | Formula | Valore | Significato |
|---|---|---|---|
| Quota hotspot $f$ (5 rip., profilo della consegna) | $\text{Self}(\texttt{compute\_statistics})$ | **0.836 ± 0.027** (183 campioni) | Frazione del tempo CPU user-space nell'hotspot |
| **Bound di Amdahl $S_{\max}$** (5 rip.) | $1/(1-f)$ | **6.10×** (5.2–7.3× a $\pm 1\sigma$) | Stima della consegna, fatta prima della modifica |
| Quota hotspot $f$ (30 rip.) | $\text{Self}(\texttt{compute\_statistics})$ | **0.866 ± 0.010** (1069 campioni) | Stessa grandezza con più campioni |
| **Bound di Amdahl $S_{\max}$** (30 rip.) | $1/(1-f)$ | **7.47×** (6.9–8.1× a $\pm 1\sigma$) | Limite se `compute_statistics` diventasse istantanea |
| Modello del solo traffico | $2688\text{ MiB} / 896\text{ MiB}$ | **3.00×** | Rapporto dei byte per ripetizione; `cache-references` misurate: 3.08× |
| Amdahl con $p = 8$ (teorico) | $1 / (0.134 + 0.866/8)$ | **4.13×** | Se l'hotspot accelerasse quanto l'amplificazione del traffico |
| Amdahl con $p$ misurato | $p = 10.29$, $1 / (0.134 + 0.866/10.29)$ | **4.59×** | Previsione con l'accelerazione reale dell'hotspot (30 rip.) |
| Speedup user-space misurato | `Event count` $10.80 / 2.38$ | **4.53×** | Solo tempo CPU in user-space |
| **Speedup wall-clock misurato** | $T_{\text{orig}} / T_{\text{rows}}$ (mediane) | **3.83×** (3.84× `perf stat`) | Include il tempo non user, circa costante |
:::

## Commenti

1. **Previsione e misura.** La lettura del sorgente individua correttamente
   l'hotspot, ma ne sottostima il peso: `compute_statistics` porta il 76% del
   traffico teorico e occupa l'84–87% del tempo user-space. L'accesso con passo di
   2048 B costa più di quanto dica il solo volume di byte: ogni lettura tocca una
   cache line diversa e, con due soli elementi utili per pagina da 4 KiB, i
   prefetcher hardware (che non attraversano i confini di pagina) e la TLB aiutano
   poco. Il ruolo della TLB è un'ipotesi: i contatori dTLB non sono stati misurati.
2. **Stesse istruzioni, quasi un quarto dei cicli.** Le due versioni eseguono
   $\approx 2.8 \times 10^9$ istruzioni (−2.8%), ma i cicli scendono da
   $5.46 \times 10^9$ a $1.29 \times 10^9$ (−76.3%) e l'IPC sale da **0.52 a 2.12**.
   Nell'originale l'89.78% dei riferimenti alla cache è un miss e la CPU resta in
   stallo in attesa dei dati: il programma è limitato dalla memoria. Con l'accesso
   per righe i miss scendono di **4.91×** e i riferimenti di **3.08×**, in accordo
   con il rapporto 3.0× del modello di traffico (2688 MiB → 896 MiB).
3. **Perché 3.83× e non il bound di Amdahl.** Il bound $S_{\max} = 6.1$–$7.5\times$
   suppone un hotspot istantaneo; in realtà `compute_statistics` accelera di
   $p = 10.3\times$, e Amdahl con questo $p$ prevede 4.59×, vicino allo speedup
   user-space misurato (4.53×). Il tempo totale contiene inoltre una parte non user
   quasi costante: tempo totale meno `user` vale circa 0.08 s per l'originale e
   0.07 s per la versione per righe (`sys` 0.05–0.06 s più avvio del processo).
   Aggiungendo 0.07 s ai tempi `user` si ottiene $(1.82 + 0.07)/(0.43 + 0.07)
   \approx 3.8\times$, in accordo con lo speedup misurato.
4. **Perché la stima di Amdahl è approssimata.** La frazione $f$ viene da un
   profilo campionato: con 183 campioni l'errore statistico su $f$ sposta
   $S_{\max}$ fra 5.2× e 7.3×, e il valore a 30 ripetizioni (7.47×) cade al bordo
   di questo intervallo. Il profilo misura solo il tempo CPU user-space
   (`cpu-clock:u`): esclude il tempo `sys`, i page fault e l'avvio del processo,
   che il cronometro esterno invece conta. Infine $f$ dipende dal numero di
   ripetizioni, perché `generate_data` gira una volta sola (2.19% del profilo a 5
   ripetizioni, 0.37% a 30).
5. **L'hotspot ha perso importanza; cosa investigare dopo.** `compute_statistics`
   scende da 83.61% a 31.91% (5 ripetizioni; da 86.62% a 38.14% a 30) e il tempo
   resta ripartito fra `compute_statistics`, `compute_scores` (22.0%),
   `standardize` (21.6%) e `memcpy` (16.5%), tutte con accesso contiguo. La matrice
   da 128 MiB supera la L3 da 40 MiB e viene riletta dalla RAM a ogni fase: un
   ulteriore guadagno richiederebbe di ridurre le passate, con **loop fusion**
   (fondere il secondo passaggio di `compute_statistics`, `standardize` e
   `compute_scores`) o evitando la `memcpy` (leggere da `original` durante il calcolo
   della media).

## Checkpoint

- **Validazione superata (`PASS`)** su `1024 32 1 check` e `65536 256 1 check`;
  checksum del problema completo identico al bit ($|a-b| = 0$, entro la tolleranza
  della consegna) anche a 30 ripetizioni e su `100000 256 5`.
- **Hotspot individuato e ridotto**: `compute_statistics` scende da **83.61%** a
  **31.91%** di `Self` (5 ripetizioni; da 86.62% a 38.14% a 30), con un'accelerazione
  di **10.3×** sulla singola funzione e le altre fasi invariate.
- **Prova hardware (`perf stat`)**: a parità di istruzioni (−2.8%) i cache miss
  calano del **79.6%**, i cicli del **76.3%** e l'IPC sale da **0.52 a 2.12**.
- **Speedup complessivo su WILSON**: **3.83×** (1.902 s → 0.497 s, job `61207`;
  3.82× nel job `61199`), sotto il bound di Amdahl 6.1–7.5× perché l'hotspot accelera
  di un fattore finito e il tempo non user resta costante.
