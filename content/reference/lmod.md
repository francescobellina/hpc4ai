# Riferimento Lmod

WILSON espone compilatori, librerie e framework come **environment modules**: si
seleziona un pacchetto e l'ambiente di shell cambia, così versioni diverse non
entrano in conflitto. I nomi includono la versione perché lo stack compilatore +
librerie conta.

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module avail
module spider OpenMPI
module spider OpenMPI/4.1.6
module load GCC/13.2.0
module load OpenMPI/4.1.6
module list
module unload OpenMPI/4.1.6
module purge
```

| Comando | Scopo |
|---|---|
| `module use PCT` | aggiunge l'albero `Core` al search path |
| `module avail` | moduli caricabili direttamente |
| `module spider NOME` | cerca nella gerarchia completa |
| `module spider NOME/VERSIONE` | mostra i prerequisiti di una versione |
| `module load NOME/VERSIONE` | carica |
| `module list` | moduli attivi (incluse dipendenze) |
| `module unload NOME/VERSIONE` | scarica uno |
| `module purge` | scarica tutto (ambiente pulito) |

Se un modulo non compare in `module avail`, usa `module spider NOME`. Registra la
versione caricata insieme ai risultati.

::: {note}
Le versioni negli esempi (`GCC/13.2.0`, `OpenMPI/4.1.6`) sono esempi del corso:
confermale su WILSON con `module spider` prima di usarle.
:::
