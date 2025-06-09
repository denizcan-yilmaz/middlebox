#!/usr/bin/env python3
import socket, os, csv, pathlib, time

def start_udp_listener():
    csv_name = "receiver_ben_log.csv"
    if not pathlib.Path(csv_name).exists():
        with open(csv_name, "w", newline="") as f:
            csv.writer(f).writerow(["ts", "src", "bytes", "service"])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 8888))
    print("UDP listener started on port 8888")

    while True:
        data, address = sock.recvfrom(4096)
        t0 = time.time()
        sent = sock.sendto(data, address)
        t1 = time.time()
        srv = t1 - t0
        print(f"RX {len(data)}B → TX {sent}B  service={srv:.3f}s")

        with open(csv_name, "a", newline="") as f:
            csv.writer(f).writerow(
                [f"{t1:.6f}", address[0], len(data), f"{srv:.4f}"]
            )

if __name__ == "__main__":
    start_udp_listener()
