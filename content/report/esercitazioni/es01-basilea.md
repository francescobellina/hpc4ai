# Esercitazione 1 — Problema di Basilea

:::{note} Consegna
Calcolare le somme parziali

$$S(N) = \sum_{n=1}^{N} \frac{1}{n^2}$$

in **singola precisione** (`float32`), in **ordine diretto** (da $1$ a $N$) e in
**ordine inverso** (da $N$ a $1$), scegliendo l'ordine a runtime. Il programma
deve leggere $N$ dalla riga di comando, stampare una riga leggibile da macchina
con $N$, la somma in singola precisione e il suo **errore assoluto** rispetto a
$\pi^2/6$ (errore calcolato in doppia precisione). Confrontare con la stessa somma
in doppia precisione (`float64`).

Misura da produrre: $|S(N) - \pi^2/6|$ in funzione di $N$ per i due ordini, e la
discussione di **dove domina il troncamento e dove l'arrotondamento**.

**(Optional)** Versione SIMD con intrinsic (AVX su x86, NEON su ARM/Apple
silicon) e confronto di velocità e accuratezza con la versione scalare.
:::

## Parametri

| Parametro | Valore |
|---|---|
| Dimensione del problema | $N$ da $10$ a $10^9$ (campionamento log-spaziato) |
| Precisione numerica | `float32` (binary32) e `float64` (binary64) |
| Ordine di somma | diretto / inverso, selezionato a runtime |
| Criterio di arresto | nessuna iterazione; $N$ fissato a ogni esecuzione |
| Seed casuali | non applicabile (nessun campionamento casuale) |
| Compilatore | Apple clang 21.0.0, `-O2 -Wall -Wextra` (nessun `-ffast-math`) |
| Ambiente | macOS 27.0.1, arm64 (Apple M3 Pro); Python 3.12.14, NumPy 2.5.3 |

:::{note}
Non usare opzioni che riordinano le operazioni in virgola mobile
(`-ffast-math`, `-Ofast`): cambierebbero proprio la grandezza misurata.
:::

## Implementazione

Il programma C `basel_naive.c` (codice completo in
[Appendice — Codici](../appendice-codici.md), cartella `codes/exec1/`) legge tre
argomenti — $N$, ordine (`0` diretto, `1` inverso), precisione (`1` singola,
`0` doppia) — accumula la somma nel tipo richiesto e stampa una riga
leggibile da macchina:

```c
if (reverse)
    for (long n = N; n >= 1; --n) sum += 1.0f / ((float)n * (float)n);
else
    for (long n = 1; n <= N; ++n) sum += 1.0f / ((float)n * (float)n);
printf("%ld %d %.9f %.6e\n", N, reverse, (double)sum, fabs((double)sum - exact));
```

La somma è in `float`, ma il valore stampato e l'errore sono convertiti/calcolati
in `double`, così l'errore è misurato rispetto a $\pi^2/6$ senza aggiungere
errore di confronto. Comandi:

```bash
gcc -O2 -Wall -Wextra -o basel basel_naive.c -lm
./basel 1000000 0 1     # N=10^6, ordine diretto,  float32
./basel 1000000 1 1     # N=10^6, ordine inverso,  float32
```

Lo studio di convergenza è nel notebook, che richiama lo stesso programma con $N$
campionato log-spaziato.

## Procedura di validazione

- **Riferimento noto.** Il valore esatto $\pi^2/6 = 1.644934066848226$ è calcolato
  in doppia precisione dalla costante `M_PI`.
- **Controllo di precisione del riferimento.** Con `float64` e $N = 10^6$
  entrambi gli ordini danno errore $\approx 10^{-6} \approx 1/N$: la somma in
  doppia precisione è limitata dal solo troncamento, come atteso.
- **Coerenza ordine/tipo.** In `float32` l'ordine inverso deve avvicinarsi molto
  di più all'esatto dell'ordine diretto; in `float64` i due ordini devono
  coincidere entro l'errore di troncamento.
- **Verifica del plateau.** In `float32` diretto l'errore deve fermarsi a un valore
  costante quando $1/n^2 < \varepsilon\, S$, cioè intorno a $n \approx 2200$.

## Risultati e plot

:::{table} Esercitazione 1, $N = 10^6$: somma parziale e errore assoluto $\Delta = |S - \pi^2/6|$. Grandezze adimensionali.
:name: tab-basel-n1e6

