# Compilazione C/C++

Compilazione ed esecuzione sono fasi separate. Il compilatore traduce il sorgente; l'eseguibile viene avviato successivamente dalla shell.

```bash
gcc -Wall -Wextra -o prog prog.c
g++ -Wall -Wextra -o prog prog.cpp
./prog
```

Adatta il nome del file sorgente e quello dell'eseguibile. `-o prog` sceglie il nome dell'output. Se il programma usa funzioni matematiche C che richiedono la libreria matematica, il collegamento può richiedere `-lm`:

```bash
gcc -Wall -Wextra -o prog prog.c -lm
```

Per compilare codice OpenMP o MPI e scegliere moduli e ambiente di esecuzione, consulta la [guida WILSON](../workflow/lab-client-wilson.md).
