# Ottimizzazione di `compute_statistics`: confronto tra accesso originale e per righe

## Obiettivo

Confrontare il programma originale (`preprocess.c`) con la variante
ottimizzata (`preprocess_rows.c`), nella quale i cicli di
`compute_statistics` sono stati riordinati per visitare i dati per
righe.

La matrice dei dati è memorizzata in ordine row-major. Nella versione
originale il ciclo interno attraversa le osservazioni mantenendo fissa
la feature; nella variante per righe il ciclo interno attraversa le
feature di una stessa osservazione.

## Ambiente e compilazione

I test sono stati eseguiti sul cluster WILSON, nella directory:

``` text
/srv/data/wilson/students/home/fbellina2/profiling-data-preparation
```

Entrambe le versioni sono state compilate con:

``` bash
gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess.c -lm -o preprocess
gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess_rows.c -lm -o preprocess_rows
```

I comandi di esecuzione sono stati lanciati con `srun --cpu-bind=cores`.

## Verifica della correttezza

Prima del benchmark, entrambe le versioni sono state eseguite con il
controllo `check`, usando `1024` osservazioni, `32` feature e `1`
ripetizione.

  Versione                  Checksum Validazione
  ----------- ---------------------- -------------
  Originale     `8173.5024171285777` PASS
  Per righe     `8173.5024171285777` PASS

Output di validazione per entrambe:

``` text
Validation: PASS (max |mean| 2.418e-14; max variance error 1.217e-11)
```

È stato ripetuto il controllo anche sulla dimensione usata per il
benchmark: `65536` osservazioni, `256` feature e `1` ripetizione.

  Versione                  Checksum Validazione
  ----------- ---------------------- -------------
  Originale     `452271.54382956069` PASS
  Per righe     `452271.54382956069` PASS

Output di validazione per entrambe:

``` text
Validation: PASS (max |mean| 1.147e-14; max variance error 1.211e-11)
```

I risultati riportati mostrano che, per questi test, entrambe le
versioni superano il controllo e producono lo stesso checksum.

## Benchmark dei tempi

Configurazione:

-   Osservazioni: `65536`
-   Feature: `256`
-   Ripetizioni: `5`

Ogni versione è stata eseguita tre volte. I tempi misurati sono:

    Esecuzione   Originale (s)   Per righe (s)
  ------------ --------------- ---------------
             1            1.92            0.49
             2            1.91            0.49
             3            1.91            0.49

I checksum sono risultati identici in tutte le esecuzioni:

``` text
2261357.7191473623
```

La versione originale ha impiegato circa `1.91–1.92 s`, mentre quella
per righe circa `0.49 s`.

Usando i valori medi riportati (1.9133 s per l'originale e 0.49 s per la
variante per righe), lo speedup è circa:

\[ `\text{speedup}`{=tex} = `\frac{1.9133}{0.49}`{=tex}
`\approx 3.90`{=tex} \]

La riduzione del tempo trascorso è circa il `74.4%`. Il rapporto è
calcolato sui tempi arrotondati stampati dal comando `/usr/bin/time`,
quindi va considerato approssimativo.

> Nota: in una precedente esecuzione singola, i tempi erano `1.92 s` e
> `0.51 s`. Il confronto ripetuto sopra è basato sulle tre esecuzioni
> successive.

## Contatori hardware con `perf stat`

È stato eseguito:

``` bash
srun --cpu-bind=cores perf stat -e cycles,instructions,cache-references,cache-misses ./preprocess 65536 256 5
srun --cpu-bind=cores perf stat -e cycles,instructions,cache-references,cache-misses ./preprocess_rows 65536 256 5
```

Risultati originali:

  Contatore                                  Valore
  --------------------------------- ---------------
  cycles                              5,496,844,213
  instructions                        2,818,084,016
  cache-references                      211,238,959
  cache-misses                          189,620,745
  cache-misses / cache-references            89.77%
  Tempo trascorso                     1.923004894 s
  Tempo user                          1.840539000 s
  Tempo sys                           0.068656000 s
  Instructions per cycle (IPC)                 0.51

Risultati della variante per righe:

  Contatore                                  Valore
  --------------------------------- ---------------
  cycles                              1,294,445,012
  instructions                        2,739,432,998
  cache-references                       68,703,756
  cache-misses                           38,600,350
  cache-misses / cache-references            56.18%
  Tempo trascorso                     0.507690219 s
  Tempo user                          0.431594000 s
  Tempo sys                           0.072672000 s
  Instructions per cycle (IPC)                 2.12

### Confronto dei contatori

Rispetto alla versione originale, la variante per righe mostra:

  Misura                                            Variazione
  --------------------------------------------- --------------
  Cicli CPU (`cycles`)                            circa −76.5%
  Istruzioni (`instructions`)                      circa −2.8%
  Riferimenti alla cache (`cache-references`)     circa −67.5%
  Cache miss (`cache-misses`)                     circa −79.6%
  Tempo trascorso (`time elapsed`)                circa −73.6%

Il rapporto tra i tempi `perf stat` è:

\[ `\text{speedup}`{=tex} = `\frac{1.923004894}{0.507690219}`{=tex}
`\approx 3.79`{=tex} \]

Il dato `instructions per cycle` passa da `0.51` a `2.12`.

## Interpretazione

La variante per righe migliora la località spaziale degli accessi alla
memoria. Con la disposizione row-major, gli elementi di una stessa
osservazione sono memorizzati consecutivamente.

Nella versione originale, il ciclo interno attraversa le osservazioni a
feature fissata: tra due accessi consecutivi vengono saltati `256`
elementi `double`, cioè `2048` byte. Nella variante per righe, il ciclo
interno legge elementi adiacenti della stessa osservazione.

I contatori misurati sono coerenti con questa spiegazione: nella
variante per righe diminuiscono sensibilmente i riferimenti alla cache e
i cache miss, insieme ai cicli CPU. Il rapporto
`cache-misses / cache-references` scende dal `89.77%` al `56.18%`.

Questi dati supportano l'interpretazione basata sulla migliore località
degli accessi. I contatori riportati, tuttavia, non identificano da soli
ogni livello della gerarchia di cache né dimostrano quale specifico
livello abbia causato il miglioramento.

## Conclusione

Per la configurazione testata (`65536` osservazioni, `256` feature, `5`
ripetizioni), la variante che attraversa i dati per righe:

-   supera gli stessi controlli di validazione della versione originale;
-   produce lo stesso checksum;
-   riduce il tempo misurato da circa `1.91–1.92 s` a circa `0.49 s`
    nelle tre ripetizioni;
-   ottiene uno speedup di circa `3.8–3.9×`, a seconda dei tempi usati
    nel calcolo;
-   presenta meno cicli CPU, riferimenti alla cache e cache miss nei
    contatori raccolti.

Il risultato è coerente con il vantaggio atteso dal riordino dei cicli:
accedere in modo contiguo ai dati in memoria row-major riduce gli
accessi poco localizzati e rende l'elaborazione più efficiente.

## Nota operativa su SLURM

Durante la sessione, un'allocazione SLURM precedente è stata revocata e
i successivi `srun` hanno restituito `Invalid job id`. È stata richiesta
una nuova allocazione con:

``` bash
salloc -plab4 --nodes=1 --ntasks=1 --cpus-per-task=1 \
    --hint=nomultithread --mem=1G --time=00:15:00
```

Dopo il messaggio `Nodes wnode25 are ready for job`, i comandi `srun`
sono stati eseguiti correttamente. Questo problema di allocazione è
operativo e non fa parte dei risultati prestazionali.
