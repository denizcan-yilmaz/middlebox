#!/usr/bin/env python3

import os, time, asyncio, random, csv
from nats.aio.client import Client as NATS
from scapy.all import Ether, IP
from detector import SlidingEntropyDetector

MEAN_DELAY = float(os.getenv("MEAN_DELAY_SEC", "0.05"))
FLAG_FILE  = "/tmp/channel_flag"
RUN_FILE   = "/tmp/run_id"
CFG_FILE   = "/tmp/config_str"
RAW_CSV    = "/tmp/logs_raw.csv"

det = SlidingEntropyDetector(
    win_sec     = float(os.getenv("DET_WIN_SEC",  "2")),
    thr_opts    = float(os.getenv("DET_THR_OPTS", "0.01")),
    thr_entropy = float(os.getenv("DET_THR_ENT",  "1.0")),
    thr_comp    = float(os.getenv("DET_THR_COMP", "0.5")),
)

if not os.path.exists(RAW_CSV):
    with open(RAW_CSV, "w", newline="") as f:
        csv.writer(f).writerow(
            ["ts","run","truth","pred","config","src","dst","proto"]
        )

async def make_handler(nc: NATS):
    async def handler(msg):
        data = msg.data
        pkt  = Ether(data)

        print(f"Received on '{msg.subject}' len={len(data)}")
        print(pkt.show())

        truth  = int(open(FLAG_FILE).read().strip())   if os.path.exists(FLAG_FILE) else 0
        run_id = int(open(RUN_FILE ).read().strip())   if os.path.exists(RUN_FILE ) else 0
        cfg    =     open(CFG_FILE ).read().strip()    if os.path.exists(CFG_FILE ) else "unknown"

        pred   = int(det.feed(pkt))
        ts     = time.time()

        ip_src = pkt[IP].src if IP in pkt else ""
        ip_dst = pkt[IP].dst if IP in pkt else ""
        l4name = pkt.payload.__class__.__name__
        with open(RAW_CSV, "a", newline="") as f:
            csv.writer(f).writerow(
                [f"{ts:.6f}", run_id, truth, pred, cfg, ip_src, ip_dst, l4name]
            )

        print(f"LOG {ts:.3f} {run_id} {truth} {pred} {cfg}")

        if pred:
            alert = f"[ALERT] covert-detected run={run_id} cfg={cfg} ts={ts:.3f}"
            print(alert, flush=True)
            await nc.publish("covert.alert", alert.encode())

        await asyncio.sleep(random.expovariate(1 / MEAN_DELAY))
        subj_out = "outpktinsec" if msg.subject == "inpktsec" else "outpktsec"
        await nc.publish(subj_out, data)
    return handler

async def main():
    nc = NATS()
    await nc.connect(os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222"))
    handler = await make_handler(nc)

    await nc.subscribe("inpktsec",   cb=handler)
    await nc.subscribe("inpktinsec", cb=handler)
    print("python-processor online – relaying & detecting")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
