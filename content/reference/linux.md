# Riferimento Linux

La shell permette di esplorare file, eseguire programmi e configurare l'ambiente. Controlla la directory corrente prima di operazioni che modificano o rimuovono file.

## File e directory

| Comando | Funzione |
|---|---|
| `pwd` | Mostra la directory corrente |
| `cd <DIR>` | Cambia directory; `cd` o `cd ~` torna alla home |
| `ls -l <PERCORSO>` | Elenca file e dettagli |
| `mkdir <DIR>` | Crea una directory |
| `mv <SORGENTE> <DESTINAZIONE>` | Sposta o rinomina |
| `rm <FILE>` | Rimuove file senza cestino: verifica prima percorso e nome |
| `df -h` | Mostra spazio disco in unità leggibili |
| `man <COMANDO>` | Apre il manuale del comando; `q` esce |

## Input, output e variabili

`>` scrive l'output in un file sovrascrivendolo; `>>` aggiunge in coda; `|` passa l'output di un comando al successivo.

```bash
echo hello > output.txt
echo again >> output.txt
wc -l *.txt | sort -n | head -n 5
```

Le variabili di shell valgono nella shell corrente. `export` le rende disponibili ai programmi avviati da quella shell.

```bash
NAME=value
export NAME
printenv NAME
```

Per accesso remoto e trasferimenti tra client e WILSON, consulta la [guida pratica al cluster](../workflow/lab-client-wilson.md).
