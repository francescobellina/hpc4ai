# codes/exec1 — Problema di Basilea

Somma parziale di $\zeta(2)$ in singola o doppia precisione, in ordine diretto o
inverso. Corrisponde all'[Esercitazione 1](../../esercitazioni/es01-basilea.md).

## File

| File | Scopo |
|---|---|
| `basel_naive.c` | programma scalare; stampa una riga leggibile da macchina |

## Dipendenze

- Compilatore C (testato con Apple clang 21.0.0; su WILSON `gcc`).
- Libreria matematica `libm` (`-lm`).

## Build

```bash
gcc -O2 -Wall -Wextra -o basel basel_naive.c -lm
```

Non usare `-ffast-math` né `-Ofast`: riordinano le operazioni in virgola mobile e
invalidano la misura.

## Esecuzione

```bash
./basel <N> <ordine> <precisione>
```

| Argomento | Valori |
|---|---|
| `N` | intero positivo (es. `1000000`) |
| `ordine` | `0` diretto, `1` inverso |
| `precisione` | `1` `float32`, `0` `float64` |

Output: una riga `N ordine somma errore_assoluto`, con la somma e l'errore in
doppia precisione rispetto a $\pi^2/6$.

## Parametri di default

Nessuno: tutti e tre gli argomenti sono obbligatori. Lo studio di convergenza
(campionamento log-spaziato di $N$, chunk da $2^{20}$) è nel notebook.
