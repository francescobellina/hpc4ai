#!/usr/bin/env bash
# Esercitazione 4 (profiling della data preparation): tutte le misure della
# relazione in un'unica esecuzione su WILSON.
#
#   bash es04_all.sh
#
# Va eseguito sul login node, nella cartella di preprocess.c e preprocess_rows.c.
# Compila con il gcc di sistema e i flag del corso, invia le misure come job
# Slurm su un core dedicato, ne attende la fine e lascia un unico file di testo:
#
#   es04_run_<data>/es04_<JOBID>.txt
#
# Contenuto: build con diff dei sorgenti, nodo e CPU, validazione, checksum con
# la tolleranza della consegna, timing (time di bash e GNU time sulle stesse run,
# versioni alternate), perf record/report a 5 e 30 ripetizioni, perf stat,
# riepilogo numerico. I file perf-*.data restano nella stessa cartella.
#
#SBATCH --job-name=es04_all
#SBATCH --partition=lab4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=1G
#SBATCH --time=00:15:00
set -uo pipefail

N=65536 D=256 REPS=5 PROF_REPS=30 TIMING_RUNS=3 STAT_RUNS=3
CFLAGS="-O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra"
SHARED=/srv/data/wilson/project/hpc4ai/exercises/profiling-data-preparation
TIME_BIN=${TIME_BIN:-/usr/bin/time}
GFMT='GNU time: %e s elapsed, %U s user, %S s sys, %M KB max RSS'
SRUN="srun --cpu-bind=cores"

SUMMARY=()
section() { printf '\n========== %s ==========\n' "$*"; }
note()    { SUMMARY+=("$*"); }
# cmd stampa il comando dopo un prompt reale (utente, macchina, cartella) e lo
# esegue; cap fa lo stesso e conserva l'output in $OUT per il riepilogo.
prompt() { printf '[%s@%s %s]$ ' "${USER:-$(id -un)}" "$(hostname -s)" "${PWD##*/}"; }
cmd() { printf '%s%s\n' "$(prompt)" "$*"; "$@" 2>&1; }
cap() { printf '%s%s\n' "$(prompt)" "$*"; OUT=$("$@" 2>&1); local rc=$?; printf '%s\n' "$OUT"; return $rc; }

checksum() { sed -n 's/^Checksum: //p' <<<"$OUT"; }
pass()     { grep -q 'Validation: PASS' <<<"$OUT" && echo PASS || echo FAIL; }
same()     { [ -n "$1" ] && [ "$1" = "$2" ] && echo identici || echo DIVERSI; }
median()   { printf '%s\n' "$@" | sort -n | awk '{ a[NR] = $1 } END { if (NR % 2) print a[(NR + 1) / 2]; else if (NR) print (a[NR / 2] + a[NR / 2 + 1]) / 2 }'; }
ratio()    { awk -v a="${1:-0}" -v b="${2:-0}" 'BEGIN { if (b > 0) printf "%.2f", a / b; else printf "n/d" }'; }
change()   { awk -v a="${1:-0}" -v b="${2:-0}" 'BEGIN { if (a > 0) printf "%+.1f%%", (b / a - 1) * 100; else printf "n/d" }'; }
stat_val() { awk -v ev="$1" '$2 ~ "^" ev { gsub(",", "", $1); print $1; exit }' <<<"$OUT"; }
# Criterio della consegna: |a - b| <= 1e-8 + 1e-10 |a|.
within_tol() {
    [ -n "$1" ] && [ -n "$2" ] || { printf 'n/d'; return; }
    awk -v a="$1" -v b="$2" 'BEGIN { d = a - b; if (d < 0) d = -d; t = 1e-8 + 1e-10 * (a < 0 ? -a : a)
        printf "|a-b| = %.3g <= %.3g: %s", d, t, (d <= t ? "OK" : "FUORI TOLLERANZA") }'
}
# amdahl <rip.> <Self% before> <Self% after> <Event count before> <Event count after>
amdahl() {
    awk -v r="$1" -v sb="${2:-0}" -v sa="${3:-0}" -v eb="${4:-0}" -v ea="${5:-0}" 'BEGIN {
        f = sb / 100
        if (f >= 1 || sa <= 0 || ea <= 0) { printf "Amdahl (%s rip.): dati perf incompleti", r; exit }
        p = (sb * eb) / (sa * ea)
        printf "Amdahl (%s rip.): f = %.4f, S_max = 1/(1-f) = %.2fx; speedup user-space (Event count) = %.2fx; accelerazione hotspot p = %.2fx; Amdahl con p = %.2fx",
            r, f, 1 / (1 - f), eb / ea, p, 1 / ((1 - f) + f / p)
    }'
}

