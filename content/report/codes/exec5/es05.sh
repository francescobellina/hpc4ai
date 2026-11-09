#!/usr/bin/env bash
# Esercitazione 5 (benchmarking e scaling, HPL e HPCG) su WILSON.
#
#   bash es05.sh setup     # ricognizione, copia dei file del corso, baseline
#   bash es05.sh node      # confronto delle ripartizioni MPI x OpenMP su un nodo
#   bash es05.sh collect   # raccoglie input, output e sacct di tutti i run
#
# Va eseguito sul login node. Lavora in ~/es05/: una cartella per configurazione
# (input + script batch + output), come chiede la consegna. Ogni comando viene
# scritto con il suo output in ~/es05/logs/<sottocomando>_<data>.txt, il file da
# scaricare.
set -uo pipefail

REF=${REF:-/srv/data/wilson/project/hpc4ai/exercises/benchmark}
ES=${ES:-$HOME/es05}
SACCT_FMT=JobID,JobName%24,Partition,NodeList%24,NNodes,NTasks,AllocCPUS,ReqMem,Timelimit,Elapsed,State,ExitCode
# Tutte le serie usano un solo tipo di nodo: la partizione wilson mescola tre
# generazioni di CPU. Sandy Bridge E5-2650: 2.0 GHz x 8 flop/ciclo (AVX senza FMA).
CONSTRAINT=sandy_bridge
PEAK_CORE=16

section() { printf '\n========== %s ==========\n' "$*"; }
# cmd stampa il comando dopo un prompt reale (utente, macchina, cartella) e lo esegue.
prompt() { printf '[%s@%s %s]$ ' "${USER:-$(id -un)}" "$(hostname -s)" "${PWD##*/}"; }
cmd() { printf '%s%s\n' "$(prompt)" "$*"; "$@" 2>&1; }
is_text() {
    if command -v file >/dev/null; then
        file -b --mime-type "$1" | grep -q '^text/'
    else
        case $1 in *.dat|*.sh|*.txt|*README*) true ;; *) false ;; esac
    fi
}

