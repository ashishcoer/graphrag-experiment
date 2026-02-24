import json, numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path

# ── setup ─────────────────────────────────────────────────────────────────────

out_dir = Path("results/figures")
out_dir.mkdir(parents=True, exist_ok=True)

PIPELINES   = ["bm25", "vector_rag", "graph_only", "graphrag"]
LABELS      = ["BM25", "Vector RAG", "Graph-Only", "GraphRAG"]
COLORS      = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
DIMENSIONS  = ["relevance", "completeness", "coherence", "overall"]

metrics  = json.load(open("results/stats/all_metrics.json"))
cache    = json.load(open("results/stats/judge_cache.json"))
comps    = metrics["comparisons"]

plt.rcParams.update({
    "font.family": "serif", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150
})

# ── Figure 1: LLM-as-judge bar chart (main result) ────────────────────────────

fig, ax = plt.subplots(figsize=(8, 5))
dims   = ["Relevance", "Completeness", "Coherence", "Overall"]
keys   = ["judge_relevance_mean", "judge_completeness_mean",
          "judge_coherence_mean", "judge_overall_mean"]
x      = np.arange(len(dims))
width  = 0.18

for i, (pipe, label, color) in enumerate(zip(PIPELINES, LABELS, COLORS)):
    vals = [metrics["per_pipeline"][pipe][k] for k in keys]
    bars = ax.bar(x + i * width, vals, width, label=label, color=color, alpha=0.88)

ax.set_ylabel("Score (1–5)")
ax.set_title("LLM-as-Judge Evaluation Across Pipelines", fontweight="bold", pad=12)
ax.set_xticks(x + width * 1.5)
ax.set_xticklabels(dims)
ax.set_ylim(4.5, 5.05)
ax.legend(frameon=False)
ax.axhline(5.0, color="gray", linewidth=0.6, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig(out_dir / "fig1_judge_scores.pdf", bbox_inches="tight")
plt.savefig(out_dir / "fig1_judge_scores.png", bbox_inches="tight")
plt.close()
print("Saved fig1_judge_scores")

# ── Figure 2: Box plots of overall judge scores per pipeline ──────────────────

fig, ax = plt.subplots(figsize=(8, 5))
box_data = []
for pipe in PIPELINES:
    scores = [v["overall"] for k, v in cache.items() if k.startswith(pipe + "_")]
    box_data.append(scores)

bp = ax.boxplot(box_data, patch_artist=True, notch=True,
                medianprops=dict(color="black", linewidth=2))
for patch, color in zip(bp["boxes"], COLORS):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)

ax.set_xticklabels(LABELS)
ax.set_ylabel("Overall Judge Score (1–5)")
ax.set_title("Distribution of LLM-as-Judge Overall Scores", fontweight="bold", pad=12)
ax.set_ylim(0, 5.5)
plt.tight_layout()
plt.savefig(out_dir / "fig2_score_distribution.pdf", bbox_inches="tight")
plt.savefig(out_dir / "fig2_score_distribution.png", bbox_inches="tight")
plt.close()
print("Saved fig2_score_distribution")

# ── Figure 3: Radar chart ─────────────────────────────────────────────────────

dim_labels = ["Relevance", "Completeness", "Coherence", "Overall"]
dim_keys   = ["judge_relevance_mean", "judge_completeness_mean",
              "judge_coherence_mean", "judge_overall_mean"]
N = len(dim_labels)
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(dim_labels, size=11)
ax.set_ylim(4.5, 5.0)
ax.set_yticks([4.6, 4.7, 4.8, 4.9, 5.0])
ax.set_yticklabels(["4.6", "4.7", "4.8", "4.9", "5.0"], size=8)

for pipe, label, color in zip(PIPELINES, LABELS, COLORS):
    vals = [metrics["per_pipeline"][pipe][k] for k in dim_keys]
    vals += vals[:1]
    ax.plot(angles, vals, "o-", linewidth=2, label=label, color=color)
    ax.fill(angles, vals, alpha=0.08, color=color)

ax.set_title("Radar: Judge Dimensions per Pipeline", fontweight="bold", pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), frameon=False)
plt.tight_layout()
plt.savefig(out_dir / "fig3_radar.pdf", bbox_inches="tight")
plt.savefig(out_dir / "fig3_radar.png", bbox_inches="tight")
plt.close()
print("Saved fig3_radar")

# ── Figure 4: Latency vs quality scatter ─────────────────────────────────────

fig, ax = plt.subplots(figsize=(7, 5))
for pipe, label, color in zip(PIPELINES, LABELS, COLORS):
    m   = metrics["per_pipeline"][pipe]
    lat = m["lat_mean"]
    score = m["judge_overall_mean"]
    ax.scatter(lat, score, s=180, color=color, zorder=3, label=label)
    ax.annotate(label, (lat, score), textcoords="offset points",
                xytext=(8, 4), fontsize=10)

ax.set_xlabel("Mean Latency (seconds)")
ax.set_ylabel("Mean Overall Judge Score (1–5)")
ax.set_title("Quality vs Latency Trade-off", fontweight="bold", pad=12)
ax.set_ylim(4.85, 5.02)
plt.tight_layout()
plt.savefig(out_dir / "fig4_latency_vs_quality.pdf", bbox_inches="tight")
plt.savefig(out_dir / "fig4_latency_vs_quality.png", bbox_inches="tight")
plt.close()
print("Saved fig4_latency_vs_quality")

# ── Figure 5: Statistical significance (Cohen's d) ───────────────────────────

fig, ax = plt.subplots(figsize=(7, 4))
baselines = ["bm25", "vector_rag", "graph_only"]
bl_labels = ["BM25", "Vector RAG", "Graph-Only"]
ds        = [comps[bl]["d"] for bl in baselines]
pvals     = [comps[bl]["p_corr"] for bl in baselines]
bar_colors = [COLORS[PIPELINES.index(bl)] for bl in baselines]

bars = ax.barh(bl_labels, ds, color=bar_colors, alpha=0.85)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Cohen's d  (GraphRAG − Baseline)")
ax.set_title("Effect Size: GraphRAG vs Baselines (LLM-as-Judge)", fontweight="bold", pad=12)

for bar, pval, d in zip(bars, pvals, ds):
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
    ax.text(d + 0.003, bar.get_y() + bar.get_height() / 2,
            sig, va="center", fontsize=12, fontweight="bold")

plt.tight_layout()
plt.savefig(out_dir / "fig5_effect_sizes.pdf", bbox_inches="tight")
plt.savefig(out_dir / "fig5_effect_sizes.png", bbox_inches="tight")
plt.close()
print("Saved fig5_effect_sizes")

print(f"\nAll figures saved to {out_dir}/")
print("Files: fig1_judge_scores, fig2_score_distribution, fig3_radar, fig4_latency_vs_quality, fig5_effect_sizes")
print("Formats: .pdf (publication) + .png (preview)")