import os, sys, time, argparse, random, csv, pathlib
from datetime import datetime
from scapy.all import IP, UDP, Raw, send

def pad4(opt: bytes) -> bytes:
    return opt + b"\x00" * ((4 - (len(opt) & 3)) & 3)

def build_opts(n: int) -> bytes:
    return b"" if n == 0 else pad4(b"\x01" * n)

def text_to_symbols(txt: str, bits: int):
    bitstr = "".join(f"{ord(c):08b}" for c in txt)
    bitstr += "0" * ((-len(bitstr)) % bits)
    return [int(bitstr[i : i + bits], 2) for i in range(0, len(bitstr), bits)]

def send_once(cfg):
    if cfg.nop_bits > 5:
        sys.exit("nop‑mapping‑bits cannot exceed 5")

    START, END = (1 << cfg.nop_bits), (1 << cfg.nop_bits) + 1
    symbols = text_to_symbols(cfg.message, cfg.nop_bits)

    def pkt(sym, tag=b"DATA"):
        return (IP(dst=cfg.target_ip, options=build_opts(sym))
                / UDP(sport=random.randint(1024, 65535), dport=cfg.port)
                / Raw(load=tag))

    t0 = time.time()
    for _ in range(3):              send(pkt(START, b"START"), iface=cfg.iface, verbose=False); time.sleep(cfg.delay)
    for s in symbols:
        for _ in range(cfg.pps):
            send(pkt(s), iface=cfg.iface, verbose=False); time.sleep(cfg.delay)
    for _ in range(3):              send(pkt(END,   b"END"),   iface=cfg.iface, verbose=False); time.sleep(cfg.delay)

    dur  = time.time() - t0
    bits = len(symbols) * cfg.nop_bits
    return bits, dur, bits / dur

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1,
                    help="Run this configuration N times")
    ap.add_argument("--message", default="Hello from SEC!")
    ap.add_argument("--nop-bits",  dest="nop_bits", type=int, default=3,
                    help="Bits per symbol (max 5)")
    ap.add_argument("--delay",     type=float, default=0.1,
                    help="Inter‑packet delay (s)")
    ap.add_argument("--pps",       type=int, default=1,
                    help="Packets per symbol (redundancy)")
    ap.add_argument("--target-ip",
                    default=os.getenv("INSECURENET_HOST_IP", "10.0.0.15"))
    ap.add_argument("--port", type=int, default=8888)
    ap.add_argument("-i", "--iface", default=os.getenv("SND_IFACE", "eth0"))
    args = ap.parse_args()

    csv_name = "sender_log.csv"
    if not pathlib.Path(csv_name).exists():
        with open(csv_name, "w", newline="") as f:
            csv.writer(f).writerow(
                ["run_idx","message","nop_bits","pps","delay","target_ip","port",
                 "bits","duration","bps","timestamp"]
            )

    for idx in range(1, args.repeat + 1):
        bits, dur, bps = send_once(args)
        print(f"[run {idx}/{args.repeat}] {bits} bits in {dur:.2f}s → {bps:.2f} bps")
        with open(csv_name, "a", newline="") as f:
            csv.writer(f).writerow(
                [idx, args.message, args.nop_bits, args.pps, args.delay,
                 args.target_ip, args.port, bits, f"{dur:.4f}",
                 f"{bps:.2f}", datetime.now().isoformat()]
            )

if __name__ == "__main__":
    main()
