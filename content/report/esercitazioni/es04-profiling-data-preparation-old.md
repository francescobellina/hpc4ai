# Esercitazione 4 — Profiling e ottimizzazione della data preparation (OLD VERSION)

:::{warning} Versione precedente
Versione della pagina precedente alla riscrittura dai dati del job `61207`, conservata
per confronto. La versione attuale è
[Esercitazione 4](es04-profiling-data-preparation.md).
:::

:::{note} Consegna
Data una pipeline di preprocessing su una matrice $X$ di $N$ osservazioni e $D$
feature memorizzata in formato row-major (`data[i*d+j]`):

1. **Prevedere** quale funzione dominerà il tempo di esecuzione prima di profilare,
   considerando accessi a memoria e aritmetica;
2. **Compilare, validare e misurare** la versione originale (`preprocess.c`) su
   WILSON e **profilare** con `perf record` per individuare l'hotspot reale (`Self`);
3. **Stimare** con la legge di Amdahl $S_{\max} = 1/(1-f)$ il limite superiore di
   speedup sull'intero programma;
4. **Ottimizzare** l'ordine di attraversamento in `compute_statistics`
   (`preprocess_rows.c`), **verificare** che checksum e validazione restino
   invariati, **rimisurare** tempi e profili (`perf record` e `perf stat`).
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

:::{table} Parametri sperimentali e configurazione su WILSON.
:name: tab-es04old-params

| Parametro | Valore |
|---|---|
| Directory di lavoro | `/srv/data/wilson/students/home/fbellina2/profiling-data-preparation` |
| Sorgente condiviso | `/srv/data/wilson/project/hpc4ai/exercises/profiling-data-preparation` |
| Dimensione benchmark | $N = 65536$ osservazioni, $D = 256$ feature ($16\,777\,216$ `double` = 128 MiB per matrice) |
| Dimensione validazione | `1024 32 1 check` (piccola) e `65536 256 1 check` (dimensione piena) |
| Ripetizioni | 5 per timing e `perf stat`; 30 per `perf record` (entrambe le versioni) |
| Dati sintetici | deterministici: `((i*17 + j*13) % 1009) / 1009.0 + (j % 11)`, nessun seed |
| Compilatore | `gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)` |
| Flag di compilazione | `-O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra -lm` |
| Risorse Slurm | partizione `lab4`, nodo `wnode25`, 1 nodo, 1 task, 1 core, `--hint=nomultithread --mem=1G`, `--cpu-bind=cores` |
| Job Slurm | `60924`, `60943` (`TIMEFORMAT` e `perf record`), `60959` (`/usr/bin/time`, validazione piena, `perf stat`) |
| Memoria allocata | `original` (128 MiB) + `data` (128 MiB) + `scores` (512 KiB) + `mean`, `scale`, `weights` ($3 \times 2$ KiB) $\approx 256.5$ MiB |
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
:name: tab-es04old-funzioni

| Funzione | Righe (`preprocess.c`) | Chiamate | Ordine cicli (esterno → interno) | Passo su `data[i*d+j]` | Traffico teorico per rip. ($N=65536, D=256$) |
|---|---|---|---|---|---|
| `generate_data` | 25–31 | 1 (fuori ciclo) | `i` → `j` (per riga) | +8 B (contiguo) | 128 MiB scrittura (una tantum) |
| `memcpy(data, original)` | 142 | 1 per rip. | streaming AVX | +8 B (contiguo) | 128 MiB R + 128 MiB W = **256 MiB** |
| `compute_statistics` (**originale**) | 34–50 | 1 per rip. | `j` → `i` (2 passaggi per colonna) | **+2048 B (strided)** | $2 \times 128\text{ MiB} \times 8 = \mathbf{2048\text{ MiB}}$ |
| `compute_statistics` (**per righe**) | 36–56 | 1 per rip. | `i` → `j` (2 passaggi per riga) | **+8 B (contiguo)** | $2 \times 128\text{ MiB} = \mathbf{256\text{ MiB}}$ |
| `standardize` | 53–59 | 1 per rip. | `i` → `j` (per riga) | +8 B (contiguo) | 128 MiB R + 128 MiB W = **256 MiB** |
| `compute_scores` | 62–71 | 1 per rip. | `i` → `j` (per riga) | +8 B (contiguo) | 128 MiB R = **128 MiB** |
| `validate` (solo con `check`) | 74–107 | 1 a fine run | `j` → `i` poi `i` → `j` | misto | escluso dai run di benchmark |
:::