submit() {
    cd -- "$(dirname -- "$0")" || exit 1
    local self f
    self=$(basename -- "$0")
    for f in preprocess.c preprocess_rows.c; do
        [ -f "$f" ] || { echo "Errore: manca $f in $PWD" >&2; exit 1; }
    done
    command -v sbatch >/dev/null || { echo "Errore: sbatch non trovato, non sei su WILSON?" >&2; exit 1; }

    RUN=es04_run_$(date +%Y%m%d_%H%M%S)
    mkdir -p "$RUN"
    {
        section "0. Build sul login node"
        cmd date
        cmd hostname
        cmd pwd
        cmd gcc --version
        cmd sha256sum preprocess.c preprocess_rows.c
        if [ -f "$SHARED/preprocess.c" ]; then
            if cmd cmp preprocess.c "$SHARED/preprocess.c"; then
                echo "preprocess.c identico alla copia condivisa del corso"
            else
                echo "ATTENZIONE: preprocess.c differisce dalla copia condivisa del corso"
            fi
        fi
        # Il diff documenta il cambio dei cicli e, applicato a preprocess.c,
        # ricostruisce esattamente il sorgente misurato (verificabile con sha256sum).
        cmd diff -u preprocess.c preprocess_rows.c
        if type module >/dev/null 2>&1; then
            cmd module list
        else
            echo "(module non inizializzato in questa shell: nessun modulo caricato, gcc di sistema)"
        fi
        cmd gcc $CFLAGS preprocess.c -lm -o preprocess &&
            cmd gcc $CFLAGS preprocess_rows.c -lm -o preprocess_rows
    } | tee "$RUN/build.txt"
    [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "Errore: compilazione fallita, vedi sopra" >&2; exit 1; }

    echo
    echo "Invio il job su lab4 e attendo la fine (circa 1-2 minuti più l'attesa in coda)."
    echo "Se il terminale si chiude il job continua: l'output sarà comunque in $RUN/."
    local jobid
    jobid=$(sbatch --parsable --wait --output="$RUN/es04_%j.txt" "$self" measure "$RUN")
    jobid=${jobid%%;*}
    [ -n "$jobid" ] || { echo "Errore: invio del job fallito, vedi sopra" >&2; exit 1; }

    local out="$RUN/es04_${jobid}.txt"
    [ -f "$out" ] || { echo "Errore: $out non trovato; controlla il job $jobid con squeue/sacct" >&2; exit 1; }
    sed -n '/= RIEPILOGO =/,$p' "$out"
    echo
    echo "File da scaricare (file browser di JupyterLab, clic destro > Download):"
    echo "    $PWD/$out"
}

