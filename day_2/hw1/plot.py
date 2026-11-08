#!/usr/bin/env python3
# plot.py — results.csv 를 읽어 그래프 두 개를 그린다
import csv
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOSS = {'loss0': 0, 'loss1': 1, 'loss5': 5, 'loss10': 10}
p95, lossrate = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))

with open('results.csv') as f:
    for row in csv.DictReader(f):
        key = row['tag'].split('_')[0]          # loss5_a -> loss5
        if key not in LOSS:
            continue
        x = LOSS[key]
        p95[row['qos']][x].append(float(row['p95_ms']))
        lossrate[row['qos']][x].append(float(row['loss_pct']))

def avg(d, x):
    return sum(d[x]) / len(d[x])

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for qos, marker in (('reliable', 'o'), ('best_effort', 's')):
    if qos not in p95:
        continue
    xs = sorted(p95[qos])
    ax[0].plot(xs, [avg(p95[qos], x) for x in xs], marker=marker, label=qos)
    ax[1].plot(xs, [avg(lossrate[qos], x) for x in xs], marker=marker, label=qos)

ax[0].set_xlabel('netem loss (%)'); ax[0].set_ylabel('RTT p95 (ms)')
ax[0].set_title('loss vs RTT p95'); ax[0].legend(); ax[0].grid(alpha=.3)
ax[1].set_xlabel('netem loss (%)'); ax[1].set_ylabel('measured loss (%)')
ax[1].set_title('loss vs measured loss'); ax[1].legend(); ax[1].grid(alpha=.3)
plt.tight_layout()
plt.savefig('evidence/graph.png', dpi=150)
print('saved evidence/graph.png')