| Precisione | Ordine | Somma $S(N)$ | Errore $\Delta$ |
|---|---|---|---|
| `float32` | diretto | 1.644725323 | 2.087441e-04 |
| `float32` | inverso | 1.644932985 | 1.081542e-06 |
| `float64` | diretto | 1.644933067 | 9.999995e-07 |
| `float64` | inverso | 1.644933067 | 9.999995e-07 |

:::

:::{table} Studio di convergenza: errore assoluto $\Delta = |S(N) - \pi^2/6|$ per i due ordini e le due precisioni, $N$ log-spaziato. Grandezze adimensionali.
:name: tab-basel-convergenza

| $N$ | f32 diretto | f32 inverso | f64 diretto | f64 inverso |
|---|---|---|---|---|
| 10 | 9.517e-02 | 9.517e-02 | 9.517e-02 | 9.517e-02 |
| 127 | 7.843e-03 | 7.843e-03 | 7.843e-03 | 7.843e-03 |
| 1610 | 6.213e-04 | 6.210e-04 | 6.209e-04 | 6.209e-04 |
| 10826 | 2.087e-04 | 9.240e-05 | 9.237e-05 | 9.237e-05 |
| 72790 | 2.087e-04 | 1.372e-05 | 1.374e-05 | 1.374e-05 |
| 489390 | 2.087e-04 | 2.035e-06 | 2.043e-06 | 2.043e-06 |
| 3290345 | 2.087e-04 | 3.663e-07 | 3.039e-07 | 3.039e-07 |
| 22122163 | 2.087e-04 | 1.279e-07 | 4.521e-08 | 4.520e-08 |
| 148735211 | 2.087e-04 | 8.659e-09 | 9.014e-09 | 6.723e-09 |
| 1000000000 | 2.087e-04 | 8.659e-09 | 9.014e-09 | 1.000e-09 |

:::

:::{figure} ../figures/basel-error-vs-N.png
:name: fig-basel-error-vs-N
:width: 90%

Errore assoluto $\Delta(N)$ contro $N$ (log–log) per `float32`/`float64` e ordine
diretto/inverso. La retta tratteggiata è il troncamento $\approx 1/N$; le linee
puntinate sono $\varepsilon_{32}$ e $\varepsilon_{64}$.
:::

:::{figure} ../figures/basel-float32.png
:name: fig-basel-float32
:width: 70%

Viste separate dell'errore in `float32`: l'ordine diretto si ferma a
$\approx 2.09\times10^{-4}$, l'ordine inverso continua a scendere.
:::

:::{figure} ../figures/basel-float64.png
:name: fig-basel-float64
:width: 70%

Viste separate dell'errore in `float64`: i due ordini coincidono e seguono il
troncamento fino alla epsilon di macchina.
:::

## Commenti

- In `float32` **diretto** l'errore si blocca a $2.087\times10^{-4}$ già intorno a
  $N \approx 2200$: quando $1/n^2$ scende sotto $\varepsilon\,S \approx
  2\times10^{-7}$, i nuovi addendi non cambiano più la somma. Aggiungere termini
  non migliora il risultato.
- In `float32` **inverso** l'errore segue il troncamento fino a $\approx
  9\times10^{-9}$ e poi si appiattisce: sommare prima i termini piccoli conserva
  la precisione relativa.
- In `float64` i due ordini coincidono fino a $N \approx 10^8$; per $N$ più grandi
  differiscono di poco (ordine della $\varepsilon$ di macchina). L'errore segue
  $1/N$ fino a $\approx 10^{-9}$.
- Il comportamento osservato è coerente con la stima del punto di crossover
  $n \approx 1/\sqrt{\varepsilon\,S}$ ricavata dalla teoria.

## Checkpoint

- La somma in `float32` diretto si ferma a $2.087\times10^{-4}$: l'errore di
  arrotondamento domina, il troncamento non è più il limite.
- L'ordine inverso recupera la precisione: errore $\approx 1.08\times10^{-6}$ a
  $N=10^6$, e si appiattisce a $\approx 9\times10^{-9}$ per $N$ grandi.
- In `float64` l'effetto d'ordine scompare: entrambi gli ordini danno
  $\Delta \approx 10^{-6}$ a $N=10^6$ (solo troncamento).
- Validazione superata: il riferimento $\pi^2/6$ e il controllo a due precisioni
  confermano il risultato.
