def calculate_overall_score(
    description_judge,
    content_judge,
    impact_score=None,
    compatibility_score=None,
    community_score=None,
):
    # Weighted average: 40% description, 40% content, 20% (impact+compatibility+community if present)
    weights = []
    scores = []
    weights.append(0.4)
    scores.append(description_judge.normalized_score * 100)
    weights.append(0.4)
    scores.append(content_judge.normalized_score * 100)
    extra_scores = [
        s for s in (impact_score, compatibility_score, community_score) if s is not None
    ]
    if extra_scores:
        weights.append(0.2)
        scores.append(sum(extra_scores) / len(extra_scores))
    else:
        # If no extra scores, distribute weight to main scores
        weights[0] += 0.1
        weights[1] += 0.1
    overall = sum(w * s for w, s in zip(weights, scores)) / sum(weights)
    return int(round(overall))


def determine_quality_gate(overall_score, blocking_issues, requires_human_review):
    if overall_score is None:
        return "unscored"
    if overall_score < 50 or (blocking_issues and len(blocking_issues) > 0):
        return "fail"
    if requires_human_review:
        return "warn"
    if overall_score >= 80 and not blocking_issues:
        return "pass"
    if 50 <= overall_score < 80:
        return "warn"
    return "unscored"
