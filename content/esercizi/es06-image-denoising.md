# Esercitazione 6 — Image denoising in parallel

:::{note} Consegna
Studiare un programma C sequenziale che **ripulisce un'immagine in scala di grigi**
con un algoritmo iterativo, poi **parallelizzarlo con MPI**. In alternativa si può
scrivere una propria versione sequenziale in C o C++. Il calcolo combina due schemi
di comunicazione: i processi vicini si scambiano i bordi dell'immagine
(**comunicazione point-to-point**), e tutti insieme partecipano a una riduzione per
decidere quando fermarsi (**operazione collettiva**). Non servono librerie di machine
learning né addestramento. Il capitolo del corso su memoria distribuita e MPI copre
le operazioni point-to-point e collettive necessarie.

- **Sequenziale** — leggere `denoise_serial.c` e verificarlo: un'immagine costante
  resta invariata; il caso 2 × 2 con righe (0, 1) e (1, 0) e $\lambda = 1$ dà
  (2/3, 1/3), (1/3, 2/3) dopo un'iterazione e converge a (0.4, 0.6), (0.6, 0.4);
  sull'immagine media, confrontare $\lambda = 0.2$ e $\lambda = 1$ mostrando le due
  ricostruzioni e il MSE di immagine rumorosa e ricostruita rispetto a quella pulita.
- **MPI** — strisce orizzontali contigue, anche con altezza non divisibile per il
  numero di rank ($1 \le p \le H$). Dimensioni e parametri con **operazioni
  collettive**, input con `MPI_Scatterv`, risultato con `MPI_Gatherv` (anche queste
  **collettive**): solo il rank 0 legge e scrive immagini, e nessun altro rank tiene
  una copia completa. Prima di ogni aggiornamento scambiare con `MPI_Sendrecv`
  (**point-to-point**) la prima e l'ultima riga possedute; la variazione massima si
  combina con `MPI_Allreduce` (`MPI_MAX`, **collettiva**) e tutti i rank decidono
  insieme se continuare.
- **Validazione** — un rank, più rank, decomposizione irregolare (per esempio
  17 × 19 su 3 rank) e una riga per rank. A parità di iterazioni la differenza
  massima dal sequenziale, prima dell'arrotondamento a 8 bit, deve essere sotto
  $10^{-12}$; devono coincidere anche la decisione di arresto e il numero di
  iterazioni.
- **Scaling** — strong scaling a lavoro fisso: `images/large/noisy.pgm`
  (8192 × 8192), 200 iterazioni, tolleranza zero (la riduzione resta), un rank per
  core fisico, prima in un nodo e poi su più nodi. Tempo della sola fase iterativa
  con `MPI_Wtime` (massimo sui rank, dopo una sincronizzazione), tempo per
  iterazione, speedup ed efficienza; discutere il lavoro locale $\propto HW/p$, le
  due righe da $W$ `double` che un rank interno invia a ogni iterazione e la
  riduzione globale.

**(Optional)** Weak scaling (altezza che cresce con i rank a larghezza e righe per
rank fisse); scambio degli halo non bloccante; MPI + OpenMP dentro ogni striscia;
griglia di processi bidimensionale con quattro vicini.
:::

:::{seealso} Teoria di riferimento
- **7. Programmare con MPI** — {ref}`Possesso dei dati e decomposizione a blocchi <t7-decomposizione>`
- **7. Programmare con MPI** — {ref}`Comunicazione point-to-point <t7-p2p>` e {ref}`tipi derivati e scambio degli halo <t7-datatype>`
- **7. Programmare con MPI** — {ref}`Comunicazione collettiva <t7-collettive>`
- **7. Programmare con MPI** — {ref}`Prestazioni di un programma MPI <t7-prestazioni>`
- **2. Calcolo parallelo** — {ref}`Prestazioni e scalabilità <prestazioni-scalabilita>`
- **4. Gestione delle risorse** — {ref}`Disposizione, affinità e Slurm <disposizione-e-slurm>`
:::

