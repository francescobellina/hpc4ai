# codes/exec6 — Image denoising in parallel

Esercitazione 6 della relazione: denoising di un'immagine in scala di grigi con
l'iterazione di Jacobi, versione sequenziale del corso e versione MPI a strisce
(in corso).

## File

| File | Scopo |
|---|---|
| `denoise_serial.c`, `pgm_io.h`, `prepare_image.py` | file del corso, copiati senza modifiche da `/srv/data/wilson/project/hpc4ai/exercises/image-denoising/` (SHA256 `e1b6b131…`, `35ec1dd7…`, `234e3bce…`) |
| `README-corso.md` | il `README.md` del corso, con i comandi di compilazione ed esecuzione |
| `figure_2x2.py` | calcolo esatto (frazioni) del caso 2 × 2 e figure `es06-2x2-*.png`: la previsione teorica |
| `denoise_mpi.c` | versione MPI a strisce; `jacobi_step` copiata identica dal corso |
| `compare_bin.c` | differenza massima fra due `.bin` (soglia 1e-12) |
| `test_mpi.sh` | validazione per piccoli passi: `uno`, `nodo`, `nodi` |
| `analyze_es06.py` | riferimento NumPy del passo di Jacobi (stesso ordine delle somme del C), confronto con le uscite del programma, MSE, PSNR, SSIM e figure `es06-ricostruzioni.png`, `es06-ssim-mappe.png`, `es06-profilo.png`, `es06-qualita-lambda.png` |

## Uso

Su WILSON (comandi della consegna; `srun` richiede la partizione):

```bash
module load GCC/13.2.0
gcc -O2 -std=c11 -Wall -Wextra denoise_serial.c -lm -o denoise_serial
srun -p wilson --constraint=sandy_bridge --ntasks=1 --cpus-per-task=1 --cpu-bind=cores \
    ./denoise_serial images/medium/noisy.pgm serial.pgm 1 200 1e-6 serial.bin
```

Versione MPI (su WILSON, nella stessa cartella di `denoise_serial`):

```bash
module load GCC/13.2.0 OpenMPI/4.1.6
mpicc -O2 -std=c11 -Wall -Wextra denoise_mpi.c -lm -o denoise_mpi
gcc -O2 compare_bin.c -lm -o compare_bin
bash test_mpi.sh uno; bash test_mpi.sh nodo; bash test_mpi.sh nodi
```

Sul Mac, con le uscite scaricate in `results/es06/raw/` (non versionata):

```bash
.venv/bin/python codes/exec6/figure_2x2.py
.venv/bin/python codes/exec6/analyze_es06.py
```
