# Esercizio 1.4 — Hello, World!

## Obiettivo

Seguire il percorso completo dal codice sorgente a un programma in esecuzione: il
programma è minuscolo, così ogni comando e ogni file del processo resta chiaro.
Ripeti la sequenza sia sul client sia su WILSON, per confrontare i due ambienti.

## 1. Versione C

Un programma C minimo richiede la dichiarazione di `printf`, una funzione `main` e
un valore di ritorno corretto:

```c
#include <stdio.h>

int main(void)
{
    printf("Hello, world!\n");
    return 0;
}
```

Salva il sorgente come `hello_world.c`, poi compila ed esegui:

```bash
gcc -Wall -Wextra -o hello_world hello_world.c
./hello_world
# Hello, world!
```

`-o hello_world` sceglie il nome del file di output; `./` dice alla shell di
eseguire l'eseguibile nella directory corrente. Se la compilazione riesce, il
compilatore di norma non stampa nulla.

Ispeziona i due file:

```bash
ls -l hello_world.c hello_world
file hello_world.c hello_world
```

## 2. Versione script

Uno script di shell passa il testo direttamente a `echo`:

```bash
#!/usr/bin/env bash
echo "Hello, world!"
```

Salvalo come `hello_world.sh`, rendilo eseguibile ed esegui:

```bash
chmod +x hello_world.sh
./hello_world.sh
# Hello, world!
```

La prima riga è lo *shebang*: indica quale interprete deve leggere il file. Lo
stesso schema vale per Python:

```python
#!/usr/bin/env python3
print("Hello, world!")
```

Salva come `hello_world.py` ed esegui con `python3 hello_world.py`, oppure rendilo
eseguibile con `chmod +x` e lancialo come `./hello_world.py`.

## 3. Verifica

Tutte e tre le versioni devono scrivere la stessa riga su standard output e
restituire stato di uscita zero. Lo stato dell'ultimo comando è nella variabile di
shell `$?`:

```bash
./hello_world
echo $?
# 0
```

## Domande

- Quale file è testo e quale è binario, e come lo distingue `file`?
- Cosa cambia tra eseguire direttamente `./hello_world.sh` e `bash hello_world.sh`?
- Ripetendo l'esercizio su WILSON, quali moduli servono e quali no?

:::{dropdown} Soluzione / esito atteso
:color: success

Le tre versioni stampano `Hello, world!` e terminano con stato 0. `file` distingue
`hello_world.c` (testo C source) da `hello_world` (ELF executable). Eseguire
`./hello_world.sh` sfrutta lo shebang e il permesso di esecuzione; `bash
hello_world.sh` esegue l'interprete esplicitamente e non richiede il permesso.
Su WILSON la compilazione C richiede `module load GCC/13.2.0`; uno script non
richiede moduli.

:::
