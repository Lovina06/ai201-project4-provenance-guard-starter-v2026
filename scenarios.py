"""
What your test runs. ← UNIT 8, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
false positives needs your own writing. One about label coverage needs inputs
across the score range. One about the appeal path needs a real content_id.

Working that out is Milestone 3's first step, and this file is where you write
it down. `run_eval.py` runs everything here three times.

Two are filled in as examples. Replace them with what your criteria actually
need — these are a shape, not a set.

A scenario carries **either** of these:

    "texts"   a list of strings. Each is sent as {"text": ..., "creator_id": ...}
              with a creator_id made up for you. Use this for most criteria.

    "bodies"  a list of whole request bodies, sent exactly as written. Use this
              when the malformed request IS the point — empty text, no `text`
              field at all, something enormous. A bad-input criterion needs it,
              because you cannot express "the field is missing" as a string.
"""

SCENARIOS = [
    {
        "name": "my own writing - false positive test",
        "criterion": 1,
        # Real writing I composed for this test. 10 pieces varying in style.
        "texts": [
            "Working through these test cases, I noticed the model struggles most with simple, direct writing. Not because it's wrong - just predictable.",
            "The system design here is straightforward: two signals, one combination rule, three labels. What's not obvious from the code is how the thresholds interact.",
            "I chose 0.6/0.4 weighting because the model signal is harder to manipulate. Style measures are trivially spoofed with typos.",
            "Rate limiting by creator_id seemed right. Same person, different devices? They share a limit. Different people, same IP? Each gets their own. Trade-offs everywhere.",
            "The appeal path matters more than anything else. If someone's wrongly accused, that endpoint is their only recourse. Has to work 100% of the time.",
            "Three labels felt necessary. Two categories (human/AI) force confidence the system doesn't have. The unsure band acknowledges what the system genuinely doesn't know.",
            "Testing revealed something unexpected: simple text scores worse than complex text on the model signal. Predictability punishes clarity.",
            "Documentation took longer than code. Explaining why a threshold is 0.65 instead of 0.75 requires thinking through who pays for each number.",
            "The hardest part? Writing labels for real people. Not 'confidence 0.81' but 'we think this was probably written by a person.' Same information, completely different impact.",
            "Looking back at the criteria, I should have made the false positive target tighter. 2 in 10 feels generous now that I see how the system actually behaves.",
        ],
    },
    {
        "name": "score separation - clear cases",
        "criterion": 2,
        # One clear AI, one clear human - need ≥0.30 separation
        "texts": [
            # AI-generated (generic, predictable patterns)
            "The implementation of machine learning systems requires careful consideration of various factors. These include data preprocessing, model selection, and hyperparameter tuning. By following established best practices, developers can achieve optimal results in their applications. It is important to validate models thoroughly before deployment.",
            # Human-written (specific, varied, personal voice)
            "Yesterday I tripped over my cat while carrying coffee. The mug flew up, spun twice - I swear I watched it in slow motion - and landed perfectly upright on the carpet. Not a drop spilled. I'm calling that my superpower now, even though it was pure dumb luck and the cat looked thoroughly unimpressed by the whole performance.",
        ],
    },
    {
        "name": "label coverage - all three reachable",
        "criterion": 3,
        # 15 diverse tests to ensure all labels appear at least once
        "texts": [
            # Clearly AI-generated (5 examples)
            "Artificial intelligence has revolutionized numerous industries. The technology continues to advance rapidly, offering new possibilities for innovation and efficiency.",
            "Machine learning algorithms process large datasets to identify patterns. These patterns enable predictive analytics and automated decision-making systems.",
            "The benefits of automation include increased productivity and reduced operational costs. Organizations can leverage these advantages to remain competitive.",
            "Data science combines statistical analysis with computational methods. This interdisciplinary approach yields valuable insights from complex information.",
            "Natural language processing enables computers to understand human communication. Applications range from chatbots to language translation services.",

            # Clearly human (5 examples - personal, specific, varied)
            "So my neighbor's kid asked me what I do for work. Tried explaining AI detection. She goes 'so you're like a lie detector for robots?' Honestly? Best job description I've heard.",
            "Three bugs left. One's a typo I made five minutes ago. One's been there since January. One doesn't exist - I'm pretty sure I'm just tired and seeing things in the logs that aren't there.",
            "Watched someone get mad at self-checkout again today. Sir, yelling 'BANANA' louder doesn't make the scale work better. Trust me. I've tried.",
            "The starter code comment said 'TODO: build this' and I felt personally attacked. Yeah okay I will build it, you don't have to call me out like that.",
            "Debugging at 2am hits different. Everything's either brilliant or completely broken and you won't know which until morning. This variable name though? Definitely a 2am decision.",

            # Borderline/Mixed (5 examples)
            "The quick brown fox jumps over the lazy dog. This sentence demonstrates various letters. It's commonly used for testing.",
            "I think the system works correctly. It processes the input and returns results. The output appears reasonable for most cases.",
            "Consider the following approach for testing. First, identify key scenarios. Second, implement test cases. Third, verify the results match expectations.",
            "The documentation states that rate limiting prevents abuse. The threshold of 10 per minute seems reasonable. This balances usability with security.",
            "When signals disagree, uncertainty increases. The combined score reflects this ambiguity. Such cases land in the middle range.",
        ],
    },
    {
        "name": "bad input handling",
        "criterion": 5,
        # Test that bad inputs return 400, not 500 crashes
        "bodies": [
            {"text": "", "creator_id": "eval_bad_empty"},  # Empty text
            {"creator_id": "eval_bad_missing"},  # No text field
            {"text": "word " * 50001, "creator_id": "eval_bad_huge"},  # >50k chars
            {"text": None, "creator_id": "eval_bad_null"},  # Null text
            {"text": "some text"},  # Missing creator_id
        ],
    },
    # Note: Criterion 4 (appeal path) tested manually via curl after getting content_ids,
    # as it requires two-step flow: submit → get content_id → appeal with that id.
    # Test script: submit 5 texts, appeal each one, verify all status changes recorded.
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