:::{tip} L'esercizio in breve
**Cosa vogliamo sapere.** Un'immagine rumorosa si ripulisce cercando un'immagine
vicina ai dati ma più liscia. L'algoritmo di Jacobi aggiorna ogni pixel usando solo
i suoi **quattro primi vicini** (sopra, sotto, sinistra, destra) dell'iterazione
precedente: è un lavoro locale, quindi l'immagine si può dividere in strisce, una
per processo. Proprio perché servono solo i primi vicini, ogni processo deve farsi
dare dai processi accanto **una sola riga** per lato (l'*halo*), e poi partecipare a
una decisione comune su quando fermarsi. Le due cose usano i due tipi di
comunicazione di MPI: le righe di confine vanno solo fra rank vicini
(**point-to-point**), la decisione coinvolge tutti i rank (**collettiva**). Nel caso
ideale $p$ processi vanno $p$ volte più veloci; in realtà la comunicazione ha un
costo che non cala con $p$.

**Stato.** Teoria del modello scritta (sotto). Programma sequenziale del corso letto
e verificato: le previsioni a mano coincidono con le sue uscite, e un'implementazione
NumPy indipendente lo riproduce bit per bit. Qualità delle ricostruzioni misurata.
Versione MPI scritta e validata, sul Mac e su WILSON (1 rank, un nodo, due nodi):
differenza zero dal sequenziale in tutti i 20 casi. Da fare: lo scaling.
:::

| Parte | Stato | Obbligatoria |
|---|---|---|
| Modello, Jacobi, criterio di arresto | scritta in questa pagina | sì |
| Verifiche del sequenziale (costante, 2 × 2, piccola, $\lambda$ = 0.2 e 1, MSE) | fatte | sì |
| Versione MPI a strisce, validazione a $10^{-12}$ | fatte (Mac e WILSON, 20 casi su 20) | sì |
| Strong scaling su `large` | da fare | sì |
| Weak scaling, halo non bloccanti, MPI + OpenMP, griglia 2D | — | no (corso) |
| PSNR, SSIM, scansione di $\lambda$ | fatti | no (aggiunta) |
| Confronto con convoluzione e steepest descent | — | no (approfondimento personale, non chiesto dal corso) |

(es06-teoria)=
## Modello e teoria

### L'energia da minimizzare

$f$ è l'immagine rumorosa, con valori normalizzati in $[0, 1]$: è il dato e non
cambia mai. $u$ è la ricostruzione, l'incognita, un valore per pixel. Si cerca la
$u$ che minimizza

$$
E(u) = \frac{1}{2}\sum_{i,j}\left(u_{i,j} - f_{i,j}\right)^2
     + \frac{\lambda}{2}\sum_{\{a,b\} \in \mathcal{E}}\left(u_a - u_b\right)^2,
\qquad \lambda > 0,
$$

dove $\mathcal{E}$ è l'insieme delle coppie di pixel adiacenti in orizzontale o in
verticale (non in diagonale), ciascuna contata una volta.

- Il primo termine (**fedeltà**) costa allontanarsi dal dato: da solo darebbe
  $u = f$, cioè nessuna pulizia.
- Il secondo (**regolarità**) costa avere pixel vicini diversi: da solo darebbe
  un'immagine costante.
- $\lambda$ bilancia i due. Con $\lambda$ piccolo $u$ resta vicino a $f$ e si toglie
  poco rumore; con $\lambda$ grande $u$ è più liscia, si toglie più rumore ma si
  sfocano anche i contorni degli oggetti. Il confronto fra $\lambda = 0.2$ e
  $\lambda = 1$ della consegna serve a vedere questo compromesso.

$E$ è una somma di quadrati di funzioni lineari di $u$, e il termine di fedeltà la
rende strettamente convessa: c'è **un solo minimo** $u^\ast$, che dipende solo da $f$
e da $\lambda$, non dal punto di partenza.

### Dalla condizione di minimo all'aggiornamento di Jacobi

Sia $N(i,j)$ l'insieme dei vicini **esistenti** del pixel $(i,j)$ e $d_{i,j}$ il
loro numero. Il pixel compare in un termine di fedeltà e in una coppia per ogni
vicino; la derivata di $\tfrac{\lambda}{2}(u_a - u_b)^2$ rispetto a $u_a$ è
$\lambda (u_a - u_b)$. Nel minimo tutte le derivate sono nulle:

$$
\frac{\partial E}{\partial u_{i,j}} = \left(u_{i,j} - f_{i,j}\right)
  + \lambda \sum_{(k,l) \in N(i,j)} \left(u_{i,j} - u_{k,l}\right) = 0
\quad\Longrightarrow\quad
\left(1 + \lambda d_{i,j}\right) u_{i,j} = f_{i,j} + \lambda \sum_{(k,l) \in N(i,j)} u_{k,l}.
$$

È un sistema lineare con un'equazione per pixel, e ogni equazione contiene **solo il
pixel e i suoi primi vicini**: al più 5 incognite su $H \times W$. **Jacobi** risolve
ogni equazione per il proprio pixel usando per i vicini i valori dell'iterazione
precedente, partendo da $u^{(0)} = f$ ([Saad 2003](#es06-fonti), §4.1, eq. 4.4):

$$
u^{(t+1)}_{i,j} = \frac{f_{i,j} + \lambda \sum_{(k,l) \in N(i,j)} u^{(t)}_{k,l}}{1 + \lambda d_{i,j}}.
$$

```text
            (i-1, j)
               │
 (i, j-1) ── (i, j) ── (i, j+1)        stencil a 5 punti: il pixel e i suoi
               │                       quattro primi vicini (niente diagonali)
            (i+1, j)
```

Il pixel nuovo dipende da **cinque valori**, $f_{i,j}$ e i quattro $u^{(t)}$ dei primi
vicini (meno ai bordi), e da $\lambda$. Nessun pixel più lontano entra nel calcolo
di un singolo passo; l'informazione si propaga di **un pixel per iterazione**.
Conseguenze pratiche:

- servono **due array** per $u$ (iterazione corrente e successiva) più $f$, che resta
  intatto. Scrivere il nuovo valore sopra il vecchio farebbe leggere a un pixel
  vicini già aggiornati: sarebbe un altro metodo, **Gauss–Seidel**, con risultati
  diversi a parità di iterazioni (riquadro sotto);
- ogni pixel nuovo dipende solo da valori vecchi, quindi i pixel si possono
  calcolare **in qualsiasi ordine e in parallelo**. È ciò che rende possibile la
  versione MPI a strisce;
- poiché lo stencil arriva solo ai primi vicini, a una striscia mancano, per
  aggiornare le sue righe estreme, **solo la riga subito sopra e quella subito
  sotto**, che appartengono ai rank vicini (sezione {ref}`es06-mpi-teoria`).

:::{admonition} Jacobi e Gauss–Seidel
:class: dropdown
I due metodi partono dalla stessa equazione per pixel e differiscono solo in **quali
valori dei vicini** usano. Jacobi usa sempre quelli dell'iterazione precedente
([Saad 2003](#es06-fonti), §4.1, eq. 4.4–4.5). Gauss–Seidel percorre i pixel in un ordine
fissato e usa **subito** i valori già aggiornati in questa iterazione (stessa
sezione, eq. 4.6): in un solo array, sopra e a sinistra trova valori nuovi, sotto e a
destra valori vecchi.

| | Jacobi | Gauss–Seidel |
|---|---|---|
| Valori dei vicini | tutti dell'iterazione $t$ | già aggiornati quando li ha incontrati |
| Memoria per $u$ | due array | un array |
| Ordine dei pixel | indifferente | conta: ordini diversi danno numeri diversi |
| Parallelismo | immediato: ogni pixel è indipendente | ogni pixel aspetta il precedente; si parallelizza solo cambiando ordine, per esempio "a scacchiera" (red–black, Saad 2003, §12.4.1) |
| Convergenza per questo problema | sì (sotto) | sì, per lo stesso teorema |

La consegna chiede Jacobi, e il confronto MPI contro seriale a $10^{-12}$ vale solo
se entrambi fanno esattamente Jacobi. Lo stesso problema di dipendenza fra punti è
quello che nell'[esercizio 5](es05-hpl-hpcg.md) (commento 2 sui risultati su un
nodo) frena lo smoother di Gauss–Seidel dentro il multigrid di HPCG.
:::

### Perché converge e quanto in fretta

Questa stima è ricavata qui e non è nella consegna. Sia $e^{(t)} = u^{(t)} - u^\ast$
l'errore. Sottraendo l'equazione del minimo dall'aggiornamento, $f$ si cancella:

$$
e^{(t+1)}_{i,j} = \frac{\lambda}{1 + \lambda d_{i,j}} \sum_{(k,l) \in N(i,j)} e^{(t)}_{k,l}
\quad\Longrightarrow\quad
\max |e^{(t+1)}| \le q \, \max |e^{(t)}|, \qquad
q = \max_{i,j} \frac{\lambda d_{i,j}}{1 + \lambda d_{i,j}} = \frac{4\lambda}{1 + 4\lambda},
$$

perché il coefficiente del pixel, $1 + \lambda d$, supera sempre la somma dei
coefficienti dei vicini, $\lambda d$ (l'ultima uguaglianza vale se l'immagine ha
almeno un pixel interno). In termini di matrici, il sistema $A u = f$ ha
$A = I + \lambda L$, con $L$ la matrice laplaciana della griglia dei pixel, ed è
**strettamente diagonalmente dominante** ([Saad 2003](#es06-fonti), §4.2.3, Definizione
4.5). Due risultati del libro di Saad coprono il caso:

- se una norma della matrice di iterazione è minore di 1, l'iterazione converge per
  ogni punto di partenza (§4.2.1, Corollario 4.2). La $q$ sopra è proprio la norma
  infinito della matrice di iterazione di Jacobi;
- se $A$ è strettamente diagonalmente dominante, Jacobi e Gauss–Seidel convergono per
  ogni punto di partenza (§4.2.3, Teorema 4.9).

Jacobi quindi converge per ogni $\lambda > 0$, e l'errore massimo cala almeno del
fattore $q$ a ogni iterazione:

| $\lambda$ | $q = 4\lambda/(1 + 4\lambda)$ | Iterazioni per ridurre l'errore di $10^{-6}$, al più |
|---|---|---|
| 0.2 | 0.444 | 18 |
| 1 | 0.800 | 62 |

$\lambda$ più grande vuol dire immagine più liscia ma **convergenza più lenta**.
Quale parte dell'errore cala più piano: Saad (§13.1) osserva che i metodi di
rilassamento come Jacobi e Gauss–Seidel smorzano in fretta le componenti oscillanti
dell'errore (che cambiano segno da un pixel all'altro), mentre quelle lisce
(*smooth modes*) si smorzano a fatica, e da qui viene il rallentamento di tutti i
metodi iterativi di base. È anche la ragione del multigrid, che risolve le
componenti lisce su griglie più grossolane; l'articolo di ResNet cita il multigrid
proprio come esempio di metodo che lavora sul residuo ([He et al. 2016](#es06-fonti), §2). Su
un'immagine grande la stima con $q$ è quindi quasi esatta per le componenti lisce.
Sono previsioni da confrontare con le iterazioni stampate dal programma, non
risultati.

### Il criterio di arresto

$$
\Delta^{(t)} = \max_{i,j} \left| u^{(t+1)}_{i,j} - u^{(t)}_{i,j} \right|,
\qquad \text{stop se } \Delta^{(t)} < \varepsilon \text{ oppure se si raggiunge il numero massimo di iterazioni.}
$$

Va sempre riportato **quale** delle due condizioni ha fermato il run.

- $\Delta$ piccolo non vuol dire errore piccolo, ma i due sono legati. Da
  $\max|e^{(t+1)}| \le q \max|e^{(t)}| \le q\,(\max|e^{(t+1)}| + \Delta^{(t)})$
  segue $\max|u^\ast - u^{(t+1)}| \le \tfrac{q}{1-q}\,\Delta^{(t)}$ (ricavata qui dalla
  contrazione sopra): per $\lambda = 1$ la distanza dal minimo vero è al più
  $4\Delta$.
- $\Delta$ misura solo quanto si è fermata l'iterazione, **non quanto $u$ assomiglia
  all'immagine pulita**: quello si misura a parte (sezione {ref}`es06-qualita`).
- Per le misure di tempo la consegna chiede tolleranza zero: il run fa sempre lo
  stesso numero di iterazioni, quindi lo stesso lavoro, e le configurazioni si
  confrontano a parità di lavoro.

### Bordi e angoli, senza pixel fittizi

Ogni pixel usa solo i vicini che esistono davvero:

| Posizione del pixel | $d_{i,j}$ | Denominatore |
|---|---|---|
| interno | 4 | $1 + 4\lambda$ |
| bordo, non angolo | 3 | $1 + 3\lambda$ |
| angolo | 2 | $1 + 2\lambda$ |
| estremo di un'immagine di una sola riga o colonna | 1 | $1 + \lambda$ |

- **Niente cornice di zeri.** Pixel a zero attorno all'immagine sarebbero vicini
  neri inventati: aggiungerebbero all'energia termini $(u_a - 0)^2$ e trascinerebbero
  i bordi verso il nero.
- **Nemmeno una cornice che ripete il pixel stesso.** Porterebbe allo stesso minimo,
  ma con un'iterazione diversa: a parità di iterazioni i numeri non coinciderebbero
  con quelli del programma di riferimento, e il confronto a $10^{-12}$ fallirebbe.
- **In MPI il confine fra due strisce non è un bordo.** La riga ricevuta dal rank
  vicino (l'halo, sezione {ref}`es06-mpi-teoria`) contiene vicini veri, quindi
  $d_{i,j}$ dipende dalla posizione **globale** del pixel: solo la prima e l'ultima
  riga dell'immagine intera sono bordi. Per questo una striscia deve sapere da quale
  riga globale parte (`first_row` nel codice del corso).

### Esempio a mano: il caso 2 × 2 della consegna

L'immagine ha righe $(0, 1)$ e $(1, 0)$: due pixel neri e due bianchi a scacchiera,
con $\lambda = 1$. Indichiamo il pixel con (riga, colonna), partendo da (0,0) in alto
a sinistra. Il calcolo qui sotto è fatto a mano (e verificato con frazioni esatte da
[`codes/exec6/figure_2x2.py`](../../codes/exec6/README.md)), non con il programma del
corso: è la **previsione** da confrontare con il suo output.

**Passo 0: i dati.** In un'immagine 2 × 2 ogni pixel è un angolo, quindi ha
$d = 2$ primi vicini (uno in orizzontale e uno in verticale) e il denominatore è
$1 + \lambda d = 3$ per tutti. Si parte da $u^{(0)} = f$:

$$
f = u^{(0)} = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix},
\qquad
d = \begin{pmatrix} 2 & 2 \\ 2 & 2 \end{pmatrix},
\qquad
u^{(1)}_{i,j} = \frac{f_{i,j} + u^{(0)}_{\text{orizz.}} + u^{(0)}_{\text{vert.}}}{3}.
$$

**Passo 1: la prima iterazione, pixel per pixel.** Ogni pixel legge i suoi due primi
vicini **dall'array vecchio** $u^{(0)}$ e scrive il risultato **nell'array nuovo**
$u^{(1)}$; l'ordine in cui si calcolano i pixel non cambia nulla.

| Pixel | $f_{i,j}$ | Primi vicini letti da $u^{(0)}$ | Calcolo | $u^{(1)}_{i,j}$ |
|---|---|---|---|---|
| (0,0) | 0 | (0,1) = 1, (1,0) = 1 | $(0 + 1 + 1)/3$ | $2/3$ |
| (0,1) | 1 | (0,0) = 0, (1,1) = 0 | $(1 + 0 + 0)/3$ | $1/3$ |
| (1,0) | 1 | (0,0) = 0, (1,1) = 0 | $(1 + 0 + 0)/3$ | $1/3$ |
| (1,1) | 0 | (0,1) = 1, (1,0) = 1 | $(0 + 1 + 1)/3$ | $2/3$ |

```{figure} figures/es06-2x2-passo.png
:name: fig-es06-2x2-passo
:width: 100%

Prima iterazione di Jacobi sul caso 2 × 2, un pixel per colonna. Sopra: $u^{(0)}$,
con il pixel da aggiornare (blu) e i suoi primi vicini letti (arancione). Sotto:
l'array nuovo $u^{(1)}$ dopo quel pixel; il tratteggio indica i pixel non ancora
calcolati. Grigio: 0 nero, 1 bianco.
```

$$
u^{(1)} = \begin{pmatrix} 2/3 & 1/3 \\ 1/3 & 2/3 \end{pmatrix}
\approx \begin{pmatrix} 0.6667 & 0.3333 \\ 0.3333 & 0.6667 \end{pmatrix},
\qquad
\Delta^{(0)} = \max\left|u^{(1)} - u^{(0)}\right| = \tfrac{2}{3},
$$

come nella consegna. Il nero e il bianco si sono già mescolati, ma la scacchiera si
è **invertita**: i pixel che erano 0 ora sono i più chiari. È l'effetto di leggere
solo i vicini: un pixel nero con due vicini bianchi viene tirato verso il bianco più
di quanto il suo $f = 0$ lo trattenga.

**Passo 2: la seconda iterazione.** Stessa regola, ora con i vicini presi da
$u^{(1)}$:

$$
u^{(2)}_{0,0} = \frac{0 + \tfrac13 + \tfrac13}{3} = \frac{2}{9},
\qquad
u^{(2)}_{0,1} = \frac{1 + \tfrac23 + \tfrac23}{3} = \frac{7}{9},
\qquad
u^{(2)} = \begin{pmatrix} 2/9 & 7/9 \\ 7/9 & 2/9 \end{pmatrix},
\qquad
\Delta^{(1)} = \tfrac{4}{9}.
$$

**Le iterazioni successive.** Per simmetria bastano due numeri, $a = u_{0,0} = u_{1,1}$
e $b = u_{0,1} = u_{1,0}$, e l'aggiornamento diventa

$$
a^{(t+1)} = \frac{0 + 2 b^{(t)}}{3}, \qquad b^{(t+1)} = \frac{1 + 2 a^{(t)}}{3}.
$$

| $t$ | $a^{(t)}$ | $b^{(t)}$ | $\Delta^{(t)} = \max\lvert u^{(t+1)} - u^{(t)}\rvert$ |
|---|---|---|---|
| 0 | 0 | 1 | 2/3 = 0.6667 |
| 1 | 2/3 = 0.6667 | 1/3 = 0.3333 | 4/9 = 0.4444 |
| 2 | 2/9 = 0.2222 | 7/9 = 0.7778 | 8/27 = 0.2963 |
| 3 | 14/27 = 0.5185 | 13/27 = 0.4815 | 16/81 = 0.1975 |
| 4 | 26/81 = 0.3210 | 55/81 = 0.6790 | 32/243 = 0.1317 |
| 5 | 110/243 = 0.4527 | 133/243 = 0.5473 | 64/729 = 0.0878 |
| $\infty$ | 0.4 | 0.6 | 0 |

```{figure} figures/es06-2x2-iterazioni.png
:name: fig-es06-2x2-iterazioni
:width: 100%

Le prime cinque iterazioni di Jacobi sul caso 2 × 2 e il punto fisso $u^*$. Sotto
ogni matrice, la variazione massima rispetto alla precedente. I valori oscillano
attorno a 0.4 e 0.6, e l'ampiezza dell'oscillazione cala di $2/3$ a ogni passo.
```

**Il punto fisso.** Ponendo $a^{(t+1)} = a^{(t)} = a$ e $b^{(t+1)} = b^{(t)} = b$:
$a = 2b/3$ e $b = (1 + 2a)/3$, quindi $b = (1 + 4b/3)/3$, cioè $5b/3 = 1$:

$$
b = 0.6, \qquad a = 0.4, \qquad
u^* = \begin{pmatrix} 0.4 & 0.6 \\ 0.6 & 0.4 \end{pmatrix},
$$

come nella consegna. Controllo diretto con l'equazione del minimo
$(1 + \lambda d)\,u = f + \lambda \sum u_{\text{vicini}}$: per (0,0),
$3 \cdot 0.4 = 0 + 0.6 + 0.6$; per (0,1), $3 \cdot 0.6 = 1 + 0.4 + 0.4$.

**Quanto in fretta.** L'errore iniziale è

$$
e^{(0)} = u^{(0)} - u^* = \begin{pmatrix} -0.4 & 0.4 \\ 0.4 & -0.4 \end{pmatrix},
\qquad
e^{(t)} = \left(-\tfrac{2}{3}\right)^{t} e^{(0)} :
$$

a ogni passo l'errore cambia segno (l'oscillazione nella figura) e si riduce di
$2/3$, che qui è esattamente il fattore $q = \lambda d / (1 + \lambda d)$ della stima
generale. Ne segue $\Delta^{(t)} = \lvert e^{(t+1)} - e^{(t)} \rvert_{\max}
= 0.4 \cdot (2/3)^t \cdot (1 + 2/3) = (2/3)^{t+1}$, come nella tabella.

```{figure} figures/es06-2x2-delta.png
:name: fig-es06-2x2-delta
:width: 80%

Variazione massima $\Delta^{(t)}$ contro l'iterazione per il caso 2 × 2 (calcolo
teorico): in scala logaritmica è una retta di pendenza $\log_{10}(2/3)$. La linea
tratteggiata è la tolleranza $\varepsilon = 10^{-6}$ del comando della consegna.
```

Con $\varepsilon = 10^{-6}$ la prima variazione sotto soglia è
$\Delta^{(34)} = (2/3)^{35} \approx 6.9 \times 10^{-7}$, ottenuta calcolando
$u^{(35)} \approx (0.4000003, 0.5999997)$. Il programma dovrebbe quindi fermarsi
dopo **35 aggiornamenti**; se stampa 34 o 36, la differenza sta in come conta le
iterazioni, ed è il primo controllo da fare sul codice del corso.

(es06-mpi-teoria)=
### Cosa implica per la versione MPI: primi vicini e halo

Ogni rank possiede una **striscia** di righe consecutive. Per aggiornare la sua
prima riga gli servono i valori della riga subito sopra, che sta nel rank
precedente; per l'ultima, la riga subito sotto, che sta nel rank successivo. Le
copie locali di queste righe altrui si chiamano **halo** o celle fantasma: sono
righe in più allocate sopra e sotto la striscia, riempite a ogni iterazione con un
messaggio dal vicino (definizione e schema generale nel capitolo di teoria, sezione
{ref}`t7-halo`; una prima definizione è nel capitolo 6, {ref}`SPMD, comunicazioni e deadlock <t-mpi-spmd>`).

- **Quanto è spesso l'halo.** Lo stencil arriva ai *primi* vicini, quindi basta
  **una riga** per lato. Con uno stencil che usasse anche i secondi vicini ne
  servirebbero due.
- **Cosa si scambia.** Solo $u^{(t)}$, perché cambia a ogni iterazione; $f$ è fisso e
  ogni rank ha già la sua parte. Una striscia interna invia e riceve a ogni
  iterazione due righe da $W$ valori `double`, qualunque sia la sua altezza.
- **Come.** Lo scambio degli halo è **comunicazione point-to-point**: ogni messaggio
  ha un mittente e un destinatario precisi, il rank sopra o quello sotto
  ({ref}`t7-p2p`). Nessun altro rank è coinvolto.
- **Quando.** Prima di ogni aggiornamento: scambio degli halo, poi calcolo di tutta
  la striscia nell'array nuovo, poi scambio dei ruoli dei due array.
- **I rank agli estremi** hanno un solo vicino: dalla parte del bordo dell'immagine
  non c'è halo da riempire, e lì vale la regola dei bordi ($d$ più piccolo), non uno
  zero.
- **La decisione di fermarsi è globale.** Ogni rank calcola il proprio $\Delta$
  locale; il massimo su tutti i rank è il $\Delta$ dell'immagine intera, e tutti
  decidono con lo stesso valore. Questa è un'**operazione collettiva**: la chiamano
  tutti i rank del communicator, e nessuno ottiene il risultato finché non l'hanno
  chiamata tutti (riduzione `MPI_Allreduce` con `MPI_MAX`, {ref}`t7-collettive`).

**I due tipi di comunicazione, a confronto.**

| | Point-to-point | Collettiva |
|---|---|---|
| Chi partecipa | due rank: un mittente e un destinatario | tutti i rank del communicator |
| In questo esercizio | scambio degli halo con i rank vicini (`MPI_Sendrecv`) | parametri (`MPI_Bcast`), distribuzione e raccolta dell'immagine (`MPI_Scatterv`, `MPI_Gatherv`), decisione di arresto (`MPI_Allreduce`), misura del tempo (`MPI_Barrier`, `MPI_Reduce`) |
| Quanto spesso | a ogni iterazione | `MPI_Allreduce` a ogni iterazione; le altre una volta per run |
| Dati per rank | 2 righe da $W$ `double` in uscita e 2 in entrata (1 per i rank agli estremi) | 1 `double` per `MPI_Allreduce`; una striscia per `Scatterv` e `Gatherv` |
| Come cresce il costo con $p$ | non cresce: ogni rank parla solo con 2 vicini | cresce con $p$: tutti devono contribuire, tipicamente in $\log_2 p$ passi |
| Rischio tipico | deadlock se due rank si aspettano a vicenda (evitato con `MPI_Sendrecv`) | blocco se un rank non chiama l'operazione (per questo tutti escono insieme in caso di errore) |

La progettazione completa (divisione delle righe non divisibili, `MPI_Scatterv` e
`MPI_Gatherv`, ordine degli scambi) è la fase 3.

(es06-qualita)=
### Misurare la qualità: MSE (richiesto), PSNR e SSIM (aggiunta)

$\Delta$ dice quando l'iterazione si ferma, non se l'immagine è buona. Per questo si
confronta la ricostruzione $v$ con l'immagine pulita $c$ (`clean.pgm`, usata solo per
la valutazione, mai dal solutore), entrambe in $[0, 1]$ e di dimensione $H \times W$.

- **MSE** (richiesto dalla consegna):
  $\mathrm{MSE}(v, c) = \frac{1}{HW}\sum_{i,j}\left(v_{i,j} - c_{i,j}\right)^2$. Si
  calcola sia per l'immagine rumorosa ($v = f$) sia per le ricostruzioni: una buona
  ricostruzione ha MSE più basso di $f$.
- **PSNR** (aggiunta): la stessa informazione in scala logaritmica,
  $\mathrm{PSNR} = 10 \log_{10}\left(L^2 / \mathrm{MSE}\right)$ dB, con $L$ l'intervallo
  dei valori ($L = 1$ per immagini normalizzate). Più alto è meglio; non aggiunge
  informazione rispetto al MSE, ma è l'unità più usata per confrontare risultati.
- **SSIM** (aggiunta): MSE e PSNR trattano ogni pixel da solo e possono dare lo stesso
  valore a immagini che a occhio sono molto diverse. Nella Fig. 2 di
  [Wang et al. 2004](#es06-fonti) cinque versioni distorte della stessa immagine
  hanno tutte MSE = 210 (in unità a 8 bit), ma vanno da quasi indistinguibili
  dall'originale (luminosità spostata, MSSIM 0.990; contrasto aumentato, 0.917) a
  molto degradate (JPEG, 0.695; **sfocatura**, 0.705; rumore impulsivo, 0.775). La
  sfocatura è proprio il difetto che un $\lambda$ troppo grande introduce. SSIM confronta invece, in una finestra attorno a ogni pixel, media
  (luminanza), deviazione standard (contrasto) e correlazione (struttura) delle due
  immagini (§III-B, eq. 13):

  $$
  \mathrm{SSIM}(x, y) = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}
  {(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)},
  \qquad C_1 = (K_1 L)^2,\; C_2 = (K_2 L)^2,
  $$

  con $K_1 = 0.01$ e $K_2 = 0.03$. Le statistiche locali si calcolano con una finestra
  gaussiana 11 × 11 di deviazione standard 1.5 pixel, normalizzata a somma 1
  (§III-C, eq. 14–16), e il valore dell'immagine è la media delle SSIM locali (MSSIM,
  eq. 17). Vale 1 solo per immagini identiche. Per questo esercizio è interessante
  perché distingue le due cose che $\lambda$ mette in competizione: togliere il
  rumore alza la SSIM, sfocare i contorni la abbassa.

I valori misurati sono nella sezione {ref}`es06-ris-qualita`.

## Parametri

| Parametro | Valore |
|---|---|
| Programma | `denoise_serial.c` e `pgm_io.h` del corso (`/srv/data/wilson/project/hpc4ai/exercises/image-denoising/`, SHA256 `e1b6b131…` e `35ec1dd7…`), copiati in [`codes/exec6/`](../../codes/exec6/README.md) senza modifiche |
| Compilazione | `GCC/13.2.0`, `gcc -O2 -std=c11 -Wall -Wextra denoise_serial.c -lm -o denoise_serial` (comando della consegna); nessun warning |
| Precisione | `double` in memoria; i `.pgm` di uscita sono arrotondati a 8 bit solo per la visualizzazione, i `.bin` tengono i `double` |
| Immagini | `images/small` (17 × 19) e `images/medium` (2048 × 2048) del corso: immagine sintetica (fondo con gradiente 0.15–0.30, rettangolo 0.75, cerchio 0.90, barra 0.50), rumore gaussiano $\sigma = 0.30$ con seed 12345, poi **tagliato a [0, 1]** (`np.clip` in `prepare_image.py`) |
| Run della consegna | $\lambda = 1$, 200 iterazioni massime, $\varepsilon = 10^{-6}$ su small e medium; in più $\lambda = 0.2$ su medium |
| Lancio | `srun -p wilson --constraint=sandy_bridge --ntasks=1 --cpus-per-task=1 --cpu-bind=cores`; senza `-p` Slurm rifiuta la richiesta ("User's group not permitted to use this partition"). Il nome del nodo non è stato registrato |
| Prove piccole | immagine costante 3 × 4 (valore 128/255) e caso 2 × 2, scritte a mano in P2 e lanciate sul login node |
| Riferimento NumPy | [`codes/exec6/analyze_es06.py`](../../codes/exec6/README.md): stesso passo di Jacobi con le somme nello stesso ordine del C; MSE, PSNR, SSIM ($L = 1$, $K_1 = 0.01$, $K_2 = 0.03$, finestra gaussiana 11 × 11, $\sigma = 1.5$, solo finestre interne all'immagine) |

## Implementazione

### Il programma sequenziale del corso

**In breve.** `denoise_serial.c` fa esattamente il Jacobi della teoria: un array per
$f$, due array per $u$ che si scambiano a ogni iterazione, e una funzione
`jacobi_step` che aggiorna tutti i pixel e restituisce la variazione massima. È già
scritto pensando alla versione MPI: gli array di $u$ hanno una riga in più sopra e
sotto (gli halo futuri), e `jacobi_step` riceve la posizione della striscia
nell'immagine globale.

**Gli array.** Con $H$ righe e $W$ colonne:

```text
f        H righe            solo dati, mai modificato
current  H + 2 righe        riga 0 | righe 1..H = immagine | riga H+1
next     H + 2 righe        stessa forma; i ruoli si scambiano a ogni iterazione
```

Nel sequenziale le righe 0 e $H + 1$ sono allocate con `calloc` ma **non vengono mai
lette**: `jacobi_step` legge il vicino di sopra solo se `global_row > 0` e quello di
sotto solo se `global_row + 1 < height`. Non è una cornice di zeri: è spazio
riservato per gli halo della versione MPI (sezione {ref}`es06-mpi-teoria`).

**Il passo di Jacobi** (righe 25–58 del sorgente):

```c
for (int i = 1; i <= rows; ++i) {
    int global_row = first_row + i - 1;          /* riga nell'immagine intera */
    for (int j = 0; j < width; ++j) {
        size_t k = (size_t)i * width + j;
        double neighbours = 0.0;
        int count = 0;                           /* d_ij: solo vicini esistenti */
        if (global_row > 0)          { neighbours += current[k - width]; ++count; }  /* sopra    */
        if (global_row + 1 < height) { neighbours += current[k + width]; ++count; }  /* sotto    */
        if (j > 0)                   { neighbours += current[k - 1];     ++count; }  /* sinistra */
        if (j + 1 < width)           { neighbours += current[k + 1];     ++count; }  /* destra   */
        next[k] = (f[(size_t)(i - 1) * width + j] + lambda * neighbours)
                  / (1.0 + lambda * count);
        change = fmax(change, fabs(next[k] - current[k]));
    }
}
```

- Legge solo da `current` e scrive solo in `next`: è Jacobi, non Gauss–Seidel.
- `count` è il $d_{i,j}$ della teoria, calcolato dalla riga **globale**: con
  `first_row = 0` e `rows = height` è il sequenziale; in MPI la stessa funzione
  aggiorna una striscia, e la sua prima riga leggerà il vicino di sopra dalla riga 0
  di `current`, cioè dall'halo.
- `f` non ha righe in più: `f[(i - 1) * width + j]` è il dato della riga $i$.
- La variazione massima si accumula durante lo stesso ciclo, quindi costa solo un
  confronto per pixel.
- L'ordine delle somme dei vicini è fisso (sopra, sotto, sinistra, destra). La
  versione MPI deve usare la stessa funzione, altrimenti l'arrotondamento potrebbe
  cambiare l'ultimo bit e il confronto a $10^{-12}$ diventerebbe più delicato.

**Il ciclo principale** (righe 114–127):

```c
while (completed < steps) {
    change = jacobi_step(f, current, next, height, width, 0, height, lambda);
    double *temporary = current; current = next; next = temporary;   /* scambio, nessuna copia */
    ++completed;
    if (change < tolerance)          /* tolleranza zero: nessuna fermata anticipata */
        break;
}
```

`iterations` nell'output è quindi il numero di aggiornamenti fatti, e `max change` è
il $\Delta$ dell'ultimo aggiornamento. Il tempo stampato misura solo questo ciclo:
lettura e scrittura delle immagini sono fuori. Con tolleranza zero la condizione
`change < 0` non è mai vera e il programma fa sempre `steps` iterazioni, cioè lavoro
fisso, come chiede lo studio di scaling.

(es06-mpi-impl)=
### La versione MPI

**In breve.** [`denoise_mpi.c`](../../codes/exec6/README.md) ha gli stessi argomenti e
lo stesso output del sequenziale, più una riga `Ranks:`. La funzione `jacobi_step` è
**copiata identica** dal programma del corso: ogni rank la chiama sulla sua striscia,
con il proprio `first_row`. Tutto il resto è comunicazione, in quattro fasi; per
ognuna è indicato se è **point-to-point** o **collettiva** (tabella in
{ref}`es06-mpi-teoria`).

**1. Lettura e parametri — collettiva (`MPI_Bcast`).** Solo il rank 0 legge argomenti
e immagine, con gli stessi controlli del sequenziale e in più $P \le H$. Due
`MPI_Bcast`, **operazioni collettive** da uno a tutti, mandano a tutti
`{ok, height, width, steps}` e `{lambda, tolerance}`. Se qualcosa non va, `ok = 0` e
tutti i rank escono insieme, senza restare bloccati in attesa di un messaggio.

**2. Divisione in strisce — collettiva (`MPI_Scatterv`, alla fine `MPI_Gatherv`).**
Con $H = qP + r$ (quoziente $q$, resto $r$), i primi $r$
rank hanno $q + 1$ righe e gli altri $q$:

$$
\text{rows}_k = q + [k < r], \qquad \text{first\_row}_k = k\,q + \min(k, r).
$$

Ogni rank possiede quindi almeno una riga se $P \le H$, e le strisce differiscono al
più di una riga. Esempio della consegna, small (17 righe) su 3 rank: $17 = 5 \cdot 3 +
2$, quindi le righe sono 6, 6 e 5:

| rank | righe | `first_row` | righe globali | `counts` (pixel) | `displs` (pixel) |
|---|---|---|---|---|---|
| 0 | 6 | 0 | 0–5 | $6 \cdot 19 = 114$ | 0 |
| 1 | 6 | 6 | 6–11 | 114 | 114 |
| 2 | 5 | 12 | 12–16 | 95 | 228 |

`counts` e `displs` sono gli argomenti di `MPI_Scatterv` e `MPI_Gatherv`: quanti valori
vanno a ogni rank e da dove partono nell'immagine del rank 0, che è contigua per
righe. `MPI_Scatterv` (con la *v*, perché le strisce possono essere diverse) è
un'**operazione collettiva** da uno a tutti: manda a ogni rank solo la sua parte di
$f$. Alla fine `MPI_Gatherv`, **collettiva** da tutti a uno, rimette insieme le
strisce di $u$ sul rank 0. Gli altri rank allocano solo la loro striscia: $f$ con
`rows` righe, `current` e `next` con `rows + 2` (le due righe di halo).

**3. Fase iterativa — point-to-point (`MPI_Sendrecv`) e collettiva
(`MPI_Allreduce`).** A ogni iterazione:

```c
/* POINT-TO-POINT: scambio degli halo, solo con i rank sopra (up) e sotto (down) */
/* prima riga posseduta -> rank sopra; dal rank sotto -> halo inferiore (riga rows + 1) */
MPI_Sendrecv(current + width, width, MPI_DOUBLE, up, 0,
             current + (rows + 1) * width, width, MPI_DOUBLE, down, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
/* ultima riga posseduta -> rank sotto; dal rank sopra -> halo superiore (riga 0) */
MPI_Sendrecv(current + rows * width, width, MPI_DOUBLE, down, 1,
             current, width, MPI_DOUBLE, up, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
double local = jacobi_step(f, current, next, rows, width, first_row, height, lambda);
/* COLLETTIVA: tutti i rank, massimo globale della variazione */
MPI_Allreduce(&local, &change, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
/* scambio di current e next, ++completed, stop se change < tolerance */
```

```text
               scambio degli halo: comunicazione point-to-point fra rank vicini
rank k-1   ┌──────────────────────┐
           │ ...                  │
           │ ultima riga          │ ──Sendrecv (tag 1)──▶  halo superiore (riga 0) di k
           └──────────────────────┘
rank k     ┌──────────────────────┐
           │ halo sup. (riga 0)   │   copia dell'ultima riga di k-1
           │ prima riga           │ ──Sendrecv (tag 0)──▶  halo inferiore di k-1
           │ ...                  │
           │ ultima riga          │ ──Sendrecv (tag 1)──▶  halo superiore di k+1
           │ halo inf. (rows+1)   │   copia della prima riga di k+1
           └──────────────────────┘
```

- **Una riga per lato**, perché lo stencil usa solo i primi vicini (sezione
  {ref}`es06-mpi-teoria`); si scambia solo $u$, mai $f$.
- **Lo scambio è point-to-point**: ogni rank parla solo con due vicini, quindi la
  quantità di dati che invia non dipende da $p$.
- **`MPI_Sendrecv` evita il deadlock**: se ogni rank facesse prima `MPI_Send` e poi
  `MPI_Recv`, con righe abbastanza lunghe tutti resterebbero bloccati nell'invio
  (capitolo 7, {ref}`t7-p2p`; il notebook di teoria lo misura da 503 `double` in su,
  e una riga dell'immagine media ne ha 2048). Con `Sendrecv` invio e ricezione
  procedono insieme.
- **Ai bordi dell'immagine** il vicino è `MPI_PROC_NULL`: lo scambio non fa nulla e
  l'halo resta a zero, ma `jacobi_step` non lo legge, perché `global_row` è 0 o
  $H - 1$. Il rank 0 e l'ultimo non hanno casi speciali nel codice.
- **La decisione di arresto è comune**: `MPI_Allreduce` con `MPI_MAX`, unica
  **operazione collettiva** del ciclo, dà a tutti il
  massimo globale delle variazioni locali, cioè lo stesso $\Delta$ del sequenziale, e
  tutti valutano lo stesso `change < tolerance`.

**4. Tempo e uscita — collettive (`MPI_Barrier`, `MPI_Reduce`, `MPI_Gatherv`).** Prima
del ciclo una `MPI_Barrier`, **collettiva**, allinea i rank; ognuno misura il proprio
tempo con `MPI_Wtime`, e `MPI_Reduce` con `MPI_MAX`, **collettiva** da tutti a uno,
porta al rank 0 il più lento, che è il tempo della fase iterativa (scambi e riduzione compresi). Lettura,
distribuzione, raccolta e scrittura restano fuori.

**Compilazione e lancio** (su WILSON, con i moduli della consegna):

```bash
module load GCC/13.2.0 OpenMPI/4.1.6
mpicc -O2 -std=c11 -Wall -Wextra denoise_mpi.c -lm -o denoise_mpi
srun -p wilson --constraint=sandy_bridge --cpu-bind=cores -N 1 -n 4 \
    ./denoise_mpi images/medium/noisy.pgm mpi.pgm 1 200 1e-6 mpi.bin
```

(es06-scaling-impl)=
### Lo studio di scaling (fase 4)

**La domanda.** Con $p$ rank ogni striscia ha $H/p$ righe, quindi il lavoro locale per
iterazione è $\propto HW/p$, e nel caso ideale il tempo cala come $1/p$. Due cose non
calano: la comunicazione **point-to-point** degli halo (ogni rank interno invia e
riceve 2 righe da $W$ `double` per iterazione, qualunque sia $p$) e la riduzione
**collettiva** `MPI_Allreduce`, che coinvolge tutti i rank e costa di più quando $p$
cresce. In più, un'iterazione di Jacobi fa poche operazioni per byte letto, quindi
dentro un nodo può fermarsi sulla banda di memoria prima che sui core.

**Scelte, dalla consegna:**

- **lavoro fisso**: `images/large/noisy.pgm` (8192 × 8192), $\lambda = 1$, 200
  iterazioni, **tolleranza 0**. Ogni configurazione fa esattamente le stesse 200
  iterazioni, e la `MPI_Allreduce` resta in ogni iterazione anche se non può fermare
  il ciclo;
- **un rank per core fisico**: `--hint=nomultithread`, `--cpu-bind=cores`, nodi
  `sandy_bridge` in esclusiva (`--exclusive --mem=0`), prima dentro un nodo (1, 2, 4,
  8, 16 rank) e poi su più nodi (2, 4, 8 nodi da 16 rank, cioè 32, 64, 128 rank);
- **tempo**: quello stampato da `denoise_mpi`, cioè la fase iterativa (scambi e
  riduzione compresi) del rank più lento, dopo una `MPI_Barrier`. Lettura, `Scatterv`,
  `Gatherv` e scrittura sono escluse. Si riportano tempo, tempo per iterazione,
  $S_p = T_1/T_p$ ed $E_p = S_p/p$, con $T_1$ il run MPI a 1 rank;
- **ripetizioni**: 3 per configurazione; più un run del programma sequenziale del
  corso, per controllare che la versione MPI a 1 rank non costi di più;
- **correttezza durante lo scaling**: la prima ripetizione di ogni configurazione
  scrive il `.bin` (512 MB), ne calcola lo SHA256 e lo cancella. Tutti gli SHA256
  devono essere uguali, cioè risultato identico bit per bit per ogni $p$, senza tenere
  su disco un file da 512 MB per configurazione;
- **registrazione**: `sacct` (nodi, task, stato), nome e modello di CPU di ogni nodo,
  moduli, versione di `mpicc` e maschere di `--cpu-bind=verbose`.

**Stime prima di misurare**, dai dati del sequenziale su medium (8.26 ns per pixel e
iterazione su un core):

| Grandezza | Stima | Da dove viene |
|---|---|---|
| tempo per iterazione, 1 rank | 0.56 s; 200 iterazioni ≈ 111 s | $8.26\ \text{ns} \times 8192^2$ |
| memoria del rank 0 con 1 rank | 2.2 GB | immagine intera + $f$ + `current` + `next` in `double` |
| banda per core richiesta | ≈ 3.9 GB/s | circa 32 byte per pixel e iterazione (lettura di $f$ e di `current`, scrittura di `next` con write-allocate) |
| halo per rank e iterazione | 128 KB inviati, 128 KB ricevuti | 2 righe da 8192 `double` |
| dati locali a 128 rank | 12.8 MB per rank | 64 righe |

16 core per 3.9 GB/s fanno circa 62 GB/s, più dei 51 GB/s che triad ha misurato su un
nodo `sandy_bridge` nell'esercizio 3. **Previsione:** dentro un nodo lo speedup
dovrebbe crescere bene fino a qualche rank e poi rallentare, perché la banda di
memoria si satura; passando a più nodi la banda totale cresce con i nodi, e la
comunicazione resta piccola rispetto al calcolo (128 KB contro decine di MB per
iterazione). Sono previsioni da confrontare con le misure.

Script: [`scaling_job.sh`](../../codes/exec6/README.md) (il job) e `scaling.sh` (invio e
raccolta):

```bash
bash scaling.sh nodo      # 1 job: sequenziale + 1, 2, 4, 8, 16 rank su un nodo
bash scaling.sh nodi      # 3 job: 2, 4, 8 nodi da 16 rank
bash scaling.sh collect   # quando squeue è vuoto: RUN, sacct, maschere, SHA256
```

## Procedura di validazione

**Programma sequenziale.**

1. **Previsioni a mano** (sezione {ref}`Modello e teoria <es06-teoria>`): immagine
   costante invariata e ferma dopo un aggiornamento; caso 2 × 2 con
   $u^{(1)} = (2/3, 1/3; 1/3, 2/3)$, punto fisso $(0.4, 0.6; 0.6, 0.4)$ e arresto dopo
   35 aggiornamenti con $\Delta = (2/3)^{35}$.
2. **Riferimento indipendente.** Un'implementazione NumPy dello stesso passo, scritta
   a partire dalla formula e con le somme nello stesso ordine del C, deve dare gli
   stessi numeri di iterazioni e gli stessi `.bin` **bit per bit** sui casi piccoli,
   e gli stessi `.pgm` a 8 bit sull'immagine media.
3. **Qualità contro l'immagine pulita**: MSE (richiesto), PSNR e SSIM (aggiunta), per
   l'immagine rumorosa e le ricostruzioni.

**Versione MPI**, per piccoli passi, con
[`test_mpi.sh`](../../codes/exec6/README.md) e `compare_bin.c`. Ogni caso confronta il
`.bin` di `denoise_mpi` con quello di `denoise_serial` (differenza massima, soglia
$10^{-12}$ della consegna) e il numero di iterazioni e la ragione d'arresto stampati:

| Passo | Comando | Casi |
|---|---|---|
| 1. un rank | `bash test_mpi.sh uno` | 2 × 2, small (con tolleranza e a lavoro fisso), medium |
| 2. più rank, un nodo | `bash test_mpi.sh nodo` | una riga per rank (2 × 2 su 2 rank, 8 righe su 8 rank); strisce irregolari (small su 2, 3, 4, 16 rank); lavoro fisso; medium su 2, 4, 8, 16 rank, $\lambda$ = 1 e 0.2 |
| 3. più nodi | `bash test_mpi.sh nodi` | small su 17 rank e 2 nodi (una riga per rank); medium su 32 rank e 2 nodi, con tolleranza e a lavoro fisso; 18 rank su 17 righe (deve rifiutare) |

## Risultati e plot

Log: {download}`run_serial.txt <../../../results/es06/run_serial.txt>` (run della
consegna), {download}`run_tests.txt <../../../results/es06/run_tests.txt>` (prove
piccole, con i `.bin` stampati da `od`) e
{download}`listing.txt <../../../results/es06/listing.txt>` (file del corso). Tabelle
e figure:

```bash
.venv/bin/python codes/exec6/analyze_es06.py   # legge results/es06/raw/ (non versionato)
```

### 1. Il programma fa ciò che dice

**Idea.** Se il programma implementa la formula, i casi calcolabili a mano devono
tornare esatti, e un'implementazione indipendente deve dare gli stessi bit.

:::{table} Uscite di `denoise_serial` (WILSON) contro previsione a mano e riferimento NumPy (Mac).
:name: tab-es06-verifiche

| Caso | $\lambda$, iter. max, $\varepsilon$ | Uscita del programma | Previsione | max \|C − NumPy\| |
|---|---|---|---|---|
| costante 3 × 4 (128/255) | 1, 200, $10^{-6}$ | 1 iterazione, max change 0, *tolerance*; tutti i valori 0.5019607843137255 | invariata, ferma subito | 0 |
| 2 × 2, una iterazione | 1, 1, 0 | max change 0.666666666667, *iteration limit*; (0.6666666666666666, 0.3333333333333333; …) | $(2/3, 1/3; 1/3, 2/3)$, $\Delta^{(0)} = 2/3$ | 0 |
| 2 × 2, a convergenza | 1, 200, $10^{-6}$ | **35** iterazioni, max change 6.86761488122e-07, *tolerance*; (0.4000002747045952, 0.5999997252954047; …) | 35 aggiornamenti, $(2/3)^{35} = 6.868 \times 10^{-7}$, $0.4 + 0.4\,(2/3)^{35}$ | 0 |
| small 17 × 19 | 1, 200, $10^{-6}$ | 44 iterazioni, max change 9.37653652833e-07, *tolerance* | — | 0 |
| medium, $\lambda = 1$ | 1, 200, $10^{-6}$ | 53 iterazioni, max change 9.41714581926e-07 | — | `.pgm` identico a 8 bit |
| medium, $\lambda = 0.2$ | 0.2, 200, $10^{-6}$ | 16 iterazioni, max change 6.12660595811e-07 | — | `.pgm` identico a 8 bit |
:::

Tutte le previsioni della teoria sono confermate, compreso il conteggio di 35
aggiornamenti, e il riferimento NumPy riproduce numeri di iterazioni e valori dei
`.bin` con differenza **zero**. Sull'immagine media sono stati scaricati solo i `.pgm`
(i `.bin` da 33 MB sono rimasti su WILSON): coincidono pixel per pixel con quelli
ricostruiti da NumPy.

### 2. Iterazioni contro $\lambda$

**Idea.** La teoria dice che l'errore cala almeno di $q = 4\lambda/(1 + 4\lambda)$ a
ogni passo e che sulle componenti lisce la stima è quasi esatta. Se è così, il numero
di iterazioni $n$ per arrivare a $\varepsilon$ cresce come $1/(-\ln q) \approx
1 + 4\lambda$, e il prodotto $n\,(-\ln q)$ resta circa costante.

:::{table} Iterazioni per arrivare a $\Delta < 10^{-6}$ sull'immagine media. $\lambda$ = 0.2 e 1: programma del corso; gli altri: riferimento NumPy (identico al programma, sezione precedente), con 200 iterazioni massime fino a $\lambda = 2$ e 10 000 oltre.
:name: tab-es06-iterazioni

| $\lambda$ | 0.05 | 0.1 | 0.2 | 0.5 | 1 | 2 | 5 | 10 | 20 | 50 |
|---|---|---|---|---|---|---|---|---|---|---|
| $q$ | 0.167 | 0.286 | 0.444 | 0.667 | 0.800 | 0.889 | 0.952 | 0.976 | 0.988 | 0.995 |
| iterazioni $n$ | 8 | 11 | **16** | 30 | **53** | 97 | 227 | 433 | 828 | 1972 |
| $n\,(-\ln q)$ | 14.3 | 13.8 | 13.0 | 12.2 | 11.8 | 11.4 | 11.1 | 10.7 | 10.3 | 9.8 |
:::

Da $\lambda = 0.05$ a 50 le iterazioni crescono di 250 volte, ma $n\,(-\ln q)$ resta
fra 10 e 14, vicino a $\ln(10^6) = 13.8$: la velocità di convergenza osservata è
quella prevista dalla stima con $q$, e i run della consegna ($n$ = 16 e 53) stanno
sotto i limiti a priori di 18 e 62 iterazioni.

(es06-ris-qualita)=
### 3. Qualità delle ricostruzioni

**Idea.** Più $\lambda$ è grande, più rumore si toglie, ma più si sfocano i contorni.
MSE e PSNR misurano lo scarto pixel per pixel; SSIM misura quanto si somigliano le
strutture locali.

:::{table} Immagine media 2048 × 2048 contro `clean.pgm`, valori in $[0, 1]$. $\lambda$ = 0.2 e 1 sono i run del programma del corso (valori `double` ricalcolati con il riferimento NumPy, identico a 8 bit); gli altri sono solo del riferimento NumPy. In grassetto il minimo del MSE nella scansione.
:name: tab-es06-qualita

| Immagine | MSE | PSNR (dB) | MSSIM |
|---|---|---|---|
| rumorosa (input) | 0.05987 | 12.23 | 0.022 |
| $\lambda = 0.05$ | 0.04305 | 13.66 | 0.030 |
| $\lambda = 0.1$ | 0.03348 | 14.75 | 0.038 |
| $\lambda = 0.2$ | 0.02312 | 16.36 | 0.054 |
| $\lambda = 0.5$ | 0.01220 | 19.14 | 0.108 |
| $\lambda = 1$ | 0.00732 | 21.35 | 0.202 |
| $\lambda = 2$ | 0.00474 | 23.24 | 0.371 |
| $\lambda = 5$ | 0.00330 | 24.82 | 0.662 |
| $\lambda = 10$ | 0.00295 | 25.30 | 0.831 |
| $\lambda = 20$ | **0.00292** | **25.34** | 0.917 |
| $\lambda = 50$ | 0.00321 | 24.94 | 0.955 |
:::

```{figure} figures/es06-ricostruzioni.png
:name: fig-es06-ricostruzioni
:width: 100%

Immagine pulita, rumorosa (input del solutore) e ricostruzioni con $\lambda$ = 0.2,
1 (run della consegna) e 20 (minimo del MSE nella scansione). Sotto: ingrandimento
del riquadro arancione (angolo del rettangolo e inizio della barra), 410 × 410 pixel.
```

```{figure} figures/es06-qualita-lambda.png
:name: fig-es06-qualita-lambda
:width: 100%

MSE, PSNR e MSSIM contro $\lambda$ (scala logaritmica). Linea tratteggiata: immagine
rumorosa. Cerchi arancioni: i due valori della consegna.
```

```{figure} figures/es06-profilo.png
:name: fig-es06-profilo
:width: 100%

Profilo attraverso i due bordi verticali del rettangolo, mediato sulle righe 614–818
(dove il bordo è verticale): la media su 205 righe riduce il rumore di circa 14 volte
e lascia la forma media del bordo.
```

```{figure} figures/es06-ssim-mappe.png
:name: fig-es06-ssim-mappe
:width: 100%

Mappe SSIM locali (finestra gaussiana 11 × 11) rispetto all'immagine pulita: chiaro =
struttura simile, scuro = diversa.
```

:::{table} Larghezza dei bordi del rettangolo: pixel in cui il profilo medio passa dal 10% al 90% del salto.
:name: tab-es06-bordi

| | pulita | rumorosa | $\lambda = 0.2$ | $\lambda = 1$ | $\lambda = 20$ |
|---|---|---|---|---|---|
| bordo sinistro | 0 | 0 | 2 | 3 | 13 |
| bordo destro | 0 | 0 | 2 | 3 | 14 |
:::

### 4. Prima misura di tempo

| $\lambda$ | Iterazioni | Tempo del ciclo (s) | Per iterazione | Per pixel e iterazione |
|---|---|---|---|---|
| 1 | 53 | 1.837 | 34.66 ms | 8.3 ns |
| 0.2 | 16 | 0.555 | 34.68 ms | 8.3 ns |

Il costo di un'iterazione non dipende da $\lambda$, come atteso: il lavoro per pixel è
lo stesso. È una sola misura per caso, su un core di un nodo `sandy_bridge` non
registrato: serve solo come ordine di grandezza per scegliere le dimensioni dello
scaling (fase 4).

### 5. Validazione della versione MPI

**Idea.** `denoise_mpi` usa la stessa `jacobi_step` e riceve negli halo gli stessi
valori che il sequenziale legge dai vicini, quindi fa le stesse operazioni nello
stesso ordine: la differenza dal sequenziale dovrebbe essere zero, non solo sotto
$10^{-12}$.

**Sul Mac** (Apple M3 Pro, Open MPI 5.0.11, `mpicc` con Apple clang 21.0.0, `-O2
-ffp-contract=off` per entrambi i programmi; `mpirun --oversubscribe`, quindi fino a
32 rank su 12 core: valida la correttezza, non dice nulla sui tempi):

:::{table} `bash test_mpi.sh uno|nodo|nodi` sul Mac: 20 casi su 20 con stesse iterazioni, stessa ragione d'arresto e differenza massima 0.
:name: tab-es06-mpi-mac

| Caso | Rank (righe per rank) | Iterazioni, arresto | max \|MPI − seriale\| |
|---|---|---|---|
| 2 × 2 | 1 (2), 2 (1) | 35, tolerance | 0 |
| 8 righe di small | 8 (1) | 42, tolerance | 0 |
| small 17 × 19 | 1 (17), 2 (8–9), 3 (5–6), 4 (4–5), 16 (1–2), 17 (1) | 44, tolerance | 0 |
| small, lavoro fisso | 1, 3, 16 | 200, iteration limit | 0 |
| medium, $\lambda = 1$ | 1, 2, 4, 8, 16, 32 (64–2048) | 53, tolerance | 0 |
| medium, $\lambda = 0.2$ | 16 (128) | 16, tolerance | 0 |
| medium, lavoro fisso (50 iterazioni) | 32 (64) | 50, iteration limit | 0 |
| small su 18 rank | — | rifiutato: `Require 1 <= number of ranks <= image height` | — |
:::

**Su WILSON** (`GCC/13.2.0`, `OpenMPI/4.1.6`, `mpicc -O2 -std=c11 -Wall -Wextra`;
`srun -p wilson --constraint=sandy_bridge --cpu-bind=cores`, con `-N 1` per i passi 1
e 2 e `-N 2` per il passo 3) i tre comandi danno lo stesso esito: **20 casi su 20**
con le stesse iterazioni e la stessa ragione d'arresto del sequenziale e differenza
massima 0, e il rifiuto di 18 rank per 17 righe. Log:
{download}`test_uno.txt <../../../results/es06/test_uno.txt>`,
{download}`test_nodo.txt <../../../results/es06/test_nodo.txt>`,
{download}`test_nodi.txt <../../../results/es06/test_nodi.txt>` (copiati dal terminale).

Nel passo 3 i 17 rank stanno su due nodi diversi: `hostname` lanciato con la stessa
richiesta dà 15 rank su `wnode07` e 2 su `wnode08`. Slurm riempie prima un nodo e
mette sul secondo il resto. La striscia di confine fra i due nodi viaggia quindi
sulla rete, e il risultato resta identico. I nodi dei passi 1 e 2 e dei run a 32
rank non sono stati registrati.

## Commenti

1. **Il programma del corso è corretto** sui casi verificabili: costante, 2 × 2 a
   una iterazione e a convergenza (35 aggiornamenti, come previsto), e il riferimento
   NumPy lo riproduce bit per bit. Il riferimento servirà anche per controllare la
   versione MPI.
2. **La teoria della convergenza regge**: le iterazioni crescono come
   $1/(-\ln q) \approx 1 + 4\lambda$ su tre ordini di grandezza di $\lambda$
   (tabella {numref}`tab-es06-iterazioni`).
3. **Con questo rumore i due $\lambda$ della consegna smussano poco.** Con
   $\sigma = 0.30$ il MSE scende fino a $\lambda \approx 20$ (0.00292, 25.3 dB) e poi
   risale (0.00321 a $\lambda = 50$): è il compromesso fra rumore tolto e contorni
   sfocati. La sfocatura si vede nei profili: il bordo, netto nell'immagine pulita,
   si allarga a 2, 3 e 13–14 pixel per $\lambda$ = 0.2, 1 e 20.
4. **Un limite che il denoising non può togliere: il rumore tagliato.**
   `prepare_image.py` taglia l'immagine rumorosa a $[0, 1]$, quindi il rumore non ha
   più media zero vicino a 0 e a 1. Sui profili la media della rumorosa sta sopra la
   pulita sul fondo scuro e sotto nel rettangolo. Misurato su zone piatte: +0.059 sul
   fondo (0.158), −0.033 nel rettangolo (0.749), −0.078 nel cerchio (0.902), −0.004
   nella barra (0.502). Sono gli scarti previsti per una gaussiana di
   $\sigma = 0.30$ tagliata a $[0, 1]$ (+0.057, −0.033, −0.077, −0.000). Uno smussamento
   lineare conserva le medie locali, quindi questo scarto resta: da solo vale un MSE
   di 0.0019, circa 2/3 del migliore ottenuto (0.0029).
5. **SSIM racconta un'altra parte della storia.** Le mappe smentiscono la previsione
   scritta prima delle misure, cioè che la SSIM sarebbe calata soprattutto lungo i
   contorni: con poco smussamento è il contrario. Nelle zone piatte l'immagine pulita
   non ha struttura, e la SSIM confronta di fatto il rumore residuo con la costante
   $C_2$: finché resta rumore è vicina a zero, mentre sui contorni la struttura c'è e
   la correlazione con la pulita è alta. Solo con $\lambda = 20$, quando il rumore è
   quasi sparito, i contorni diventano la zona peggiore (l'anello nella mappa).
   Per questo la MSSIM continua a salire fino a $\lambda = 50$, mentre il MSE ha già
   ricominciato a peggiorare: le due misure non sono d'accordo sul $\lambda$
   migliore, e la MSSIM qui è dominata dalle grandi zone piatte.

## Checkpoint

- Teoria del modello, dell'aggiornamento di Jacobi, della convergenza e dei bordi
  scritta; caso 2 × 2 ricavato a mano e confermato dal programma (35 aggiornamenti).
- `denoise_serial` verificato: costante, 2 × 2, small e medium coincidono con il
  riferimento NumPy (differenza zero).
- Qualità su medium: MSE da 0.0599 (rumorosa) a 0.0231 ($\lambda = 0.2$) e 0.0073
  ($\lambda = 1$); minimo 0.0029 a $\lambda \approx 20$, di cui circa 0.0019 dovuto al
  taglio del rumore.
- `denoise_mpi` (strisce con `Scatterv`/`Gatherv` collettive, halo con `Sendrecv`
  point-to-point, arresto con `Allreduce` collettiva)
  identico al sequenziale in 20 casi su 20, sul Mac e su WILSON fino a 2 nodi
  (`wnode07`, `wnode08`); lo scaling (fase 4) è da fare.

(es06-domande)=
## Domande d'esame

Domande per ripassare l'esercizio in vista dell'orale, con la risposta nascosta.

:::{dropdown} 1. Perché `current` e `next` hanno $H + 2$ righe, e perché nel sequenziale la riga 0 e la riga $H + 1$ non vengono mai lette?

Le due righe in più sono lo spazio per gli **halo** della versione MPI: la riga 0
conterrà la copia dell'ultima riga del rank di sopra, la riga $H + 1$ (in MPI,
`rows + 1`) quella della prima riga del rank di sotto. Nel sequenziale non ci sono
rank vicini e la prima e l'ultima riga sono bordi veri dell'immagine:
`jacobi_step` legge il vicino di sopra solo se `global_row > 0` e quello di sotto
solo se `global_row + 1 < height`, quindi le righe extra (azzerate da `calloc`) non
entrano mai nel calcolo. Non sono una cornice di zeri: se lo fossero, i bordi
verrebbero tirati verso il nero.

:::

:::{dropdown} 2. Dove compaiono `first_row` e `count`, e perché servono alla versione MPI?

`first_row` è la riga globale da cui parte la striscia; `global_row = first_row + i - 1`
dice a quale riga dell'immagine intera corrisponde la riga locale `i`. `count` è il
numero di vicini esistenti $d_{i,j}$, che entra nel denominatore $1 + \lambda d$. In MPI
ogni rank aggiorna solo la sua striscia, ma i bordi dell'immagine sono solo la prima
e l'ultima riga **globali**: grazie a `first_row` la prima riga di una striscia
interna ha 4 vicini (uno nell'halo) e non 3, e il risultato coincide con il
sequenziale. Con `first_row = 0` e `rows = height` la stessa funzione è il
sequenziale.

:::

:::{dropdown} 3. Come si verifica che il programma sequenziale è corretto, senza fidarsi del codice?

Con casi la cui risposta si conosce senza il programma: un'immagine costante deve
restare invariata e fermarsi al primo aggiornamento ($\Delta = 0$); il caso 2 × 2 si
calcola a mano: $(2/3, 1/3; 1/3, 2/3)$ dopo un passo, punto fisso $(0.4, 0.6; 0.6, 0.4)$,
$\Delta^{(t)} = (2/3)^{t+1}$ e quindi 35 aggiornamenti per scendere sotto $10^{-6}$. Il
programma ha dato esattamente questi numeri. In più un'implementazione indipendente
in NumPy, con le somme nello stesso ordine, ha riprodotto i `.bin` con differenza
zero e i `.pgm` dell'immagine media pixel per pixel.

:::

:::{dropdown} 4. Perché il confronto con NumPy può dare differenza esattamente zero, e quando non lo darebbe?

Perché entrambi fanno le stesse operazioni IEEE in `double` nello stesso ordine:
somma dei vicini sopra, sotto, sinistra, destra, poi $(f + \lambda\,n)/(1 + \lambda d)$.
Sommare 0.0 per un vicino assente è esatto, quindi le maschere di NumPy non cambiano
l'ordine. La differenza non sarebbe zero cambiando l'ordine delle somme, oppure con
un compilatore che fonde moltiplicazione e somma in una sola istruzione (FMA, per
esempio con `-ffp-contract` attivo su ARM): l'errore resterebbe dell'ordine di
$10^{-16}$, ben sotto la soglia $10^{-12}$ della consegna.

:::

:::{dropdown} 5. Con $\sigma = 0.30$, perché il MSE ha un minimo vicino a $\lambda = 20$ e non scende sotto circa 0.003?

Aumentando $\lambda$ si toglie più rumore, ma i contorni si allargano (2, 3 e 13–14
pixel per $\lambda$ = 0.2, 1 e 20): oltre $\lambda \approx 20$ l'errore sui contorni
supera il guadagno sul rumore e il MSE risale. Il pavimento viene in gran parte dal
**taglio del rumore a [0, 1]** in `prepare_image.py`: vicino a 0 e a 1 il rumore tagliato
non ha media zero, la media dell'immagine rumorosa è spostata (+0.059 sul fondo,
−0.078 nel cerchio) e uno smussamento lineare conserva le medie locali. Questo scarto
vale da solo un MSE di 0.0019 su 0.0029.

:::

:::{dropdown} 6. Perché MSE e MSSIM non sono d'accordo sul $\lambda$ migliore?

Nelle zone piatte l'immagine pulita non ha struttura, e la SSIM confronta di fatto il
rumore residuo con la costante $C_2 = (0.03)^2$: finché resta un po' di rumore vale
quasi zero, e appena il rumore sparisce sale verso 1. Siccome le zone piatte sono
quasi tutta l'immagine, la MSSIM continua a crescere con $\lambda$ anche quando il MSE
peggiora per la sfocatura dei contorni. Le mappe SSIM mostrano la sfocatura solo
quando il rumore è quasi sparito ($\lambda = 20$): lì i contorni diventano la zona
peggiore.

:::

:::{dropdown} 7. Perché le iterazioni crescono come $1 + 4\lambda$?

L'errore si riduce almeno del fattore $q = 4\lambda/(1+4\lambda)$ a ogni passo, quindi
servono circa $\ln(\Delta_0/\varepsilon)/(-\ln q)$ iterazioni, e
$-1/\ln q \approx 1 + 4\lambda$ per $\lambda$ grande. Le misure lo confermano: da
$\lambda = 0.05$ a 50 le iterazioni crescono di 250 volte, ma $n\,(-\ln q)$ resta fra
10 e 14.

:::

:::{dropdown} 8. Quali comunicazioni della versione MPI sono point-to-point e quali collettive?

**Point-to-point** è solo lo scambio degli halo: due `MPI_Sendrecv` per iterazione,
ognuno fra un rank e un suo vicino (sopra o sotto). **Collettive** sono tutte le altre:
`MPI_Bcast` per dimensioni e parametri, `MPI_Scatterv` e `MPI_Gatherv` per
distribuire $f$ e raccogliere $u$, `MPI_Allreduce` con `MPI_MAX` a ogni iterazione per
la decisione di arresto, `MPI_Barrier` e `MPI_Reduce` per misurare il tempo. La
divisione segue il problema: lo stencil ha bisogno solo dei primi vicini, quindi
basta parlare con i rank accanto; l'arresto dipende dall'immagine intera, quindi
deve coinvolgere tutti.

:::

:::{dropdown} 9. Come si calcolano `rows` e `first_row` di ogni rank, e perché serve $P \le H$?

Con $H = qP + r$ i primi $r$ rank hanno $q + 1$ righe e gli altri $q$, e
`first_row` del rank $k$ è $kq + \min(k, r)$. Le strisce sono contigue, coprono tutte
le righe e differiscono al più di una riga. Se $P > H$ si avrebbe $q = 0$ e alcuni rank
senza righe: la consegna lo esclude, e il programma lo rifiuta con un messaggio
prima di iniziare.

:::

:::{dropdown} 10. Cosa sono `counts` e `displs` in `MPI_Scatterv` e `MPI_Gatherv`?

Due array di $P$ interi, in numero di **valori** (pixel), non di righe: `counts[k]` è
quanti `double` vanno al rank $k$ (`rows_k * width`), `displs[k]` dove iniziano
nell'immagine del rank 0 (`first_row_k * width`). Servono le versioni con la *v*
perché le strisce possono avere altezze diverse; `MPI_Scatter` e `MPI_Gather`
richiedono la stessa quantità per ogni rank.

:::

:::{dropdown} 11. Perché si scambia una sola riga per lato, solo $u$ e mai $f$, e perché con `MPI_Sendrecv`?

Una riga perché lo stencil usa solo i primi vicini; solo $u$ perché $f$ non cambia e
ogni rank ha già la sua parte dopo `MPI_Scatterv`. `MPI_Sendrecv` perché se ogni rank
facesse `MPI_Send` e poi `MPI_Recv`, con messaggi oltre il limite eager (nel notebook
di teoria 503 `double`; una riga dell'immagine media ne ha 2048) tutti resterebbero
bloccati nell'invio aspettando un ricevente: deadlock.

:::

:::{dropdown} 12. Perché nessun rank può fermarsi sul proprio test di convergenza?

Perché il criterio riguarda l'immagine intera: una striscia già ferma può ancora
cambiare se cambiano le righe dei vicini, che entrano nei suoi halo. In più, se un
rank uscisse dal ciclo, i vicini resterebbero bloccati nel `MPI_Sendrecv` e tutti gli
altri nella `MPI_Allreduce` successiva. Con il massimo globale tutti i rank hanno lo
stesso `change` e prendono la stessa decisione nella stessa iterazione.

:::

:::{dropdown} 13. Perché per lo scaling si usa tolleranza 0, e cosa resta della decisione di arresto?

Con tolleranza 0 la condizione `change < 0` non è mai vera, quindi ogni configurazione
fa esattamente le stesse 200 iterazioni: stesso lavoro, e il rapporto fra i tempi è
uno speedup vero. Con una tolleranza positiva il numero di iterazioni dipenderebbe
dal criterio, non dal numero di rank, e non si confronterebbero cose uguali. La
`MPI_Allreduce` resta comunque a ogni iterazione, perché fa parte del costo reale
dell'algoritmo parallelo, anche se il suo risultato non può fermare il ciclo.

:::

:::{dropdown} 14. Perché si riporta il tempo del rank più lento, e perché si esclude la lettura e scrittura delle immagini?

Il programma finisce quando finisce l'ultimo rank, e a ogni iterazione la
`MPI_Allreduce` costringe tutti ad aspettare il più lento: il massimo sui rank è il
tempo che si osserva davvero. La `MPI_Barrier` prima di far partire il cronometro
evita di contare l'attesa di chi parte tardi. Lettura, distribuzione, raccolta e
scrittura sono fatte dal solo rank 0 e non dipendono dal numero di rank, quindi
nasconderebbero lo scaling della parte che si vuole studiare, cioè la fase iterativa.

:::

:::{dropdown} 15. Perché la comunicazione point-to-point per rank non cresce con $p$, mentre la riduzione collettiva sì?

Ogni rank interno scambia sempre due righe da $W$ `double` con due vicini (128 KB
inviati per iterazione con $W = 8192$), qualunque sia $p$: aumentando i rank diminuisce
il lavoro locale, ma non i dati di confine. Il rapporto fra comunicazione e calcolo
quindi **peggiora** con $p$, anche se la comunicazione per rank resta costante. La
`MPI_Allreduce` invece deve combinare un valore da ognuno dei $p$ rank e restituire il
risultato a tutti: tipicamente servono circa $\log_2 p$ passi di messaggi, quindi il
suo costo cresce con $p$, e attraversa la rete quando i rank sono su più nodi.

:::

:::{dropdown} 16. Perché dentro un nodo ci si aspetta che lo speedup rallenti prima dei 16 rank?

Un'iterazione di Jacobi legge e scrive circa 32 byte per pixel (lettura di $f$ e di
`current`, scrittura di `next` con write-allocate) e fa pochissime operazioni per
byte: è limitata dalla memoria. Dal sequenziale (8.26 ns per pixel) ogni core chiede
circa 3.9 GB/s; 16 core ne chiederebbero circa 62 GB/s, più dei 51 GB/s che triad ha
misurato su un nodo `sandy_bridge` nell'esercizio 3. Quando la banda è satura,
aggiungere core sullo stesso nodo non accelera più; aggiungere nodi sì, perché ogni
nodo porta la sua banda. È una previsione, da confrontare con le misure.

:::

(es06-fonti)=
## Fonti

- Y. Saad, *Iterative Methods for Sparse Linear Systems*, 2ª ed., SIAM, 2003
  (copia gratuita dell'autore:
  <https://www-users.cse.umn.edu/~saad/IterMethBook_2ndEd.pdf>). Usati: §4.1
  (Jacobi, eq. 4.4–4.5; Gauss–Seidel, eq. 4.6), §4.2.1 (Teorema 4.1, Corollario
  4.2), §4.2.3 (Definizione 4.5, Teorema 4.9, pp. 119–122), §12.4.1 (red–black),
  §13.1 (pp. 423–424).
- Z. Wang, A. C. Bovik, H. R. Sheikh, E. P. Simoncelli, "Image quality assessment:
  from error visibility to structural similarity", *IEEE Transactions on Image
  Processing* 13(4), 600–612, 2004, doi:10.1109/TIP.2003.819861 (copia degli autori:
  <https://www.cns.nyu.edu/pub/eero/wang03-reprint.pdf>). Usati: §I (MSE e PSNR),
  Fig. 2, §III-B (eq. 6–13), §III-C (finestra gaussiana, eq. 14–17), Fig. 8
  ($K_1$, $K_2$).
- K. He, X. Zhang, S. Ren, J. Sun, "Deep Residual Learning for Image Recognition",
  *CVPR 2016*, 770–778, doi:10.1109/CVPR.2016.90 (copia in
  `materials/He_2016_Deep_Residual_Learning_CVPR.pdf`). Usato: §2, paragrafo sul
  multigrid. È il riferimento [1] dell'esercizio 7.
