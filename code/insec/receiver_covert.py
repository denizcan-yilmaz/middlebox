#!/usr/bin/env python3
import os, sys, time, argparse, signal, csv, pathlib, random
from datetime import datetime
from collections import Counter
from scapy.all import sniff, IP, UDP, raw

# ── SCRAMBLE SETTINGS (must match sender) ─────────────────────────────────
SESSION_KEY = b"2444172"
def make_mask(idx: int, bits: int) -> int:
    rnd = random.Random(hash((SESSION_KEY, idx)) & 0xFFFFFFFF)
    return rnd.randrange(1 << bits)

def count_nops(pkt) -> int:
    ihl = pkt[IP].ihl
    if ihl <= 5:
        return 0
    # Extract the options bytes
    opts = raw(pkt[IP])[20 : 20 + (ihl - 5) * 4]
    # Strip fake Timestamp if present
    if opts.startswith(b"\x44\x04"):
        opts = opts[4:]
    # Count only NOPs
    return opts.count(0x01)

def bits_to_text(symbols, bits_per_symbol):
    bitstr = ''.join(f'{s:0{bits_per_symbol}b}' for s in symbols)
    bitstr = bitstr[: len(bitstr) - (len(bitstr) % 8)]
    return ''.join(
        chr(int(bitstr[i:i+8], 2)) for i in range(0, len(bitstr), 8)
    ).rstrip('\x00')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat",    type=int,   default=1,
                    help="Capture this many messages before quitting")
    ap.add_argument("--nop-bits",  dest="nop_bits", type=int, default=3,
                    help="Bits per symbol (max 5)")
    ap.add_argument("--pps",       type=int,   default=1,
                    help="Packets per symbol expected")
    ap.add_argument("--done-flag", default="",
                    help="Touch this file when message completes")
    ap.add_argument("--port",      type=int,   default=8888)
    ap.add_argument("--timeout",   type=int,   default=60)
    ap.add_argument("-i", "--iface", default=os.getenv("SNIFF_IFACE", "eth0"))
    args = ap.parse_args()

    if args.nop_bits > 5:
        sys.exit("receiver supports ≤ 5 bits per symbol")

    START, END = (1 << args.nop_bits), (1 << args.nop_bits) + 1

    csv_name = "receiver_log.csv"
    if not pathlib.Path(csv_name).exists():
        with open(csv_name, "w", newline="") as f:
            csv.writer(f).writerow([
                "run_idx","nop_bits","pps","port","iface",
                "bits","duration","bps","message","timestamp"
            ])

    runs, state, pkbuf, symbols, t0 = 0, "waiting", [], [], None
    start_seen, end_seen = 0, 0
    done = {"stop": False}

    def finish():
        nonlocal runs, symbols, t0
        if not symbols:
            return
        runs += 1
        dur  = time.time() - t0
        bits = len(symbols) * args.nop_bits
        bps  = bits / dur
        msg  = bits_to_text(symbols, args.nop_bits)
        print(f"[run {runs}/{args.repeat}] {bits} bits in {dur:.2f}s → {bps:.2f} bps  msg={msg!r}")

        with open(csv_name, "a", newline="") as f:
            csv.writer(f).writerow([
                runs, args.nop_bits, args.pps, args.port, args.iface,
                bits, f"{dur:.4f}", f"{bps:.2f}", msg,
                datetime.now().isoformat()
            ])

        if args.done_flag:
            pathlib.Path(args.done_flag).touch()
        symbols.clear()

        if runs >= args.repeat:
            done["stop"] = True
        else:
            signal.alarm(args.timeout)

    def handler(pkt):
        nonlocal state, pkbuf, symbols, t0, start_seen, end_seen

        if UDP not in pkt or pkt[UDP].dport != args.port:
            return
        val = count_nops(pkt)

        if state == "waiting":
            if val == START:
                start_seen += 1
                if start_seen == 3:
                    state, pkbuf, symbols = "recv", [], []
                    t0 = time.time()
                    start_seen = 0
            return

        if state == "recv":
            if val == END:
                end_seen += 1
                if end_seen == 3:
                    state    = "waiting"
                    end_seen = 0
                    finish()
                return

            if val in (START, END):
                return

            pkbuf.append(val)
            while len(pkbuf) >= args.pps:
                block = pkbuf[:args.pps]
                voted = Counter(block).most_common(1)[0][0]
                # Unscramble the masked symbol
                idx = len(symbols)
                plain = voted ^ make_mask(idx, args.nop_bits)
                symbols.append(plain)
                del pkbuf[:args.pps]

    signal.signal(signal.SIGALRM, lambda *_: done.__setitem__("stop", True))
    signal.alarm(args.timeout)

    print(f"[*] Sniffing UDP/{args.port} on {args.iface}")
    sec_ip = os.getenv("SECURENET_HOST_IP", "10.0.0.20")
    pcap_filter = f"udp and port {args.port} and src host {sec_ip}"

    sniff(
        iface=args.iface,
        filter=pcap_filter,
        prn=handler,
        store=False,
        stop_filter=lambda *_: done["stop"]
    )

if __name__ == "__main__":
    main()
