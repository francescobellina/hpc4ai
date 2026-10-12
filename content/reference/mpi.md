# Riferimento MPI

MPI esprime parallelismo a memoria distribuita: ogni processo ha il proprio spazio
di indirizzi e scambia messaggi espliciti. Su WILSON servono prima un compilatore e
un'implementazione MPI (vedi [Riferimento Lmod](lmod.md)).

```bash
module load GCC/13.2.0
module load OpenMPI/4.1.6
mpicc -o prog prog.c        # C
mpicpp -o prog prog.cpp     # C++
mpicc --showme              # invocazione reale, include e librerie
mpiexec -c 4 ./prog         # esegue 4 processi
```

| Comando | Scopo |
|---|---|
| `mpicc -o prog prog.c` | compila C con MPI |
| `mpicpp -o prog prog.cpp` | compila C++ con MPI |
| `mpicc --showme` | mostra le opzioni aggiunte dal wrapper |
| `mpiexec -c 4 ./prog` | avvia 4 processi |

I wrapper `mpicc`/`mpicpp` invocano il compilatore sottostante con le opzioni MPI
richieste.
