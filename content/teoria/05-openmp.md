# Parallelismo a thread e OpenMP

:::{seealso} Fonte principale
Capitolo 5 del corso, [*Thread parallelism and OpenMP*](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/openmp.html). Questa pagina riordina le note già scritte secondo la struttura di quel capitolo.
:::

(shared-memory-openmp)=
## Shared-memory e OpenMP

**Shared-memory** significa memoria condivisa: i thread dello stesso processo possono accedere alle stesse aree di memoria. Le variabili condivise richiedono attenzione quando più thread le modificano.

**OpenMP** permette di usare più thread all'interno di ciascun processo, tipicamente tramite direttive nel codice. `OMP_NUM_THREADS` richiede un numero di thread, ma l'effettiva esecuzione dipende dalle risorse assegnate e dalla configurazione del runtime. Non implica che ogni thread abbia una CPU distinta.

Una *race condition* si verifica quando il risultato dipende dall'ordine temporale di accessi concorrenti. Per esempio, più thread che incrementano la stessa variabile senza sincronizzazione possono perdere aggiornamenti. Una riduzione o un'altra sincronizzazione appropriata protegge il risultato; lock e barriere, se usati troppo spesso, aggiungono costo.

Questo esempio crea un team OpenMP e stampa il numero dei thread una sola volta:

```c
#include <omp.h>
#include <stdio.h>

int main(void)
{
#pragma omp parallel
    {
#pragma omp single
        printf("Thread nel team: %d\n", omp_get_num_threads());
    }
    return 0;
}
```

(t-openmp-forkjoin)=
### Fork-join, direttive e clausole

Una API per il parallelismo a memoria condivisa in C, C++ e Fortran. Il
programma parte come un solo thread (il *master*); in una regione parallela
viene creato un *team* di thread, e il master si ricongiunge a loro alla fine.
È il modello **fork-join**.

Direttive principali: `parallel`, `parallel for`, `critical`, `atomic`,
`barrier`, `single`, `master`, `task`.

Clausole principali: `private(x)`, `shared(x)`, `firstprivate(x)`,
`reduction(op:x)`, `schedule(static|dynamic|guided, chunk)`, `default(none)`.

La `reduction` è il modo corretto di sommare o di prendere un massimo in
parallelo: ogni thread accumula in una copia privata e le copie vengono
combinate alla fine. Senza, gli aggiornamenti concorrenti della stessa
variabile sono una race condition.

```bash
gcc -fopenmp -o prog prog.c
OMP_NUM_THREADS=4 ./prog
```

Anche il false sharing compare qui: contatori tenuti vicini in un array sono
condivisi fra thread; separarli su linee diverse con il padding.

Vedi [reference/openmp](../reference/openmp.md).
