#!/usr/bin/env python3
import csv, pathlib, time, socket, os

def udp_sender():
    csv_name = "sender_ben_log.csv"
    if not pathlib.Path(csv_name).exists():
        with open(csv_name, "w", newline="") as f:
            csv.writer(f).writerow(["ts", "dst", "port", "bytes", "rtt"])

    host = os.getenv("INSECURENET_HOST_IP")
    port = 8888
    message = os.getenv("BENIGN_MSG", "Hello, InSecureNet!")

    if not host:
        print("INSECURENET_HOST_IP environment variable is not set.")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        t0 = time.time()
        sock.sendto(message.encode(), (host, port))
        response, _ = sock.recvfrom(4096)          # echo from receiver
        t1 = time.time()
        rtt = t1 - t0

        with open(csv_name, "a", newline="") as f:
            csv.writer(f).writerow(
                [f"{t1:.6f}", host, port, len(message), f"{rtt:.4f}"]
            )

        print(f"TX→RX round-trip {rtt:.3f}s  (one-shot, exiting)")
    finally:
        sock.close()                               # process ends here

if __name__ == "__main__":
    udp_sender()
