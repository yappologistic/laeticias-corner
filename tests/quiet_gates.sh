#!/bin/bash
# The quiet gate run: every timing gate of the game, one after another, on a machine with
# nothing else to do, and one summary file with pass or fail per gate and the machine's load.
#
#   tests/quiet_gates.sh [OUT_DIR]        (default: out/quiet-gates)
#
# Run it from the checkout's root after `cmake --build --preset release`. It opens no window
# and plays no sound. "Quiet" means: one-minute load under 1.0, no other build, test, bench or
# game running (a second program on the GPU stalls frames for 20 to 40 ms), mains power, and
# **no CPU limit on the shell it runs from**. A shell inside a control group with a CPU quota
# (`cpu.max`; the agents' sessions on the owner's machine share one of four CPUs) is frozen for
# the rest of each 100 ms period whenever the group has used its share, whoever used it: frames
# of 20 to 90 ms on a machine whose load average looks idle, since a frozen program is not
# counted as running. The script records the load and the group's count of such stalls before
# and after every gate and marks a gate that was busy or stalled; such a gate says nothing
# either way and is to be run again (from a plain terminal, where there is no limit).
#
# Gates (streamed runs, as a player's are; frame times with the GPU waited for):
#   ctest            the release suite (its own benches and soak included)
#   bench <renderer> <size>   --bench at a small window, 1080p and 1440p on OpenGL (the
#                    classic look) and on SDL's gpu driver (the look the owner plays, high)
#   startup-look     the look path's start-up frames (the bench's start-up case alone)
#   soak             600 s of busy play: flat memory under its ceiling
#   world-bench      the viewer's cases and the 40 draw calls a city view may make
#   city-bench       the cities' simulation at the cap
set -u
out="${1:-out/quiet-gates}"
bin=build/release/laeticias-corner
[ -x "$bin" ] || { echo "build the release preset first ($bin is missing)" >&2; exit 2; }
mkdir -p "$out"
summary="$out/summary.txt"
saves="$(mktemp -d)"
trap 'rm -rf "$saves"' EXIT
export SDL_AUDIODRIVER=dummy
export LAETICIA_SAVE_DIR="$saves/unused"

load() { cut -d' ' -f1 /proc/loadavg; }
busy() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a > 2.0 || b > 2.0) }'; }
# The nearest control group above this shell with a CPU quota, if there is one.
limited=""
group="/sys/fs/cgroup$(awk -F: '$1 == "0" { print $3 }' /proc/self/cgroup 2>/dev/null)"
while [ -n "$group" ] && [ "$group" != /sys/fs/cgroup ] && [ "$group" != / ]; do
    if [ -r "$group/cpu.max" ] && ! grep -q '^max' "$group/cpu.max"; then
        limited="$group"
        break
    fi
    group="$(dirname "$group")"
done
stalls() {
    if [ -n "$limited" ]; then
        awk '$1 == "nr_throttled" { print $2 }' "$limited/cpu.stat"
    else
        echo 0
    fi
}

{
    echo "Quiet gate run: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Commit: $(git rev-parse --short HEAD 2>/dev/null) $(git status --porcelain 2>/dev/null | grep -q . && echo '(with uncommitted changes)')"
    echo "Machine: $(nproc) CPUs, load at start $(load), governor $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown)"
    if [ -n "$limited" ]; then
        echo "CPU LIMIT: $(cat "$limited/cpu.max") (quota and period in us) on $(basename "$limited"):"
        echo "  timing gates run under it are stalled by whatever else runs in that group."
    else
        echo "CPU limit: none"
    fi
    echo
    printf '%-34s %-6s %-12s %s\n' "gate" "result" "load" "detail"
} > "$summary"

failed=0
# gate NAME LOGFILE COMMAND...   (exit 0 pass, 77 skipped, anything else fail)
gate() {
    local name="$1" log="$2"
    shift 2
    local before after rc result detail stalled
    before="$(load)"
    stalled="$(stalls)"
    "$@" > "$log" 2>&1
    rc=$?
    after="$(load)"
    stalled=$(($(stalls) - stalled))
    case "$rc" in
        0) result=pass ;;
        77) result=skip ;;
        *) result=FAIL; failed=1 ;;
    esac
    detail="$(grep -h 'over budget' "$log" | sed 's/^ *//; s/^bench: //' | sort -u | head -6 | paste -sd';' -)"
    [ -z "$detail" ] && [ "$result" = FAIL ] && detail="$(grep -h 'tests failed\|FAILED\|memory over\|memory grew' "$log" | head -3 | paste -sd';' -)"
    busy "$before" "$after" && detail="(busy machine: run again) $detail"
    [ "$stalled" -gt 0 ] && detail="(stalled $stalled times by the CPU limit: run again outside it) $detail"
    printf '%-34s %-6s %-12s %s\n' "$name" "$result" "$before-$after" "$detail" >> "$summary"
}

gate "ctest release" "$out/ctest.txt" ctest --preset release
for renderer in opengl gpu; do
    quality=classic
    [ "$renderer" = gpu ] && quality=high
    for size in 1580x845 1920x1080 2560x1440; do
        gate "bench $renderer $size" "$out/bench-$renderer-$size.txt" \
            "$bin" --bench --renderer "$renderer" --quality "$quality" --gpu-sync --size "$size" \
            --seed 1 --frames 240 --budget-ms 2 --save-dir "$saves/bench-$renderer-$size"
    done
done
gate "startup-look 2560x1440" "$out/startup-look.txt" \
    "$bin" --bench --renderer gpu --quality high --gpu-sync --size 2560x1440 --seed 1 \
    --frames 240 --budget-ms 2 --bench-case start-up --save-dir "$saves/startup-look"
gate "soak 600 s" "$out/soak.txt" \
    env SDL_VIDEODRIVER=dummy "$bin" --soak 600 --size 640x400 --seed 1 --budget-ms 2 \
    --save-dir "$saves/soak"
gate "world-bench" "$out/world-bench.txt" \
    build/release/laeticias-world --bench --renderer opengl --size 1920x1080
gate "city-bench" "$out/city-bench.txt" build/release/lifeinfo bench --frames 1800

{
    echo
    echo "Load at end $(load). Logs: $out/"
    echo "What moves with the machine and what does not: in a bench log, 'cpu work ... M"
    echo "instructions' and 'pop-in in N of M frames' are the same on a busy machine; 'cpu"
    echo "(thread)' moves a little; 'whole frame' and 'gpu done' need the quiet."
    [ "$failed" = 0 ] && echo "ALL GATES PASSED" || echo "SOME GATES FAILED"
} >> "$summary"
cat "$summary"
exit "$failed"