# submit <cartella>: invia lo script batch della cartella e ne salva il job ID.
submit() {
    local dir=$1 script id
    script=$(cd "$dir" && ls ./*.sh 2>/dev/null | head -1)
    [ -n "$script" ] || { echo "Nessuno script batch in $dir"; return 1; }
    if [ -f "$dir/.jobid" ]; then
        echo "$dir: già inviato (job $(cat "$dir/.jobid")), non lo reinvio"
        return 0
    fi
    cd "$dir" || return 1
    printf '%s%s\n' "$(prompt)" "sbatch --parsable $script"
    id=$(sbatch --parsable "$script") && echo "${id%%;*}" > .jobid && echo "job ${id%%;*}"
    cd - >/dev/null || return 1
}

# patch_script <sorgente> <job-name> <nodi> <task/nodo> <cpu/task> <tempo> [argomenti extra]
# Copia uno script batch del corso cambiando solo layout, nome, tempo e vincolo sul nodo.
patch_script() {
    awk -v name="$2" -v nodes="$3" -v nt="$4" -v nc="$5" -v t="$6" -v extra="${7:-}" -v cons="$CONSTRAINT" '
        /^#SBATCH --job-name=/        { print "#SBATCH --job-name=" name; next }
        /^#SBATCH --nodes=/           { print "#SBATCH --nodes=" nodes; next }
        /^#SBATCH --ntasks-per-node=/ { print "#SBATCH --ntasks-per-node=" nt; next }
        /^#SBATCH --cpus-per-task=/   { print "#SBATCH --cpus-per-task=" nc; next }
        /^#SBATCH --time=/            { print "#SBATCH --time=" t; next }
        /^#SBATCH --partition=/       { print; print "#SBATCH --constraint=" cons; next }
        /^srun .*xhp(l|cg)$/ && extra != "" { print $0 " " extra; next }
        { print }' "$1"
}

# hpl_case <cartella> <N> <P> <Q> <nodi> <task/nodo> <cpu/task> <tempo>
hpl_case() {
    local name=$1 dir="$ES/hpl/$1" script
    script="HPL_wilson_n$6c$7_script.sh"
    [ -f "$dir/.jobid" ] && { echo "hpl/$name: già inviato (job $(cat "$dir/.jobid"))"; return 0; }
    mkdir -p "$dir"
    awk -v N="$2" -v P="$3" -v Q="$4" '
        NR == 6  { sub(/^[0-9]+/, N) }
        NR == 11 { sub(/^[0-9]+/, P) }
        NR == 12 { sub(/^[0-9]+/, Q) }
        { print }' "$ES/reference/HPL.dat" > "$dir/HPL.dat"
    patch_script "$ES/reference/HPL_wilson_n4c4_script.sh" "hpl_$name" "$5" "$6" "$7" "$8" > "$dir/$script"
    chmod +x "$dir/$script"
    echo
    echo "---- hpl/$name"
    (cd "$dir" && cmd diff "$ES/reference/HPL.dat" HPL.dat; cmd diff "$ES/reference/HPL_wilson_n4c4_script.sh" "$script")
    submit "$dir"
}

# hpcg_case <cartella> <nodi> <task/nodo> <cpu/task> "<nx ny nz>" <npx> <npy> <npz> <tempo>
hpcg_case() {
    local name=$1 dir="$ES/hpcg/$1" script
    script="HPCG_wilson_n$3c$4_script.sh"
    [ -f "$dir/.jobid" ] && { echo "hpcg/$name: già inviato (job $(cat "$dir/.jobid"))"; return 0; }
    mkdir -p "$dir"
    awk -v g="$5" 'NR == 3 { $0 = g } { print }' "$ES/reference/hpcg.dat" > "$dir/hpcg.dat"
    patch_script "$ES/reference/HPCG_wilson_n16c1_script.sh" "hpcg_$name" "$2" "$3" "$4" "$9" \
        "--npx=$6 --npy=$7 --npz=$8" > "$dir/$script"
    chmod +x "$dir/$script"
    echo
    echo "---- hpcg/$name"
    (cd "$dir" && cmd diff "$ES/reference/hpcg.dat" hpcg.dat; cmd diff "$ES/reference/HPCG_wilson_n16c1_script.sh" "$script")
    submit "$dir"
}

do_setup() {
    section "0. Login node"
    cmd date
    cmd hostname
    echo "MODULEPATH=${MODULEPATH:-}"

    section "1. File di riferimento del corso"
    cmd ls -l "$REF"
    cmd sha256sum "$REF"/*
    local f
    for f in "$REF"/*; do
        [ -f "$f" ] && is_text "$f" && cmd cat "$f"
    done

    section "2. Partizioni e nodi"
    cmd sinfo -p wilson,wilson2,lab4 -o "%P %a %l %D %c %m %f %N"
    cmd sinfo -N -p lab4 -o "%N %P %c %m %f %T"

    section "3. Moduli"
    if type module >/dev/null 2>&1; then
        cmd module spider HPL
        cmd module spider HPCG
    else
        echo "(module non inizializzato in questa shell)"
    fi

    section "4. Cartelle di lavoro in $ES"
    mkdir -p "$ES"/{reference,hpl,hpcg,nodeinfo,logs}
    cp -n "$REF"/* "$ES/reference/" 2>/dev/null
    mkdir -p "$ES/hpl/00_baseline" "$ES/hpcg/00_baseline"
    cp -n "$REF"/HPL.dat "$REF"/HPL*.sh "$ES/hpl/00_baseline/"
    cp -n "$REF"/hpcg.dat "$REF"/HPCG*.sh "$ES/hpcg/00_baseline/"
    cmd ls -l "$ES/reference" "$ES/hpl/00_baseline" "$ES/hpcg/00_baseline"

    section "5. CPU dei due tipi di nodo (job brevi, raccolti da collect)"
    local p
    for p in wilson wilson2; do
        if ls "$ES"/nodeinfo/lscpu_"$p".*.out >/dev/null 2>&1; then
            echo "lscpu su $p già raccolto"
            continue
        fi
        cd "$ES/nodeinfo" || return 1
        printf '%s%s\n' "$(prompt)" "sbatch -p $p -N 1 -n 1 --mem=1G -t 00:02:00 -o lscpu_$p.%j.out --wrap 'hostname; lscpu'"
        sbatch -p "$p" -N 1 -n 1 --mem=1G -t 00:02:00 -o "lscpu_$p.%j.out" --wrap 'hostname; lscpu' 2>&1
        cd - >/dev/null || return 1
    done

    section "6. Baseline con i file del corso non modificati"
    submit "$ES/hpl/00_baseline"
    submit "$ES/hpcg/00_baseline"
    cmd squeue -u "${USER:-$(id -un)}"
}

# Confronto su un nodo Sandy Bridge (16 core): come ripartire i core tra processi
# MPI e thread OpenMP, cambiando un solo aspetto alla volta.
do_node() {
    section "0. Nodi $CONSTRAINT"
    cmd date
    cmd sinfo -N -p wilson -o "%N %c %m %f %T"

    section "1. HPL: dimensione del problema (layout della baseline, 4 task x 4 thread, P x Q = 2 x 2)"
    hpl_case 01_N24576_4x4_P2Q2   24576 2 2  1 4 4 00:30:00

    section "2. HPL: ripartizione dei 16 core a N = 41280 fisso (task MPI x thread, griglia P x Q)"
    hpl_case 10_N41280_16x1_P4Q4  41280 4 4  1 16 1 00:30:00
    hpl_case 11_N41280_16x1_P2Q8  41280 2 8  1 16 1 00:30:00
    hpl_case 12_N41280_16x1_P1Q16 41280 1 16 1 16 1 00:30:00
    hpl_case 13_N41280_8x2_P2Q4   41280 2 4  1 8 2  00:30:00
    hpl_case 14_N41280_4x4_P2Q2   41280 2 2  1 4 4  00:30:00
    hpl_case 15_N41280_2x8_P1Q2   41280 1 2  1 2 8  00:30:00
    hpl_case 16_N41280_1x16_P1Q1  41280 1 1  1 1 16 00:30:00

    section "3. HPCG: ripartizione dei 16 core a griglia globale fissa 416 x 208 x 208, 60 s"
    hpcg_case 10_16x1 1 16 1  "104 104 104" 4 2 2 01:00:00
    hpcg_case 11_8x2  1 8 2   "208 104 104" 2 2 2 01:00:00
    hpcg_case 12_4x4  1 4 4   "208 104 208" 2 2 1 01:00:00
    hpcg_case 13_2x8  1 2 8   "208 208 208" 2 1 1 01:00:00
    hpcg_case 14_1x16 1 1 16  "416 208 208" 1 1 1 01:00:00

    echo
    cmd squeue -u "${USER:-$(id -un)}"
}

# Tabella finale: un run per riga, con la frazione del picco dei core usati.
summary() {
    section "RIEPILOGO"
    local dir out f node nt th v N NB P Q T G chk np gx gy gz rate
    printf '%-26s %-8s %5s %4s %7s %6s %9s %11s %7s %s\n' HPL nodo task thr N PxQ "Time(s)" "GFLOP/s" "%picco" residuo
    for dir in "$ES"/hpl/*/; do
        out=$(ls "$dir"*.out 2>/dev/null | head -1)
        [ -n "$out" ] || continue
        node=$(sed -n 's/^Job: .*nodes: //p' "$out")
        nt=$(sed -n 's/.*MPI tasks: \([0-9]*\);.*/\1/p' "$out")
        th=$(sed -n 's/.*OpenMP threads per task: \([0-9]*\).*/\1/p' "$out")
        read -r v N NB P Q T G <<<"$(grep -E '^WR' "$out" | head -1)"
        chk=$(grep -oE 'PASSED|FAILED' "$out" | head -1)
        printf '%-26s %-8s %5s %4s %7s %6s %9s %11s %7s %s\n' "$(basename "$dir")" "$node" "$nt" "$th" "${N:-}" "${P:-}x${Q:-}" "${T:-}" "${G:-}" \
            "$(awk -v g="${G:-0}" -v c=$(( ${nt:-0} * ${th:-0} )) -v pc=$PEAK_CORE 'BEGIN { if (c > 0) printf "%.1f", 100 * g / (c * pc) }')" "${chk:-n/d}"
    done
    echo
    printf '%-26s %-8s %5s %4s %15s %11s %7s %s\n' HPCG nodo proc thr "griglia glob." "GFLOP/s" "%picco" esito
    for dir in "$ES"/hpcg/*/; do
        f=$(ls -t "$dir"HPCG-Benchmark*.txt 2>/dev/null | head -1)
        [ -n "$f" ] || continue
        out=$(ls "$dir"*.out 2>/dev/null | head -1)
        node=$(sed -n 's/^Job: .*nodes: //p' "$out" 2>/dev/null)
        np=$(sed -n 's/^Machine Summary::Distributed Processes=//p' "$f")
        th=$(sed -n 's/^Machine Summary::Threads per processes=//p' "$f")
        gx=$(sed -n 's/^Global Problem Dimensions::Global nx=//p' "$f")
        gy=$(sed -n 's/^Global Problem Dimensions::Global ny=//p' "$f")
        gz=$(sed -n 's/^Global Problem Dimensions::Global nz=//p' "$f")
        rate=$(sed -n 's/^Final Summary::HPCG result is VALID with a GFLOP\/s rating of=//p' "$f")
        chk=$(grep -q 'HPCG result is VALID' "$f" && echo VALID || echo NON-VALID)
        # La frazione del picco usa i core allocati (task x cpu/task), non i thread usati.
        nt=$(sed -n 's/.*MPI tasks: \([0-9]*\);.*/\1/p' "$out" 2>/dev/null)
        th=${th:-?}
        printf '%-26s %-8s %5s %4s %15s %11s %7s %s\n' "$(basename "$dir")" "$node" "$np" "$th" "${gx}x${gy}x${gz}" "${rate:-}" \
            "$(awk -v g="${rate:-0}" -v c="$(sed -n 's/.*CPUs per task: \([0-9]*\);.*/\1/p' "$out" 2>/dev/null)" -v n="${nt:-0}" -v pc=$PEAK_CORE 'BEGIN { if (n * c > 0) printf "%.2f", 100 * g / (n * c * pc) }')" "$chk"
    done
}

do_collect() {
    section "0. Stato dei job"
    cmd date
    cmd squeue -u "${USER:-$(id -un)}"

    section "1. CPU dei nodi"
    local f dir id
    for f in "$ES"/nodeinfo/*.out; do
        [ -f "$f" ] && cmd cat "$f"
    done

    for dir in "$ES"/hpl/*/ "$ES"/hpcg/*/; do
        [ -f "$dir/.jobid" ] || continue
        id=$(cat "$dir/.jobid")
        section "${dir#"$ES"/} (job $id)"
        cd "$dir" || continue
        cmd ls -l
        for f in *.dat *.sh; do
            [ -f "$f" ] && cmd cat "$f"
        done
        cmd sacct -j "$id" --format="$SACCT_FMT"
        # .err contiene le maschere di --cpu-bind=verbose; hpcg<data>.txt è il log di HPCG.
        for f in *.out *.err hpcg[0-9]*.txt HPCG-Benchmark*.txt; do
            [ -f "$f" ] && cmd cat "$f"
        done
        for f in *.out; do
            [ -f "$f" ] || continue
            cmd grep -E "WR[0-9A-Z]+ |PASSED|FAILED" "$f"
        done
        for f in HPCG-Benchmark*.txt; do
            [ -f "$f" ] && cmd grep "Final Summary" "$f"
        done
        cd - >/dev/null || return 1
    done
    summary
}

case "${1:-}" in
    setup|node|collect) ;;
    *) echo "Uso: bash es05.sh setup | node | collect" >&2; exit 1 ;;
esac
command -v sbatch >/dev/null || { echo "Errore: sbatch non trovato, non sei su WILSON?" >&2; exit 1; }
mkdir -p "$ES/logs"
LOG="$ES/logs/$1_$(date +%Y%m%d_%H%M%S).txt"
cd "$HOME" || exit 1
"do_$1" 2>&1 | tee "$LOG"
echo
echo "Log da scaricare: $LOG"
