"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies.

    Returns:
        Coefficient of variation (stdev/mean) of sentence word counts.
        Higher values indicate more varied sentence lengths (more human-like).
        Returns 0.0 for single-sentence or empty text.
    """
    sents = sentences(text)
    if len(sents) < 2:
        # Edge case: can't compute spread for 0 or 1 sentence
        return 0.0

    lengths = [len(words(s)) for s in sents]
    mean_length = statistics.mean(lengths)

    if mean_length == 0:
        return 0.0

    # Coefficient of variation: stdev/mean makes it scale-independent
    return statistics.stdev(lengths) / mean_length


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words.

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary (more human-like).
        Returns 0.0 for empty text.
    """
    word_list = words(text)
    if not word_list:
        return 0.0

    unique_words = len(set(word_list))
    total_words = len(word_list)

    return unique_words / total_words


def punctuation_density(text: str) -> float:
    """
    How much punctuation, relative to length.

    Returns:
        Count of varied punctuation (commas, semicolons, dashes, colons)
        divided by text length. Higher values indicate more complex punctuation
        (more human-like). Returns 0.0 for empty text.

        Focuses on "interesting" punctuation that varies between writers,
        not periods/question marks which are just sentence endings.
    """
    if not text:
        return 0.0

    # Count interesting punctuation: commas, semicolons, colons, dashes, parentheses
    interesting_punct = r'[,;:\-—–(){}[\]]'
    punct_count = len(re.findall(interesting_punct, text))

    return punct_count / len(text)


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.**

    Combines three measures (sentence spread, vocabulary diversity, punctuation)
    where each naturally points "higher = more human", so we flip them to match
    the detector's "higher = more AI" convention.

    Scaling approach:
    - sentence_length_spread: typically 0.0-1.0 (coefficient of variation)
    - type_token_ratio: naturally 0.0-1.0
    - punctuation_density: typically 0.0-0.1, scaled up by 10x

    All three are inverted (1 - value) so low human-ness = high AI score.
    """
    spread = sentence_length_spread(text)
    ttr = type_token_ratio(text)
    punct = punctuation_density(text)

    # Scale punctuation to roughly 0-1 range (typical density ~0.05, max ~0.15)
    punct_scaled = min(punct * 10, 1.0)

    # All three measures are "higher = more human", so invert them
    # to get "higher = more AI" signal
    spread_ai = 1.0 - min(spread, 1.0)  # Cap spread at 1.0 before inverting
    ttr_ai = 1.0 - ttr
    punct_ai = 1.0 - punct_scaled

    # Average the three inverted measures
    # Equal weighting: each measure contributes 1/3
    style_score = (spread_ai + ttr_ai + punct_ai) / 3.0

    return style_score


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
    print("\nAll zeros? These are stubs — Milestone 4 is where you build them.")
