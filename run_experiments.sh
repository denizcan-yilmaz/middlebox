#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "❌  aborted at line $LINENO"; exit 1' ERR

##########################################################################
LEN=5                         # seconds for each BENIGN slice
REPEAT=10
PPS_LIST=(1 2 3)
NOP_LIST=(2 3 4)
DELAY_LIST=(0 0.01 0.05)

SENDER_CVT="/code/sec/sender_covert.py"
RECV_CVT="/code/insec/receiver_covert.py"
SENDER_BEN="/code/sec/sender_ben.py"
RECV_BEN="/code/insec/receiver.py"

FLAG_FILE=/tmp/channel_flag
RUN_FILE=/tmp/run_id
CFG_FILE=/tmp/config_str
DELAY_FILE=/tmp/delay_sec
##########################################################################

echo "⚙️  Restarting core containers…"
docker compose up -d nats mitm sec insec python-processor
sleep 2

# Wait until a container responds to 'echo ok'
wait_ready() { until docker exec "$1" bash -c 'echo ok' &>/dev/null; do sleep 0.5; done; }
wait_ready python-processor; wait_ready sec; wait_ready insec

docker exec insec mkdir -p /tmp/doneflags

total=$(( REPEAT * ${#PPS_LIST[@]} * ${#NOP_LIST[@]} * ${#DELAY_LIST[@]} * 2 ))
echo "✅  Will run $total labelled slices."

run_id=0    # monotonic counter

for delay in "${DELAY_LIST[@]}"; do
  for pps in "${PPS_LIST[@]}";  do
    for nop in "${NOP_LIST[@]}"; do
      for ((k=1; k<=REPEAT; k++)); do

        ((run_id+=1))
        cfg="pps${pps}_nop${nop}_d${delay}"
        flag="/tmp/doneflags/run_$run_id"

        # ---------- BENIGN ----------
        echo "run $run_id  benign  LEN=$LEN"
        docker exec python-processor bash -c "echo $run_id  > $RUN_FILE"
        docker exec python-processor bash -c "echo 0       > $FLAG_FILE"
        docker exec python-processor bash -c "echo benign  > $CFG_FILE"
        docker exec python-processor bash -c "echo 0       > $DELAY_FILE"

        docker exec -d insec bash -c "python3 $RECV_BEN"
        docker exec -d sec   bash -c "python3 $SENDER_BEN"
        sleep "$LEN"
        docker exec insec pkill -f "$RECV_BEN"  || true
        docker exec sec   pkill -f "$SENDER_BEN" || true

        # ---------- COVERT ----------
        echo "run $run_id  covert ($cfg)"
        docker exec python-processor bash -c "echo $run_id  > $RUN_FILE"
        docker exec python-processor bash -c "echo 1        > $FLAG_FILE"
        docker exec python-processor bash -c "echo $cfg     > $CFG_FILE"
        docker exec python-processor bash -c "echo $delay   > $DELAY_FILE"

        docker exec -d insec bash -c \
            "python3 $RECV_CVT --nop-bits $nop --pps $pps --done-flag $flag"

        docker exec -d sec bash -c \
            "python3 $SENDER_CVT --nop-bits $nop --pps $pps --delay $delay"

        timeout 90s bash -c "until docker exec insec test -f '$flag'; do sleep 0.2; done"

        docker exec insec rm -f  "$flag"          || true
        docker exec insec pkill -f "$RECV_CVT"    || true
        docker exec sec   pkill -f "$SENDER_CVT"  || true
      done
    done
  done
done

echo "🟢  All slices finished."
docker cp python-processor:/tmp/logs_raw.csv ./logs_raw.csv
echo "📄  Packet log saved → logs_raw.csv"