measure() {
    local RUN=$1 size exe tag v k inner
    cd -- "${SLURM_SUBMIT_DIR:-.}" || exit 1
    echo "Esercitazione 4 — output completo del job ${SLURM_JOB_ID:-?}"
    cat "$RUN/build.txt"

    section "1. Nodo di calcolo e allocazione"
    cmd date
    cmd hostname
    echo "Slurm: job=${SLURM_JOB_ID:-?} partizione=${SLURM_JOB_PARTITION:-?} nodi=${SLURM_JOB_NODELIST:-?} cpus-per-task=${SLURM_CPUS_PER_TASK:-?}"
    cmd lscpu
    cmd getconf LEVEL1_DCACHE_LINESIZE
    cmd perf --version
    cmd "$TIME_BIN" --version
    note "Nodo: $(hostname), job ${SLURM_JOB_ID:-?}, partizione ${SLURM_JOB_PARTITION:-?}"

    section "2. Validazione (modalità check)"
    local c_o c_r v_o v_r
    for size in "1024 32 1" "$N $D 1"; do
        cap $SRUN ./preprocess $size check;      v_o=$(pass); c_o=$(checksum)
        cap $SRUN ./preprocess_rows $size check; v_r=$(pass); c_r=$(checksum)
        note "Validazione '$size check': preprocess $v_o, preprocess_rows $v_r; checksum $c_o / $c_r ($(same "$c_o" "$c_r"))"
    done

    section "3. Checksum su una dimensione diversa (100000 $D $REPS)"
    cap $SRUN ./preprocess 100000 $D $REPS;      c_o=$(checksum)
    cap $SRUN ./preprocess_rows 100000 $D $REPS; c_r=$(checksum)
    note "Checksum '100000 $D $REPS': $c_o / $c_r ($(same "$c_o" "$c_r"))"

    section "4. Timing: $TIMING_RUNS run per versione, alternate ($N $D $REPS)"
    echo "Ogni run è misurata insieme dal time di bash (ms) e da GNU time (cs, più user/sys/max RSS)."
    local T_O=() T_R=() G_O=() G_R=() tb tg c_t=()
    for k in $(seq 1 $TIMING_RUNS); do
        for exe in preprocess preprocess_rows; do
            inner="TIMEFORMAT='bash time: %R s'; time $TIME_BIN -f '$GFMT' ./$exe $N $D $REPS"
            printf '%s%s bash -c "%s"    # run %s\n' "$(prompt)" "$SRUN" "$inner" "$k"
            OUT=$($SRUN bash -c "$inner" 2>&1)
            printf '%s\n' "$OUT"
            tb=$(sed -n 's/^bash time: \([0-9.]*\) s$/\1/p' <<<"$OUT")
            tg=$(sed -n 's/^GNU time: \([0-9.]*\) s elapsed.*/\1/p' <<<"$OUT")
            c_t+=("$(checksum)")
            if [ "$exe" = preprocess ]; then T_O+=("$tb"); G_O+=("$tg"); c_o=$(checksum)
            else T_R+=("$tb"); G_R+=("$tg"); c_r=$(checksum); fi
        done
    done
    local m_o m_r
    m_o=$(median "${T_O[@]}"); m_r=$(median "${T_R[@]}")
    note "Timing time di bash (s): preprocess ${T_O[*]} -> mediana $m_o; preprocess_rows ${T_R[*]} -> mediana $m_r; tempo $(change "$m_o" "$m_r"), speedup $(ratio "$m_o" "$m_r")x"
    m_o=$(median "${G_O[@]}"); m_r=$(median "${G_R[@]}")
    note "Timing GNU time (s): preprocess ${G_O[*]} -> mediana $m_o; preprocess_rows ${G_R[*]} -> mediana $m_r; speedup $(ratio "$m_o" "$m_r")x"
    note "Checksum '$N $D $REPS' nelle run di timing: $(printf '%s\n' "${c_t[@]}" | sort -u | tr '\n' ' ')"
    note "Checksum problema completo, preprocess vs preprocess_rows: $(within_tol "$c_o" "$c_r")"

    # Profili con le ripetizioni della consegna ($REPS, nomi file del corso) e con
    # $PROF_REPS ripetizioni, per avere abbastanza campioni anche dopo l'ottimizzazione.
    section "5. Profili perf record / perf report ($N $D $REPS e $N $D $PROF_REPS)"
    local reps data self_b self_a ev_b ev_a samples self ev
    for reps in $REPS $PROF_REPS; do
        self_b= self_a= ev_b= ev_a=
        for v in before:preprocess after:preprocess_rows; do
            tag=${v%%:*} exe=${v#*:}
            data="$RUN/perf-$tag.data"
            [ "$reps" = "$REPS" ] || data="$RUN/perf-$tag-$reps.data"
            cap $SRUN perf record -e cpu-clock:u -F 99 -g -o "$data" ./$exe $N $D $reps
            samples=$(sed -n 's/.*(\([0-9]*\) samples).*/\1/p' <<<"$OUT")
            note "perf record $tag ($exe, $reps rip.): $samples campioni, checksum $(checksum)"
            cmd perf report --stdio -i "$data"
            cap perf report --stdio --no-children -g none -i "$data"
            self=$(awk '/compute_statistics/ { sub("%", "", $1); print $1; exit }' <<<"$OUT")
            ev=$(sed -n 's/^# Event count (approx.): //p' <<<"$OUT")
            if [ "$tag" = before ]; then self_b=$self ev_b=$ev; else self_a=$self ev_a=$ev; fi
        done
        note "compute_statistics Self ($reps rip.): $self_b% (before) -> $self_a% (after); Event count $ev_b -> $ev_a"
        note "$(amdahl "$reps" "$self_b" "$self_a" "$ev_b" "$ev_a")"
    done

    section "6. Contatori hardware perf stat ($STAT_RUNS rip., $N $D $REPS)"
    local cyc_o cyc_r ins_o ins_r ref_o ref_r mis_o mis_r el_o el_r
    for exe in preprocess preprocess_rows; do
        cap $SRUN perf stat -r $STAT_RUNS -e cycles,instructions,cache-references,cache-misses ./$exe $N $D $REPS
        if [ "$exe" = preprocess ]; then
            cyc_o=$(stat_val cycles) ins_o=$(stat_val instructions) ref_o=$(stat_val cache-references)
            mis_o=$(stat_val cache-misses) el_o=$(awk '/seconds time elapsed/ { print $1; exit }' <<<"$OUT")
        else
            cyc_r=$(stat_val cycles) ins_r=$(stat_val instructions) ref_r=$(stat_val cache-references)
            mis_r=$(stat_val cache-misses) el_r=$(awk '/seconds time elapsed/ { print $1; exit }' <<<"$OUT")
        fi
    done
    note "perf stat cycles: $cyc_o -> $cyc_r ($(change "$cyc_o" "$cyc_r")); instructions: $ins_o -> $ins_r ($(change "$ins_o" "$ins_r")); IPC $(ratio "$ins_o" "$cyc_o") -> $(ratio "$ins_r" "$cyc_r")"
    note "perf stat cache-references: $ref_o -> $ref_r ($(change "$ref_o" "$ref_r")); cache-misses: $mis_o -> $mis_r ($(change "$mis_o" "$mis_r"))"
    note "perf stat elapsed (media $STAT_RUNS rip.): $el_o s -> $el_r s, speedup $(ratio "$el_o" "$el_r")x"

    section "RIEPILOGO"
    printf -- '- %s\n' "${SUMMARY[@]}"
    echo
    cmd ls -l "$RUN"
}

case "${1:-}" in
    "")      submit ;;
    measure) measure "${2:?cartella di run mancante}" ;;
    *)       echo "Uso: bash es04_all.sh" >&2; exit 1 ;;
esac
