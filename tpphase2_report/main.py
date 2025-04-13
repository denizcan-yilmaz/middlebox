import pandas as pd
from scipy import stats

df = pd.read_csv('./data/sender_log.csv')

df = df[['nop_bits', 'pps', 'delay', 'duration', 'bps']]

def compute_stats(group):
    n = len(group)
    result = {
        'duration_mean': group['duration'].mean(),
        'bps_mean': group['bps'].mean()
    }

    if n > 1:
        duration_ci = stats.t.interval(0.95, df=n-1, loc=result['duration_mean'], scale=stats.sem(group['duration']))
        bps_ci = stats.t.interval(0.95, df=n-1, loc=result['bps_mean'], scale=stats.sem(group['bps']))
    else:
        duration_ci = (result['duration_mean'], result['duration_mean'])
        bps_ci = (result['bps_mean'], result['bps_mean'])

    result.update({
        'duration_ci_lower': duration_ci[0],
        'duration_ci_upper': duration_ci[1],
        'bps_ci_lower': bps_ci[0],
        'bps_ci_upper': bps_ci[1],
    })

    return pd.Series(result)

result_df = df.groupby(['nop_bits', 'pps', 'delay']).apply(compute_stats).reset_index()

print(result_df)
