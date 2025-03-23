import os
import re
import matplotlib.pyplot as plt

PING_DATA_DIR = "ping_data"

mean_delays = []
avg_rtts = []

filename_pattern = re.compile(r"ping_(\d+)ms\.txt")
rtt_pattern = re.compile(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)")

for filename in os.listdir(PING_DATA_DIR):
    match = filename_pattern.match(filename)
    if not match:
        continue

    delay_ms = int(match.group(1))
    file_path = os.path.join(PING_DATA_DIR, filename)

    with open(file_path) as f:
        content = f.read()

    rtt_match = rtt_pattern.search(content)
    if rtt_match:
        avg_rtt = float(rtt_match.group(1))
        mean_delays.append(delay_ms)
        avg_rtts.append(avg_rtt)
    else:
        print(f"Warning: No RTT found in {filename}")

combined = sorted(zip(mean_delays, avg_rtts))
mean_delays, avg_rtts = zip(*combined)

plt.figure(figsize=(8, 5))
plt.plot(mean_delays, avg_rtts, marker='o')

for x, y in zip(mean_delays, avg_rtts):
    plt.text(x + 0.7, y + 0.05, f"{y:.2f}", ha='left', fontsize=10)

plt.xlabel("Mean Random Delay (ms)")
plt.ylabel("Average Ping RTT (ms)")
plt.title("Mean Random Delay vs. Average Ping RTT")
plt.grid(True)

plt.xticks(range(0, max(mean_delays) + 5, 5))

plt.tight_layout()
plt.savefig("rtt_vs_delay_plot.png")
plt.show()
