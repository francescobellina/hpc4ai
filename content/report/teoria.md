# Teoria

Richiami essenziali per la relazione. La trattazione completa è nel
notebook [`report-exercises.ipynb`](notebooks/report-exercises.ipynb).

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

## Modello di esecuzione parallela

Due modelli di memoria, e la loro combinazione:

- **Memoria condivisa (thread)** — più thread in un unico spazio di indirizzi,
  dentro un solo processo. In OpenMP il numero di thread è controllato da
  `OMP_NUM_THREADS`.
- **Memoria distribuita (processi)** — i rank MPI sono processi separati, anche su
  nodi diversi, avviati con `mpiexec` o `srun` e comunicanti via messaggi.
- **Ibrido** — più rank per nodo, ciascuno con più thread OpenMP. Con $P$ rank e
  $T$ thread per rank si ottengono $P \times T$ linee di attività.

L'**affinità di CPU** (maschera dei core assegnati) determina dove girano
davvero thread e processi; va verificata, non solo richiesta.

## Esecuzione su cluster (Slurm)

I test sul login node servono solo a controlli molto brevi: le esecuzioni reali
passano da **Slurm** con uno script di batch che carica gli stessi moduli usati per
compilare e lancia il programma con `srun`.

- **Run OpenMP** — un task con più CPU: `--cpus-per-task=T` e
  `export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`.
- **Run MPI** — più task con una CPU ciascuno: `--ntasks=P --cpus-per-task=1`,
  `OMP_NUM_THREADS=1`.
- **Run ibrido** — più task con più CPU ciascuno, su più nodi:
  `--nodes=2 --ntasks=P --cpus-per-task=T`.

## Metriche di prestazione

Con $T_1$ tempo di riferimento e $T_p$ tempo su $p$ elementi:

$$S_p = \frac{T_1}{T_p}\quad\text{(speedup)},\qquad
E_p = \frac{S_p}{p}\quad\text{(efficienza)}.$$

Lo **strong scaling** tiene fisso il problema globale; il **weak scaling** tiene
circa costante il lavoro per elemento. Riportare sempre i tempi con le dimensioni
del problema e delle risorse.
