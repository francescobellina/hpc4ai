#!/usr/bin/env bash
# Esercitazione 3 (Tiny stories, many threads) su WILSON: baseline seriale.
#
#   bash es03.sh setup     # copia i file del corso, compila, invia il job di baseline
#   bash es03.sh omp       # compila le versioni OpenMP e invia il job di scaling
#   bash es03.sh collect   # quando i job sono finiti: tutto in un log da scaricare
#
# Il job (un nodo Sandy Bridge esclusivo, come nell'esercizio 5) misura:
#   1. tok/s seriali dei tre modelli, 3 ripetizioni, decodifica greedy (-t 0), 256 token;
#   2. il profilo con gprof (15M e 110M) e, se disponibile, perf (110M);
#   3. la banda di memoria del nodo con triad.c, da 1 a 16 thread.
set -uo pipefail

DATA=/srv/data/wilson/project/hpc4ai/exercises/tiny_stories
ES=${ES:-$HOME/es03}
CONSTRAINT=sandy_bridge
PROMPT="Once upon a time"
STEPS=256
SACCT_FMT=JobID,JobName%20,Partition,NodeList%16,NTasks,AllocCPUS,ReqMem,Timelimit,Elapsed,State,ExitCode

section() { printf '\n========== %s ==========\n' "$*"; }
prompt() { printf '[%s@%s %s]$ ' "${USER:-$(id -un)}" "$(hostname -s)" "${PWD##*/}"; }
cmd() { printf '%s%s\n' "$(prompt)" "$*"; "$@" 2>&1; }

do_setup() {
    section "0. Login node"
    cmd date
    cmd hostname

    section "1. File del corso"
    cmd ls -lh "$DATA"
    cmd sha256sum "$DATA/run.c" "$DATA/tokenizer.bin" "$DATA/prompts.txt"
    mkdir -p "$ES" && cd "$ES" || return 1
    cp -n "$DATA/run.c" "$DATA/tokenizer.bin" "$DATA/prompts.txt" .
    [ -f triad.c ] || { echo "Manca triad.c in $ES: copialo accanto a es03.sh"; return 1; }
    cmd ls -l
    cmd wc -l run.c prompts.txt

    section "2. Compilazione (GCC/13.2.0)"
    module load GCC/13.2.0
    cmd gcc --version
    cmd gcc -O3 -o run run.c -lm
    cmd gcc -O3 -pg -o run_pg run.c -lm
    cmd gcc -O3 -fopenmp -o triad triad.c

    section "3. Prova breve sul login node (15M, 32 token)"
    cmd ./run "$DATA/stories15M.bin" -t 0 -n 32 -i "$PROMPT"

    section "4. Job di baseline"
    cat > baseline.sh <<JOB
#!/usr/bin/bash
#SBATCH --job-name=es03_baseline
#SBATCH --output=%x.%j.out
#SBATCH --error=%x.%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --partition=wilson
#SBATCH --constraint=$CONSTRAINT
#SBATCH --time=01:00:00

set -uo pipefail
cd "\$SLURM_SUBMIT_DIR"
module load GCC/13.2.0
echo "Job: \$SLURM_JOB_ID; nodo: \$SLURM_JOB_NODELIST"
lscpu
module list 2>&1
command -v perf && perf --version

one() { srun --ntasks=1 --cpus-per-task=1 --cpu-bind=cores "\$@"; }

echo "=== 1. Baseline seriale: $STEPS token, -t 0, prompt \"$PROMPT\""
for m in 15M 42M 110M; do
    for r in 1 2 3; do
        echo "--- stories\$m run \$r"
        one ./run "$DATA/stories\$m.bin" -t 0 -n $STEPS -i "$PROMPT" > "out_\${m}_r\$r.txt" 2> "tok_\${m}_r\$r.txt"
        cat "tok_\${m}_r\$r.txt"
    done
    cmp -s "out_\${m}_r1.txt" "out_\${m}_r2.txt" && cmp -s "out_\${m}_r1.txt" "out_\${m}_r3.txt" \\
        && echo "stories\$m: testo identico nelle 3 ripetizioni" || echo "stories\$m: TESTO DIVERSO fra le ripetizioni"
done

echo "=== 2. Profilo con gprof"
for m in 15M 110M; do
    mkdir -p "gprof_\$m" && ln -sf ../tokenizer.bin "gprof_\$m/" && ( cd "gprof_\$m" && one ../run_pg "$DATA/stories\$m.bin" -t 0 -n $STEPS -i "$PROMPT" > /dev/null 2>&1 \\
        && gprof -b -p ../run_pg gmon.out | head -25 )
done
if command -v perf >/dev/null; then
    echo "=== 2b. Profilo con perf (110M)"
    one perf record -o perf_110M.data ./run "$DATA/stories110M.bin" -t 0 -n $STEPS -i "$PROMPT" > /dev/null 2>&1
    perf report -i perf_110M.data --stdio --sort symbol 2>/dev/null | grep -v '^#' | grep -v '^\$' | head -20
fi

echo "=== 3. Banda di memoria (triad)"
for t in 1 2 4 8 16; do
    OMP_NUM_THREADS=\$t OMP_PLACES=cores OMP_PROC_BIND=spread \\
        srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores ./triad
done
JOB
    cmd cat baseline.sh
    if [ -f .jobid ]; then
        echo "Job già inviato: $(cat .jobid)"
    else
        id=$(sbatch --parsable baseline.sh) && echo "${id%%;*}" > .jobid && echo "Inviato job ${id%%;*}"
    fi
    cmd squeue -u "${USER:-$(id -un)}"
}

