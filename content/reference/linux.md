# Riferimento Linux

Il terminale è la stessa interfaccia sul client, via SSH su WILSON e dentro gli
script. `$` indica il prompt: digita il testo dopo `$`, non `$`. Guarda il prompt
per capire dove gira il comando. Il client locale usa l'account condiviso
`student`: spazio temporaneo, non privato.

## Comandi di base

| Comando | Scopo |
|---|---|
| `pwd` | directory corrente |
| `cd [DIR]` | cambia directory; `cd` o `cd ~` torna alla home |
| `ls [-l] [PATH]` | elenca il contenuto; `-l` forma lunga |
| `mkdir DIR...` | crea directory |
| `touch FILE...` | crea file vuoti |
| `rm FILE...` | rimuove file |
| `mv SORGENTE DEST` | sposta o rinomina |
| `df -h` | spazio su disco (unità leggibili) |
| `man COMANDO` | manuale; esci con `q` |

```bash
cd
pwd
echo $HOME
ls -l
df -h
```

`rm` elimina senza cestino: controlla con `pwd` dove sei e con `ls` cosa stai per
colpire.

## Redirezione e pipe

| Operatore | Effetto |
|---|---|
| `>` | scrive l'output in un file (sovrascrive) |
| `>>` | appende in fondo al file |
| `\|` | l'output di sinistra diventa input di destra |

```bash
echo hello > testfile
echo hello again >> testfile
wc -l *.txt | sort -n | head -n 5
```

## Variabili e ambiente

```bash
FILENAME=/etc/hostname    # variabile di shell (nessuno spazio attorno a =)
echo $FILENAME
export FILENAME           # diventa variabile d'ambiente
printenv | grep FILENAME
```

Le variabili di shell valgono nella shell corrente; `export` le passa ai programmi
avviati. `OMP_NUM_THREADS` più avanti è un esempio.

## Accesso remoto

```bash
ssh -l fbellina2 wilson.mib.infn.it     # login
exit                                    # o Ctrl+D
passwd                                  # cambia password (su WILSON)
scp file.tar.gz fbellina2@wilson.mib.infn.it:        # client -> WILSON
scp fbellina2@wilson.mib.infn.it:file.tar.gz .       # WILSON -> client
```

Al primo login la password va cambiata: almeno 8 caratteri e almeno 3 categorie
tra maiuscole, minuscole, cifre e simboli. Il terminale non mostra la password
mentre digiti.

## Editor

`nano`: Ctrl+G aiuto, Ctrl+S salva, Ctrl+O salva come, Ctrl+X esci.
`vim`: `i` inserisci, `Esc`, `:wq` salva ed esci, `:q!` esci senza salvare.
