# Compilazione C/C++

Un compilatore traduce il sorgente in un eseguibile. Compilare ed eseguire sono
passi separati: gli errori del compilatore riguardano la traduzione, quelli di
`./prog` avvengono durante l'esecuzione.

```bash
gcc -o prog prog.c                  # C
g++ -o prog prog.cpp                # C++
gcc -Wall -Wextra -o prog prog.c    # con warning completi
gcc -lm -o prog prog.c              # se il codice usa <math.h>
./prog                              # esegue nella directory corrente
```

| Comando | Scopo |
|---|---|
| `gcc -o prog prog.c` | compila C |
| `g++ -o prog prog.cpp` | compila C++ |
| `gcc -Wall -Wextra ...` | abilita i warning utili |
| `gcc -lm ...` | collega la libreria matematica |
| `./prog` | esegue l'eseguibile |

`-o prog` sceglie il nome dell'output; se la compilazione riesce il compilatore non
stampa nulla. `#include <math.h>` fornisce le dichiarazioni, `-lm` chiede al linker
la libreria: le due cose sono separate. Per distinguere sorgente ed eseguibile:

```bash
ls -l prog.c prog
file prog.c prog
```