### Come cambia `compute_statistics` da `preprocess.c` a `preprocess_rows.c`

L'unica funzione modificata in [`codes/exec4/preprocess_rows.c`](../codes/exec4/README.md)
è `compute_statistics`. Tutte le altre righe del file restano identiche.

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

### Comandi di compilazione e allocazione su WILSON

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ pwd
/srv/data/wilson/students/home/fbellina2/profiling-data-preparation
[fbellina2@wilson profiling-data-preparation]$ gcc --version | head -1
gcc (GCC) 11.5.0 20240719 (Red Hat 11.5.0-14)
[fbellina2@wilson profiling-data-preparation]$ gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess.c -lm -o preprocess
[fbellina2@wilson profiling-data-preparation]$ gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess_rows.c -lm -o preprocess_rows
[fbellina2@wilson profiling-data-preparation]$ salloc -plab4 --nodes=1 --ntasks=1 --cpus-per-task=1 \
    --hint=nomultithread --mem=1G --time=00:15:00
salloc: Granted job allocation 60959
salloc: Nodes wnode25 are ready for job
```

:::{warning} Nota operativa Slurm: allocazione scaduta (`Invalid job id`)
Quando il tempo di una `salloc` scade (`Job allocation 60931 has been revoked`), la
variabile `SLURM_JOB_ID` nella shell può restare puntata al job revocato e `srun`
rifiuta l'esecuzione fino all'apertura di una nuova allocazione:

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess 1024 32 1 check
srun: error: Unable to confirm allocation for job 60931: Invalid job id specified
srun: Check SLURM_JOB_ID environment variable. Expired or invalid job 60931
```
:::

## Procedura di validazione

