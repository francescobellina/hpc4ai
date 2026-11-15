# Gestione delle risorse e scheduling

Su un cluster le risorse sono condivise: uno scheduler decide quando e dove eseguire ogni job. Questo capitolo raccoglie le note su disposizione, affinità e Slurm usate negli esercizi.

:::{seealso} Fonte principale
Capitolo 4 del corso, [*Managing resources and scheduling*](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/main/resource-management.html). Questa pagina riordina le note già scritte secondo la struttura di quel capitolo.
:::

(disposizione-e-slurm)=
## Disposizione, affinità e Slurm

La **disposizione** descrive quanti processi e thread vengono avviati e su quali nodi. L'**affinità** limita le CPU logiche sulle quali un processo o thread può essere eseguito; non garantisce che vi resti in ogni istante. L'**oversubscription** si verifica quando si richiedono più flussi software di quante CPU logiche siano assegnate. Può essere intenzionale, ma spesso causa contesa e non è una scorciatoia per ottenere più capacità.

Slurm è uno scheduler: gestisce le richieste di risorse e decide quando e dove eseguire i job secondo la configurazione del cluster. Un programma dovrebbe allineare il numero di processi e thread alle risorse richieste. Opzioni, partizioni e politiche sono specifiche del sistema; per WILSON non vanno dedotte da esempi generici.

(t-slurm-esecuzione)=
## Esecuzione su cluster (Slurm)

I test sul login node servono solo a controlli molto brevi: le esecuzioni reali
passano da **Slurm** con uno script di batch che carica gli stessi moduli usati per
compilare e lancia il programma con `srun`.

- **Run OpenMP** — un task con più CPU: `--cpus-per-task=T` e
  `export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`.
- **Run MPI** — più task con una CPU ciascuno: `--ntasks=P --cpus-per-task=1`,
  `OMP_NUM_THREADS=1`.
- **Run ibrido** — più task con più CPU ciascuno, su più nodi:
  `--nodes=2 --ntasks=P --cpus-per-task=T`.

Comandi, moduli e procedure verificate su WILSON sono nella [guida pratica al cluster](../workflow/lab-client-wilson.md) e nel riferimento [Lmod](../reference/lmod.md).
