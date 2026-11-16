#!/usr/bin/bash
#SBATCH --job-name=es03_omp
#SBATCH --output=%x.%j.out
#SBATCH --error=%x.%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --partition=wilson
#SBATCH --constraint=sandy_bridge
#SBATCH --time=01:00:00

# Esercizio 3: profilo senza inlining, configurazione dei modelli, validazione e
# scaling delle due versioni OpenMP (run_omp: matmul + teste; run_omp_mm: solo
# matmul). Ogni run confronta il testo generato con quello seriale del job di baseline
# (out_<modello>_r1.txt), quindi validazione e scaling sono la stessa misura.
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
module load GCC/13.2.0
DATA=/srv/data/wilson/project/hpc4ai/exercises/tiny_stories
PROMPT="Once upon a time"
STEPS=256
echo "Job: $SLURM_JOB_ID; nodo: $SLURM_JOB_NODELIST"
gcc --version | head -1

echo "=== 0. Configurazione dei modelli"
./config "$DATA"/stories15M.bin "$DATA"/stories42M.bin "$DATA"/stories110M.bin

echo "=== 1. Profilo seriale senza inlining (gprof, -O3 -fno-inline)"
for m in 15M 110M; do
    echo "--- stories$m"
    mkdir -p "gprof_noinline_$m" && ln -sf ../tokenizer.bin "gprof_noinline_$m/"
    ( cd "gprof_noinline_$m" && srun --ntasks=1 --cpus-per-task=1 --cpu-bind=cores ../run_noinline_pg \
        "$DATA/stories$m.bin" -t 0 -n $STEPS -i "$PROMPT" > out.txt 2> tok.txt
      cat tok.txt
      cmp -s out.txt "../out_${m}_r1.txt" && echo "testo identico al seriale" || echo "TESTO DIVERSO dal seriale"
      gprof -b -p ../run_noinline_pg gmon.out | head -14 )
done

# run1 <programma> <modello> <thread> <ripetizione> <binding>
run1() {
    OMP_NUM_THREADS=$3 OMP_PLACES=cores OMP_PROC_BIND=$5 \
        srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores ./"$1" "$DATA/stories$2.bin" \
        -t 0 -n $STEPS -i "$PROMPT" > o.txt 2> e.txt
    local tok same
    tok=$(sed -n 's/achieved tok\/s: //p' e.txt)
    cmp -s o.txt "out_$2_r1.txt" && same=identico || same=DIVERSO
    printf '%-11s %-5s %3s %2s %-6s %12s %s\n' "$1" "$2" "$3" "$4" "$5" "${tok:-ERRORE}" "$same" | tee -a scaling.txt
}

echo "=== 2. Scaling e validazione (3 ripetizioni, OMP_PLACES=cores)"
printf '%-11s %-5s %3s %2s %-6s %12s %s\n' programma model T r bind tok/s testo | tee scaling.txt
for m in 15M 42M 110M; do
    for v in run_omp run_omp_mm; do
        for t in 1 2 4 8 16; do
            for r in 1 2 3; do run1 "$v" "$m" "$t" "$r" spread; done
        done
    done
done

echo "=== 3. Disposizione dei thread: close (socket 0 prima) contro spread"
for t in 4 8; do
    run1 run_omp 110M "$t" 1 close
    OMP_NUM_THREADS=$t OMP_PLACES=cores OMP_PROC_BIND=close srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores ./triad
done

echo "=== Riepilogo"
grep -c identico scaling.txt | sed 's/^/run con testo identico: /'
grep -c DIVERSO scaling.txt | sed 's/^/run con testo diverso: /'