La modalità `check` esegue `validate(data, n, d, scores)` dopo la pipeline e
verifica che su ogni feature $|\mu_j| \le 10^{-8}$ e $|v_j - 1| \le 10^{-8}$, e che
ogni score coincida con il ricalcolo diretto $\sum_j \hat{X}_{ij}/(j+1)$ entro una
tolleranza relativa di $10^{-10}$. La verifica è stata eseguita sia sul caso piccolo
(`1024 32 1 check`) sia sulla dimensione piena del benchmark (`65536 256 1 check`).

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess 1024 32 1 check
Observations: 1024; features: 32; repeats: 1
Checksum: 8173.5024171285777
Validation: PASS (max |mean| 2.418e-14; max variance error 1.217e-11)
[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess_rows 1024 32 1 check
Observations: 1024; features: 32; repeats: 1
Checksum: 8173.5024171285777
Validation: PASS (max |mean| 2.418e-14; max variance error 1.217e-11)
[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess 65536 256 1 check
Observations: 65536; features: 256; repeats: 1
Checksum: 452271.54382956069
Validation: PASS (max |mean| 1.147e-14; max variance error 1.211e-11)
[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores ./preprocess_rows 65536 256 1 check
Observations: 65536; features: 256; repeats: 1
Checksum: 452271.54382956069
Validation: PASS (max |mean| 1.147e-14; max variance error 1.211e-11)
```

:::{important} Riepilogo di validazione e checksum su tutte le configurazioni
:name: tab-es04old-validation

| Configurazione (`N D repeats`) | Checksum `preprocess` | Checksum `preprocess_rows` | Esito `check` | Errore max (`|mean|` / `var`) |
|---|---|---|---|---|
| `1024 32 1 check` | `8173.5024171285777` | `8173.5024171285777` | `PASS` | `2.418e-14` / `1.217e-11` |
| `65536 256 1 check` | `452271.54382956069` | `452271.54382956069` | `PASS` | `1.147e-14` / `1.211e-11` |
| `65536 256 5` (benchmark) | `2261357.7191473623` ($= 5 \times 1\text{ rip.}$) | `2261357.7191473623` | — | identico a 17 cifre |
| `65536 256 30` (profili) | `13568146.314903667` ($= 30 \times 1\text{ rip.}$) | `13568146.314903667` | — | identico a 17 cifre |
| `100000 256 5` | `3450862.5211855676` | `3450862.5211855676` | — | identico a 17 cifre |
:::

## Risultati e plot

### 1. Benchmark dei tempi di esecuzione

I tempi sono stati rilevati sul nodo di calcolo `wnode25` su `65536 256 5` (senza
`check`) sia con `/usr/bin/time -f` (risoluzione al centesimo di secondo, alternando
le due versioni nel ciclo `for k in 1 2 3`) sia con il builtin `time` di `bash`
(risoluzione al millisecondo).

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores /usr/bin/time -f 'Elapsed seconds: %e' ./preprocess 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Elapsed seconds: 1.92
[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores /usr/bin/time -f 'Elapsed seconds: %e' ./preprocess_rows 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Elapsed seconds: 0.51
[fbellina2@wilson profiling-data-preparation]$ for k in 1 2 3; do
    srun --cpu-bind=cores /usr/bin/time -f 'Original: %e s' ./preprocess 65536 256 5
    srun --cpu-bind=cores /usr/bin/time -f 'Rows: %e s' ./preprocess_rows 65536 256 5
done
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Original: 1.92 s
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Rows: 0.49 s
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Original: 1.91 s
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Rows: 0.49 s
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Original: 1.91 s
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Rows: 0.49 s
```

Serie al millisecondo con `bash` `TIMEFORMAT="Elapsed seconds: %R"` (job `60924` e `60943`):

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ for i in 1 2 3; do
  srun --cpu-bind=cores bash -c 'TIMEFORMAT="Elapsed seconds: %R"; time ./preprocess_rows 65536 256 5'
done
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Elapsed seconds: 0.506
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Elapsed seconds: 0.496
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623
Elapsed seconds: 0.496
```

:::{table} Confronto dei tempi di esecuzione per `./preprocess 65536 256 5` (3 ripetizioni del benchmark).
:name: tab-es04old-tempi

| Serie / Timer | Versione | Run 1 (s) | Run 2 (s) | Run 3 (s) | Mediana (s) | Media (s) | Riduzione tempo | Speedup |
|---|---|---|---|---|---|---|---|---|
| WILSON — `bash time` (ms) | `preprocess` (originale) | 1.918 | 1.910 | 1.908 | **1.910** | 1.912 | — | 1.00× |
| WILSON — `bash time` (ms) | `preprocess_rows` (per righe) | 0.506 | 0.496 | 0.496 | **0.496** | 0.499 | −74.0% | **3.85×** |
| WILSON — `/usr/bin/time -f '%e'` | `preprocess` (originale) | 1.92 | 1.91 | 1.91 | **1.91** | 1.9133 | — | 1.00× |
| WILSON — `/usr/bin/time -f '%e'` | `preprocess_rows` (per righe) | 0.49 | 0.49 | 0.49 | **0.49** | 0.4900 | −74.4% | **3.90×** |
| WILSON — `perf stat` (1 run) | `preprocess` → `preprocess_rows` | 1.923 | — | — | 1.923 → 0.508 | — | −73.6% | **3.79×** |
| Client Apple M3 Pro (clang 21, arm64) | `preprocess` → `preprocess_rows` | 0.51 → 0.11 | 0.45 → 0.11 | 0.45 → 0.11 | 0.45 → 0.11 | — | −75.6% | 4.09× |
:::

La tabella richiesta dalla traccia del corso (Table 3, *Before and after changing the statistics traversal*) riassume i valori ufficiali:

:::{important} Tabella di sintesi del corso (Table 3) — Prima e dopo il riordino dei cicli
:name: tab-es04old-course-table3

| Version | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | Main hotspot (`Self` %) |
|---|---|---|---|---|---|
| Original (`preprocess`) | 1.918 (1.92) | 1.910 (1.91) | 1.908 (1.91) | **1.910** (1.91) | `compute_statistics` — **86.20%** (85.56% a 5 rip.) |
| Row traversal (`preprocess_rows`) | 0.506 (0.49) | 0.496 (0.49) | 0.496 (0.49) | **0.496** (0.49) | `compute_statistics` — **37.39%** |
:::

### 2. Profili di campionamento (`perf record` / `perf report`)

Poiché la versione ottimizzata dura ~0.5 s su 5 ripetizioni (~50 campioni a 99 Hz),
seguendo le indicazioni della consegna sono state usate **30 ripetizioni** per
entrambi i profili (`perf-before.data`: 1080 campioni; `perf-after.data`: 238
campioni).

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores perf record -e cpu-clock:u -F 99 -g -o perf-before.data ./preprocess_original 65536 256 30
Observations: 65536; features: 256; repeats: 30
Checksum: 13568146.314903667
[ perf record: Woken up 1 times to write data ]
[ perf record: Captured and wrote 0.085 MB perf-before.data (1080 samples) ]
[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores perf record -e cpu-clock:u -F 99 -g -o perf-after.data ./preprocess_rows 65536 256 30
Observations: 65536; features: 256; repeats: 30
Checksum: 13568146.314903667
[ perf record: Woken up 1 times to write data ]
[ perf record: Captured and wrote 0.021 MB perf-after.data (238 samples) ]
```

#### Output `perf report --stdio -i perf-before.data` (versione originale)

```{code-block} text
:class: terminal

# Total Lost Samples: 0
#
# Samples: 1K of event 'cpu-clock:u'
# Event count (approx.): 10909090800
#
# Children      Self  Command          Shared Object        Symbol
# ........  ........  ...............  ...................  ....................................
#
   100.00%     0.00%  preprocess_orig  libc.so.6            [.] __libc_start_call_main
            |
            ---__libc_start_call_main
               |
               |--86.76%--main
               |          |
               |          |--86.20%--compute_statistics
               |          |
               |           --0.56%--generate_data
               |
               |--4.81%--compute_scores
               |
               |--4.63%--standardize
               |
                --3.80%--__memmove_avx_unaligned_erms_rtm

    86.76%     0.00%  preprocess_orig  preprocess_original  [.] main
    86.20%    86.20%  preprocess_orig  preprocess_original  [.] compute_statistics
     4.81%     4.81%  preprocess_orig  preprocess_original  [.] compute_scores
     4.63%     4.63%  preprocess_orig  preprocess_original  [.] standardize
     3.80%     3.80%  preprocess_orig  libc.so.6            [.] __memmove_avx_unaligned_erms_rtm
     0.56%     0.56%  preprocess_orig  preprocess_original  [.] generate_data
```

#### Output `perf report --stdio -i perf-after.data` (versione per righe)

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores perf report --stdio -i perf-after.data
# Total Lost Samples: 0
#
# Samples: 238  of event 'cpu-clock:u'
# Event count (approx.): 2404040380
#
# Children      Self  Command          Shared Object    Symbol
# ........  ........  ...............  ...............  ....................................
#
   100.00%     0.00%  preprocess_rows  libc.so.6        [.] __libc_start_call_main
            |
            ---__libc_start_call_main
               |
               |--39.92%--main
               |          |
               |          |--37.39%--compute_statistics
               |          |
               |           --2.52%--generate_data
               |
               |--22.27%--compute_scores
               |
               |--21.01%--standardize
               |
                --16.81%--__memmove_avx_unaligned_erms_rtm

    39.92%     0.00%  preprocess_rows  preprocess_rows  [.] main
    37.39%    37.39%  preprocess_rows  preprocess_rows  [.] compute_statistics
    22.27%    22.27%  preprocess_rows  preprocess_rows  [.] compute_scores
    21.01%    21.01%  preprocess_rows  preprocess_rows  [.] standardize
    16.81%    16.81%  preprocess_rows  libc.so.6        [.] __memmove_avx_unaligned_erms_rtm
     2.52%     2.52%  preprocess_rows  preprocess_rows  [.] generate_data
```

:::{table} Confronto completo dei profili `perf` prima e dopo l'ottimizzazione (30 ripetizioni, $N=65536, D=256$).
:name: tab-es04old-perf-compare

| Simbolo | Self % (5 rip., 180 camp.) | Self % Prima (30 rip., 1080 camp.) | Self % Dopo (30 rip., 238 camp.) | Tempo Prima (s / rip.) | Tempo Dopo (s / rip.) | Speedup della singola fase |
|---|---|---|---|---|---|---|
| `compute_statistics` | 85.56% (154) | **86.20%** (931) | **37.39%** (89) | 0.3135 s | 0.0300 s | **10.46×** |
| `compute_scores` | 5.00% (9) | 4.81% (52) | 22.27% (53) | 0.0175 s | 0.0178 s | 0.98× (invariato) |
| `standardize` | 5.00% (9) | 4.63% (50) | 21.01% (50) | 0.0168 s | 0.0168 s | 1.00× (invariato) |
| `__memmove_avx_unaligned_erms_rtm` (`memcpy`) | 3.33% (6) | 3.80% (41) | 16.81% (40) | 0.0138 s | 0.0135 s | 1.02× (invariato) |
| `generate_data` (1 sola volta) | 1.11% (2) | 0.56% (6) | 2.52% (6) | 0.0606 s tot. | 0.0606 s tot. | 1.00× (invariato) |
| **Totale user-space (`Event count`)** | 1.82 s | **10.91 s** (0.364 s/rip.) | **2.40 s** (0.080 s/rip.) | — | — | **4.54×** (solo user CPU) |
:::

:::{tip} Lettura fisica della Tabella 5: campioni identici per le fasi non toccate
Guardando il numero assoluto di campioni su 30 ripetizioni:

- `compute_statistics` crolla da **931 a 89 campioni** ($10.46\times$ più veloce);
- `compute_scores` passa da **52 a 53 campioni**, `standardize` resta a **50
  campioni**, `memcpy` da **41 a 40 campioni**, `generate_data` resta a **6
  campioni**.

Le fasi non modificate eseguono esattamente lo stesso lavoro nello stesso tempo
assoluto: la loro percentuale `Self` sale di ~4.5× solo perché il tempo totale
user-space è sceso da 10.91 s a 2.40 s.
:::

### 3. Contatori hardware con `perf stat`

Per verificare direttamente l'effetto sulla gerarchia di memoria e sulla pipeline
della CPU sono stati raccolti i contatori hardware su `65536 256 5`:

```{code-block} text
:class: terminal

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores perf stat -e cycles,instructions,cache-references,cache-misses ./preprocess 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623

 Performance counter stats for './preprocess 65536 256 5':

     5,496,844,213      cycles:u
     2,818,084,016      instructions:u                   #    0.51  insn per cycle
       211,238,959      cache-references:u
       189,620,745      cache-misses:u                   #   89.77% of all cache refs

       1.923004894 seconds time elapsed

       1.840539000 seconds user
       0.068656000 seconds sys

[fbellina2@wilson profiling-data-preparation]$ srun --cpu-bind=cores perf stat -e cycles,instructions,cache-references,cache-misses ./preprocess_rows 65536 256 5
Observations: 65536; features: 256; repeats: 5
Checksum: 2261357.7191473623

 Performance counter stats for './preprocess_rows 65536 256 5':

     1,294,445,012      cycles:u
     2,739,432,998      instructions:u                   #    2.12  insn per cycle
        68,703,756      cache-references:u
        38,600,350      cache-misses:u                   #   56.18% of all cache refs

       0.507690219 seconds time elapsed

       0.431594000 seconds user
       0.072672000 seconds sys
```

:::{table} Confronto dei contatori hardware `perf stat` su `./preprocess 65536 256 5`.
:name: tab-es04old-perf-stat

| Metrica | Originale (`preprocess`) | Per righe (`preprocess_rows`) | Variazione | Rapporto |
|---|---|---|---|---|
| `cycles:u` | `5,496,844,213` | `1,294,445,012` | **−76.5%** | 4.25× meno cicli |
| `instructions:u` | `2,818,084,016` | `2,739,432,998` | **−2.8%** | ~1.03× (quasi identico) |
| IPC (`insn per cycle`) | **0.51** | **2.12** | **+315.7%** | **4.16×** |
| `cache-references:u` | `211,238,959` | `68,703,756` | **−67.5%** | 3.07× meno riferimenti |
| `cache-misses:u` | `189,620,745` | `38,600,350` | **−79.6%** | **4.91× meno miss** |
| Miss rate (`misses / refs`) | **89.77%** | **56.18%** | −33.59 punti | — |
| `seconds user` | 1.8405 s | 0.4316 s | −76.5% | 4.26× |
| `seconds sys` | 0.0687 s | 0.0727 s | +5.8% | ~1.0× (page fault / alloc) |
| `seconds time elapsed` | **1.9230 s** | **0.5077 s** | **−73.6%** | **3.79×** |
:::

### 4. Legge di Amdahl contro speedup misurato

:::{important} Confronto tra modelli predittivi e misure sperimentali
:name: tab-es04old-amdahl

| Grandezza / Modello | Formula | Valore | Significato |
|---|---|---|---|
| Quota hotspot $f$ (30 rip.) | $\text{Self}(\texttt{compute\_statistics})$ | **0.8620** (0.8556 a 5 rip.) | Frazione del tempo CPU user-space nell'hotspot |
| **Bound di Amdahl $S_{\max}$** | $1/(1-f)$ | **7.25×** (6.93× a 5 rip.) | Limite se `compute_statistics` diventasse **istantanea** ($p \to \infty$, $T_{\min} \approx 0.263$ s) |
| **Modello del solo traffico cache** | $2688\text{ MiB} / 896\text{ MiB}$ | **3.00×** | Rapporto dei byte trasferiti per ripetizione |
| **Amdahl con $p = 8$ (teorico)** | $1 / (0.1380 + 0.8620/8)$ | **4.07×** (residuo 24.6%) | Previsione se l'hotspot accelera 8× e il resto non cambia |
| **Amdahl con $p = 10.46$ (da `perf`)** | $1 / (0.1380 + 0.8620/10.46)$ | **4.54×** (solo user CPU) | Rapporto misurato sugli `Event count` user-space ($10.91 / 2.40$) |
| **Speedup wall-clock misurato** | $T_{\text{orig}} / T_{\text{rows}}$ | **3.85× – 3.90×** (3.79× in `perf stat`) | Include ~0.07 s di tempo `sys` (allocazione e page fault) incomprimibile |
:::

## Commenti

1. **Perché le istruzioni restano uguali (−2.8%) ma il tempo crolla di quasi 4×**:
   `perf stat` mostra che entrambe le versioni eseguono $\approx 2.8 \times 10^9$
   istruzioni, ma i cicli CPU scendono da $5.50 \times 10^9$ a $1.29 \times 10^9$
   (−76.5%) e l'IPC sale da **0.51 a 2.12** (4.16×). Nella versione originale la CPU
   resta in stallo in attesa dei dati per quasi due cicli ogni istruzione perché
   l'89.77% dei riferimenti alla cache produce un miss (189.6 M miss su 211.2 M).
   Con l'accesso per righe i cache miss scendono di **4.91×** (a 38.6 M) e i
   riferimenti di **3.07×** (in accordo con il rapporto 3.0× del modello di traffico
   2688 MiB → 896 MiB).
2. **Perché lo speedup reale è 3.85×–3.90× e non il bound di Amdahl 7.25×**:
   - primo, `compute_statistics` non si annulla ma accelera di $p = 10.46\times$,
     portando lo speedup user-space a $4.54\times$;
   - secondo, il timer esterno misura l'intero processo, che include $\approx 0.07$ s
     di tempo kernel (`sys`) per l'allocazione e i page fault sui 256 MiB di matrici:
     sommando $0.07$ s a entrambi ($1.84 + 0.07 \approx 1.91$ s contro
     $0.43 + 0.07 \approx 0.50$ s) si ottiene esattamente $1.91 / 0.50 = 3.82\times$.
3. **Cosa investigare come passo successivo**: nel profilo `after` il tempo è
   ripartito tra `compute_statistics` (37.4%), `compute_scores` (22.3%),
   `standardize` (21.0%) e `memcpy` (16.8%), tutte già con accesso contiguo per
   righe. Poiché la matrice da 128 MiB supera la cache L3 e viene riletta da RAM a
   ogni fase, un ulteriore miglioramento richiederebbe **loop fusion** (fondere il
   secondo passaggio di `compute_statistics`, `standardize` e `compute_scores` per
   evitare di rileggere `data` dalla RAM) oppure evitare la `memcpy` leggendo da
   `original` durante il calcolo della media.

## Checkpoint

- **Validazione superata (`PASS`)** sia su `1024 32 1 check` sia su `65536 256 1 check`,
  con checksum identico a 17 cifre (`8173.5024171285777`, `452271.54382956069`,
  `2261357.7191473623` a 5 rip., `13568146.314903667` a 30 rip.).
- **Hotspot individuato e rimosso**: `compute_statistics` scende da **86.20%** a
  **37.39%** di `Self` (da 0.314 s a 0.030 s per ripetizione, **10.5×** sulla
  singola funzione), lasciando invariate tutte le altre fasi.
- **Prova hardware (`perf stat`)**: a parità di istruzioni (−2.8%), i cache miss
  calano del **79.6%** (189.6 M → 38.6 M), i cicli CPU del **76.5%** e l'IPC sale da
  **0.51 a 2.12**.
- **Speedup complessivo su WILSON**: **3.85×** (1.910 s → 0.496 s con `bash time`;
  **3.90×**, 1.91 s → 0.49 s con `/usr/bin/time`), pienamente spiegato da Amdahl con
  accelerazione finita dell'hotspot ($4.54\times$ user-space) più i $0.07$ s di
  tempo `sys` costante.
