MIN_Q     = 4
MAX_Q     = 15
DEFAULT_Q = 6


def question_count(trigger: str, n_source_topics: int, kg_ctx: dict) -> int:
    n_concepts = len(kg_ctx.get("concepts", []))
    base = DEFAULT_Q if n_concepts == 0 else min(n_concepts + 2, MAX_Q)
    base += min(n_source_topics - 1, 3)
    if trigger in ("weak_performance", "repetitive_asking"):
        base += 2
    return max(MIN_Q, min(base, MAX_Q))


def time_limit(n: int) -> int:
    return max(5, round(n * 1.5 / 5) * 5)
