# Riferimento OpenMP

OpenMP esprime parallelismo a memoria condivisa: più thread cooperano sullo stesso
spazio di indirizzi. `-fopenmp` abilita le direttive e collega la libreria runtime;
`OMP_NUM_THREADS` sceglie il numero di thread.

```bash
gcc -fopenmp -o prog prog.c
OMP_NUM_THREADS=4
export OMP_NUM_THREADS
./prog
```

Esempio: contare i thread attivi.

```c
#include <omp.h>
#include <stdio.h>

int main(void)
{
    int thread_count = 1;

#pragma omp parallel
    {
#pragma omp single
        thread_count = omp_get_num_threads();
    }

    printf("OpenMP used %d thread(s)\n", thread_count);
    return 0;
}
```

```bash
gcc -fopenmp -o thread-count thread-count.c
OMP_NUM_THREADS=4 ./thread-count
# OpenMP used 4 thread(s)
```

| Comando | Scopo |
|---|---|
| `gcc -fopenmp -o prog prog.c` | compila con OpenMP |
| `OMP_NUM_THREADS=4` + `export` | imposta il numero di thread |
| `./prog` | esegue |