do_omp() {
    cd "$ES" || return 1
    local f id
    for f in run_omp.c run_omp_mm.c config.c omp_job.sh out_15M_r1.txt out_42M_r1.txt out_110M_r1.txt; do
        [ -f "$f" ] || { echo "Manca $f in $ES"; return 1; }
    done
    section "1. Differenze dal run.c del corso"
    cmd diff run.c run_omp.c
    cmd diff run.c run_omp_mm.c
    section "2. Compilazione (GCC/13.2.0)"
    module load GCC/13.2.0
    cmd gcc -O3 -fopenmp -o run_omp run_omp.c -lm
    cmd gcc -O3 -fopenmp -o run_omp_mm run_omp_mm.c -lm
    cmd gcc -O3 -fno-inline -pg -o run_noinline_pg run.c -lm
    cmd gcc -O2 -o config config.c
    section "3. Prova breve sul login node (15M, 32 token, 4 thread)"
    OMP_NUM_THREADS=4 cmd ./run_omp "$DATA/stories15M.bin" -t 0 -n 32 -i "$PROMPT"
    section "4. Job OpenMP"
    cmd cat omp_job.sh
    if [ -f .jobid_omp ]; then
        echo "Job già inviato: $(cat .jobid_omp)"
    else
        id=$(sbatch --parsable omp_job.sh) && echo "${id%%;*}" > .jobid_omp && echo "Inviato job ${id%%;*}"
    fi
    cmd squeue -u "${USER:-$(id -un)}"
}

do_collect() {
    cd "$ES" || return 1
    local id f
    id=$(cat .jobid 2>/dev/null)
    section "0. Stato"
    cmd date
    cmd squeue -u "${USER:-$(id -un)}"
    [ -n "$id" ] && cmd sacct -j "$id" --format="$SACCT_FMT"
    section "1. Sorgenti"
    cmd sha256sum run.c triad.c
    cmd cat triad.c
    cmd cat baseline.sh
    cmd cat run.c
    section "2. Output del job"
    for f in es03_baseline."$id".out es03_baseline."$id".err; do
        [ -f "$f" ] && cmd cat "$f"
    done
    section "3. Testi generati (prima ripetizione)"
    for f in out_*_r1.txt; do
        [ -f "$f" ] && cmd cat "$f"
    done
    section "4. Riepilogo tok/s"
    cmd grep -H "tok/s" tok_*.txt
    if [ -f .jobid_omp ]; then
        id=$(cat .jobid_omp)
        section "5. Job OpenMP (job $id)"
        cmd sacct -j "$id" --format="$SACCT_FMT"
        cmd sha256sum run_omp.c run_omp_mm.c config.c omp_job.sh
        cmd diff run.c run_omp.c
        for f in es03_omp."$id".out es03_omp."$id".err; do
            [ -f "$f" ] && cmd cat "$f"
        done
    fi
}

case "${1:-}" in
    setup|omp|collect) ;;
    *) echo "Uso: bash es03.sh setup | omp | collect" >&2; exit 1 ;;
esac
command -v sbatch >/dev/null || { echo "Errore: sbatch non trovato, non sei su WILSON?" >&2; exit 1; }
mkdir -p "$ES/logs"
LOG="$ES/logs/$1_$(date +%Y%m%d_%H%M%S).txt"
"do_$1" 2>&1 | tee "$LOG"
echo
echo "Log da scaricare: $LOG"
