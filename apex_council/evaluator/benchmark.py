from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List

from ..engine import CouncilEngine
from ..models import ModelProvider

BENCHMARK_CHALLENGES = [
    {
        "id": "SWE-01",
        "title": "Thread-Safe LRU Cache with TTL Expiry",
        "prompt": "Implement a high-throughput, thread-safe generic LRU Cache with microsecond TTL expiration and clean eviction callbacks.",
    },
    {
        "id": "SWE-02",
        "title": "Token Bucket Rate Limiter with Sliding Window",
        "prompt": "Implement a high-concurrency Token Bucket rate limiter supporting bursting and sliding window replenish logic.",
    },
    {
        "id": "SWE-03",
        "title": "Constant-Time HMAC Authenticator (Replay Safe)",
        "prompt": "Implement a cryptographic HMAC-SHA256 signature verifier with timestamp replay window defense and constant-time comparison.",
    },
    {
        "id": "SWE-04",
        "title": "Exponential Backoff & Jitter Retry Engine",
        "prompt": "Build an asynchronous resilient retry engine with full jitter, circuit-breaker tripping, and custom exception filtering.",
    },
    {
        "id": "SWE-05",
        "title": "Distributed Lease Mutex with Heartbeat",
        "prompt": "Design a fault-tolerant distributed lease lock pattern with automatic background heartbeat renewal and monotonic clock expiration.",
    },
]


@dataclass
class ModelTournamentStats:
    provider: ModelProvider
    wins: int = 0
    total_score: float = 0.0
    avg_security: float = 0.0
    avg_latency_ms: float = 0.0


def run_benchmark_tournament(force_offline: bool = False) -> Dict[str, Any]:
    """Runs the 5-Challenge SWE Benchmark across Gemini, Claude, and OpenAI."""
    start_time = time.perf_counter()
    engine = CouncilEngine(force_offline=force_offline)

    stats: Dict[ModelProvider, ModelTournamentStats] = {
        p: ModelTournamentStats(provider=p) for p in [ModelProvider.GEMINI, ModelProvider.CLAUDE, ModelProvider.OPENAI]
    }

    challenge_results = []

    for challenge in BENCHMARK_CHALLENGES:
        res = engine.convene_council(challenge["prompt"])
        winner = res.winner
        stats[winner].wins += 1

        for p, eval_score in res.evaluations.items():
            stats[p].total_score += eval_score.overall_score
            stats[p].avg_security += eval_score.security_score
            stats[p].avg_latency_ms += eval_score.execution_time_ms

        challenge_results.append({
            "id": challenge["id"],
            "title": challenge["title"],
            "winner": winner.value,
            "winner_score": res.evaluations[winner].overall_score,
        })

    # Average metrics
    n_challenges = len(BENCHMARK_CHALLENGES)
    for p in stats.values():
        p.avg_security = round(p.avg_security / n_challenges, 1)
        p.avg_latency_ms = round(p.avg_latency_ms / n_challenges, 1)
        p.total_score = round(p.total_score / n_challenges, 1)

    # Sort leaderboard by average total score
    leaderboard = sorted(stats.values(), key=lambda s: (s.wins, s.total_score), reverse=True)

    total_duration = (time.perf_counter() - start_time) * 1000

    return {
        "challenges_run": n_challenges,
        "duration_ms": round(total_duration, 1),
        "leaderboard": [
            {
                "rank": idx + 1,
                "provider": s.provider.value,
                "wins": s.wins,
                "composite_score": s.total_score,
                "avg_security": f"{s.avg_security}%",
                "avg_latency": f"{s.avg_latency_ms} ms",
            }
            for idx, s in enumerate(leaderboard)
        ],
        "challenge_breakdown": challenge_results,
    }


def format_benchmark_table(bench_data: Dict[str, Any]) -> str:
    lines = []
    lines.append("\n==========================================================================")
    lines.append("   🏆 APEX-COUNCIL SWE BENCHMARK LEADERBOARD (5 Production Challenges)   ")
    lines.append("==========================================================================")
    lines.append(f"{'Rank':<5} | {'Model Provider':<22} | {'Wins':<6} | {'Avg Score':<12} | {'Security':<10} | {'Latency'}")
    lines.append("-" * 74)

    medals = ["🥇 1st", "🥈 2nd", "🥉 3rd"]
    for row in bench_data["leaderboard"]:
        rank_badge = medals[row["rank"] - 1] if row["rank"] <= 3 else f"#{row['rank']}"
        lines.append(
            f"{rank_badge:<5} | {row['provider']:<22} | {row['wins']:<6} | {row['composite_score']:<12} | {row['avg_security']:<10} | {row['avg_latency']}"
        )

    lines.append("-" * 74)
    lines.append("\nChallenge Breakdown:")
    for c in bench_data["challenge_breakdown"]:
        lines.append(f"  • [{c['id']}] {c['title']}: Winner ➔ {c['winner']} ({c['winner_score']}/100)")
    lines.append("==========================================================================\n")
    return "\n".join(lines)
