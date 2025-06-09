#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "❌  aborted at line $LINENO"; exit 1' ERR

LEN=5
REPEAT=10
PPS_LIST=(1 2 3)
NOP_LIST=(2 3 4)
SENDER_CVT="/code/sec/sender_tpphase2.py"
RECV_CVT="/code/insec/receiver_tpphase2.py"
SENDER_BEN="/code/sec/sender.py"
RECV_BEN="/code/insec/receiver.py"

echo "⚙️  (Re)starting core containers…"
docker compose up -d nats mitm sec insec python-processor
sleep 2

wait_ready () {
    local cname=$1 tries=12
    until docker exec "$cname" bash -c 'echo ok' &>/dev/null; do
        ((tries--)) || { echo "❌  $cname not ready"; exit 1; }
        sleep 0.5
    done
}
wait_ready python-processor
wait_ready sec
wait_ready insec

docker exec insec mkdir -p /tmp/doneflags

total_phases=$(( REPEAT * ${#PPS_LIST[@]} * ${#NOP_LIST[@]} * 2 ))
echo "✅  Containers ready. Running $total_phases phases."

for pps in "${PPS_LIST[@]}"; do
    for nop in "${NOP_LIST[@]}"; do
        for ((k=1; k<=REPEAT; k++)); do

            run_id=$(( ( (pps-1)*${#NOP_LIST[@]} + (nop-2) ) * REPEAT + k ))
            cfg="pps${pps}_nop${nop}"
            flag="/tmp/doneflags/run_${run_id}"

            echo "run $run_id  benign  LEN=${LEN}s"
            docker exec python-processor bash -c "echo $run_id  > /tmp/run_id"
            docker exec python-processor bash -c "echo 0       > /tmp/channel_flag"
            docker exec python-processor bash -c "echo benign  > /tmp/config_str"

            docker exec -d insec bash -c "python3 $RECV_BEN"
            docker exec -d sec   bash -c "python3 $SENDER_BEN"
            sleep "$LEN"
            docker exec insec pkill -f "$RECV_BEN"  || true
            docker exec sec   pkill -f "$SENDER_BEN" || true

            echo "run $run_id  covert ($cfg)"
            docker exec python-processor bash -c "echo $run_id > /tmp/run_id"
            docker exec python-processor bash -c "echo 1       > /tmp/channel_flag"
            docker exec python-processor bash -c "echo $cfg    > /tmp/config_str"

            docker exec -d insec bash -c \
                "python3 $RECV_CVT --nop-bits $nop --pps $pps --done-flag $flag"

            docker exec -d sec bash -c \
                "python3 $SENDER_CVT --message $cfg-$k --nop-bits $nop --pps $pps --delay 0.02"

            timeout 90s bash -c "
                until docker exec insec test -f '$flag'; do
                    sleep 0.2
                done
            "

            docker exec insec rm -f "$flag"            || true
            docker exec insec pkill -f "$RECV_CVT"     || true
            docker exec sec   pkill -f "$SENDER_CVT"   || true

        done
    done
done

echo "🟢  All phases finished."
docker cp python-processor:/tmp/logs_raw.csv ./logs_raw.csv
echo "📄  Packet log saved → logs_raw.csv"
