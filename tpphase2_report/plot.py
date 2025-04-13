import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

df = pd.read_csv('./data/sender_log.csv')

df = df[['nop_bits', 'pps', 'delay', 'duration', 'bps']]

def compute_stats(group):
    n = len(group)
    duration_mean = group['duration'].mean()
    bps_mean = group['bps'].mean()

    if n > 1:
        duration_ci = stats.t.interval(0.95, df=n-1, loc=duration_mean, scale=stats.sem(group['duration']))
        bps_ci = stats.t.interval(0.95, df=n-1, loc=bps_mean, scale=stats.sem(group['bps']))
    else:
        duration_ci = (duration_mean, duration_mean)
        bps_ci = (bps_mean, bps_mean)

    return pd.Series({
        'duration_mean': duration_mean,
        'bps_mean': bps_mean,
        'duration_ci': f"({duration_ci[0]:.2f}, {duration_ci[1]:.2f})",
        'bps_ci': f"({bps_ci[0]:.2f}, {bps_ci[1]:.2f})",
        'duration_ci_lower': duration_ci[0],
        'duration_ci_upper': duration_ci[1],
        'bps_ci_lower': bps_ci[0],
        'bps_ci_upper': bps_ci[1],
    })

def analyze_by(key):
    grouped = df.groupby(key).apply(compute_stats).reset_index()

    plt.figure(figsize=(10, 5))
    plt.errorbar(grouped[key], grouped['duration_mean'], 
                 yerr=[grouped['duration_mean'] - grouped['duration_ci_lower'], 
                       grouped['duration_ci_upper'] - grouped['duration_mean']],
                 fmt='o', capsize=5, label='Duration')
    plt.title(f"Duration Mean ± 95% CI grouped by {key}")
    plt.xlabel(key)
    plt.ylabel("Duration (s)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{key}_duration.png")

    plt.figure(figsize=(10, 5))
    plt.errorbar(grouped[key], grouped['bps_mean'], 
                 yerr=[grouped['bps_mean'] - grouped['bps_ci_lower'], 
                       grouped['bps_ci_upper'] - grouped['bps_mean']],
                 fmt='o', capsize=5, label='BPS', color='orange')
    plt.title(f"BPS Mean ± 95% CI grouped by {key}")
    plt.xlabel(key)
    plt.ylabel("Bits per Second")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{key}.png")

    return grouped[[key, 'duration_mean', 'duration_ci', 'bps_mean', 'bps_ci']]

df_nop_bits = analyze_by('nop_bits')
df_pps = analyze_by('pps')
df_delay = analyze_by('delay')

print("\nGrouped by nop_bits:\n", df_nop_bits)
print("\nGrouped by pps:\n", df_pps)
print("\nGrouped by delay:\n", df_delay)
