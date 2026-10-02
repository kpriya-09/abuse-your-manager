"""Versioned, deterministic baseline. Geography and personalization are future policies."""
from math import exp, log1p

POLICY_VERSION = 'freshness-support-v1'
CANDIDATE_LIMIT = 500
PAGE_SIZE = 20
SNAPSHOT_TTL = 900


def rank_candidates(posts, now):
    """Bounded vote influence; comments are not rewarded just for generating replies."""
    def score(post):
        age_hours = max(0, now - post['created_at']) / 3600
        freshness = 4 / (1 + age_hours / 24)
        support = min(log1p(max(0, post['votes'])), 4) * exp(-age_hours / 168)
        return freshness + support, post['created_at'], post['id']
    return sorted(posts, key=score, reverse=True)
