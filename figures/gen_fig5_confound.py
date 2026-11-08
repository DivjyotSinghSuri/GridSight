"""Generates figures/fig5_internal_retry_confound.pdf for the GridShield paper.

Two-panel figure, the central visual for the controlled no-internal-resilience
baseline experiment:
  (a) pooled recovery rate per reliability strategy, GridSight's internal
      fetcher-level retry ON (original experiment) vs OFF (controlled
      baseline), n=180 per bar (Experiment 1, 4 fault types x 3
      probabilities x 15 repetitions).
  (b) baseline-strategy recovery rate broken down by fault type, same ON/OFF
      conditions, n=45 per bar (3 probabilities x 15 repetitions) -- shows
      the mechanism: internal retry fully absorbs 3 of 4 fault types when ON,
      and stops absorbing any of them once reduced to a single attempt.

All values are pooled means computed directly from the frozen result CSVs
under gridshield/outputs/experiment_1_reliability (ON) and
gridshield/outputs_no_resilience_baseline/experiment_1_reliability_no_resilience_baseline
(OFF); see the analysis in the paper's Results section. No values here are
invented -- rerun the pooling script against those CSVs to reproduce them.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9,
    "legend.fontsize": 7.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
})

# --- Panel (a): pooled recovery rate per strategy, ON vs OFF ---
strategies = ["Baseline", "Fixed\nRetry", "Exponential\nBackoff", "Checkpointed\nBackoff"]
recovery_on = [0.9954, 1.0000, 1.0000, 1.0000]
recovery_off = [0.8056, 1.0000, 0.9991, 1.0000]

# --- Panel (b): baseline recovery by fault type, ON vs OFF ---
fault_types = ["HTTP 429", "HTTP 500", "Timeout", "Malformed\nPayload"]
baseline_on = [1.0000, 1.0000, 1.0000, 0.9815]
baseline_off = [0.8148, 0.8111, 0.7926, 0.8037]

fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.75))

color_on = "#4C72B0"
color_off = "#C44E52"

# Panel (a)
ax = axes[0]
x = np.arange(len(strategies))
w = 0.34
ax.bar(x - w/2, recovery_on, w, label="Internal retry ON\n(original)", color=color_on, edgecolor="black", linewidth=0.5)
ax.bar(x + w/2, recovery_off, w, label="Internal retry OFF\n(controlled baseline)", color=color_off, edgecolor="black", linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(strategies)
ax.set_ylabel("Pooled recovery rate")
ax.set_ylim(0.70, 1.04)
ax.axhline(1.0, color="gray", linewidth=0.5, linestyle=":")
ax.set_title("(a) Reliability strategies (n=180/bar)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False,
          handlelength=1.2, columnspacing=1.0)
for xi, (von, voff) in enumerate(zip(recovery_on, recovery_off)):
    ax.text(xi - w/2, von + 0.012, f"{von:.3f}", ha="center", va="bottom", fontsize=6.5)
    ax.text(xi + w/2, voff + 0.012, f"{voff:.3f}", ha="center", va="bottom", fontsize=6.5)

# Panel (b)
ax = axes[1]
x = np.arange(len(fault_types))
ax.bar(x - w/2, baseline_on, w, label="Internal retry ON", color=color_on, edgecolor="black", linewidth=0.5)
ax.bar(x + w/2, baseline_off, w, label="Internal retry OFF", color=color_off, edgecolor="black", linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(fault_types)
ax.set_ylabel("Baseline recovery rate")
ax.set_ylim(0.70, 1.04)
ax.axhline(1.0, color="gray", linewidth=0.5, linestyle=":")
ax.set_title("(b) Baseline, by fault type (n=45/bar)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False,
          handlelength=1.2, columnspacing=1.0)
for xi, (von, voff) in enumerate(zip(baseline_on, baseline_off)):
    ax.text(xi - w/2, von + 0.012, f"{von:.3f}", ha="center", va="bottom", fontsize=6.5)
    ax.text(xi + w/2, voff + 0.012, f"{voff:.3f}", ha="center", va="bottom", fontsize=6.5)

for ax in axes:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.tight_layout(pad=0.6, w_pad=1.8, rect=(0, 0.08, 1, 1))
fig.savefig("figures/fig5_internal_retry_confound.pdf", bbox_inches="tight")
print("wrote figures/fig5_internal_retry_confound.pdf")
