"""
Turning two numbers into one, and one number into something a person can read.
← YOU BUILD THIS IN MILESTONES 4 AND 5

Two functions live here, and both are stubs.

`combine_signals` is where your false-positive decision from Milestone 1
actually gets made. Everything above it — the labels, the appeal path — is
downstream of a number this function produced.

`score_to_label` is where you stop writing for a machine and start writing for
a person. A score of 0.62 means nothing to a writer.

⚠️ Your README's **Signals and Scoring** section has to name the file and
function holding your combining rule. The grader checks your code against what
you claim, so that line should read `scoring.py::combine_signals`.
"""

import config


def combine_signals(model_score: float, style_score: float) -> float:
    """
    Combine two 0–1 signals into one 0–1 score.

    Both inputs point the same way: higher means more likely AI.

    Args:
        model_score: from `detector.model_signal` — how predictable the text is.
        style_score: from `stylometry.style_signal` — the shape of the text.

    Returns:
        A float from 0.0 (confidently human) to 1.0 (confidently AI).

    The rule (UPDATED for better separation):
    - Weight model signal at 0.65, style signal at 0.35 (model more robust)
    - When signals AGREE (both >0.55 or both <0.45), amplify slightly
      to create more separation between clear cases
    - When signals strongly disagree (difference > 0.4), pull toward middle
    - Favors false negatives over false positives
    """
    # Updated weights favoring the model signal more strongly
    model_weight = 0.65
    style_weight = 0.35

    # Base weighted average
    combined = model_weight * model_score + style_weight * style_score

    # Agreement amplification: when signals agree on direction, push further
    # This creates more separation between confident human and confident AI
    if model_score > 0.55 and style_score > 0.55:
        # Both signals say "AI" - amplify slightly toward AI
        push_factor = min((model_score - 0.55) * (style_score - 0.55) * 0.5, 0.1)
        combined = min(combined + push_factor, 1.0)
    elif model_score < 0.45 and style_score < 0.45:
        # Both signals say "human" - amplify slightly toward human
        push_factor = min((0.45 - model_score) * (0.45 - style_score) * 0.5, 0.1)
        combined = max(combined - push_factor, 0.0)

    # Disagreement handling: when signals split significantly, pull toward 0.5
    disagreement = abs(model_score - style_score)
    if disagreement > 0.4:
        # Strong disagreement = uncertainty
        uncertainty_factor = (disagreement - 0.4) / 0.6
        combined = combined * (1 - uncertainty_factor * 0.3) + 0.5 * (uncertainty_factor * 0.3)

    return combined


def score_to_label(score: float) -> tuple[str, str]:
    """
    Turn a score into a guess and the text a reader actually sees.

    Returns:
        (guess, label_text) — where `guess` is a short machine-readable string
        like "ai" / "human" / "unsure", and `label_text` is the full sentence
        shown to a person.
    """
    if score >= config.AI_THRESHOLD:
        return "ai", (
            "This text shows patterns commonly found in AI-generated writing. "
            "If you wrote this yourself, you can appeal this decision."
        )

    if score <= config.HUMAN_THRESHOLD:
        return "human", (
            "This text appears to have been written by a person."
        )

    return "unsure", (
        "We're uncertain about this text. It has some patterns that could go either way. "
        "This isn't an accusation — just means our system can't make a confident call here."
    )


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 – {config.HUMAN_THRESHOLD:.2f}"),
        ("unsure", f"{config.HUMAN_THRESHOLD:.2f} – {config.AI_THRESHOLD:.2f}"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} – 1.00"),
    ]
