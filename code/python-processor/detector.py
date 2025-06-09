#!/usr/bin/env python3

import time, math, zlib
from collections import deque, Counter
from scapy.all import IP, raw

def _count_nops(pkt) -> int:
    if IP not in pkt:
        return 0
    ihl = pkt[IP].ihl
    return 0 if ihl <= 5 else raw(pkt[IP])[20:20 + (ihl - 5) * 4].count(0x01)

def _entropy(counter: Counter) -> float:
    total = sum(counter.values())
    return -sum(n / total * math.log2(n / total) for n in counter.values())

class SlidingEntropyDetector:
    def __init__(self,
                 win_sec: float = 2.0,
                 thr_opts: float = 0.01,
                 thr_entropy: float = 1.0,
                 thr_comp: float = 0.5):
        self.win_sec     = win_sec
        self.thr_opts    = thr_opts
        self.thr_entropy = thr_entropy
        self.thr_comp    = thr_comp
        self.win: deque  = deque()

    def feed(self, pkt) -> bool:
        now = time.time()
        nop_cnt = _count_nops(pkt)
        opt_bytes = b'' if nop_cnt == 0 else raw(pkt[IP])[20:20 + (pkt[IP].ihl - 5) * 4]

        self.win.append((now, nop_cnt, opt_bytes))
        while self.win and now - self.win[0][0] > self.win_sec:
            self.win.popleft()

        n = len(self.win)
        if n == 0:
            return False

        n_opts = sum(1 for _, c, _ in self.win if c > 0)
        pct_opts = n_opts / n

        counts = Counter(c for _, c, _ in self.win if c > 0)
        ent     = _entropy(counts) if counts else 0.0

        raw_len  = sum(len(o) for *_, o in self.win) or 1
        comp_len = sum(len(zlib.compress(o)) for *_, o in self.win)
        comp_ratio = comp_len / raw_len

        return (pct_opts   > self.thr_opts and
                ent        > self.thr_entropy and
                comp_ratio > self.thr_comp)
