# Milestone 1: System Trace

## 1. The Path of a Submission

A piece of text moves through the system in seven steps:

1. **Route entry** — POST /submit receives JSON with `text` and `creator_id`
2. **Signal one (model)** — detector.py runs perplexity calculation, returns 0-1 score (higher = more AI-likely)
3. **Signal two (style)** — stylometry.py measures text shape (sentence spread, vocabulary, punctuation), returns 0-1 score
4. **Score combination** — scoring.py combines both signals into single confidence score (0-1)
5. **Label mapping** — scoring.py converts score to one of three labels with human-readable text
6. **Audit logging** — audit.py writes entry to logs/audit.jsonl with all scores and decision
7. **Response** — JSON returned with content_id, guess, confidence, label, and both signal scores

## 2. Signal One: The Model Signal

**What it measures:**
Text predictability using perplexity. A language model tries to predict each word — if the text is easy to predict, perplexity is low (and the signal returns high score indicating AI-likely).

**Why this might differ between human and AI:**
AI models write by repeatedly choosing likely next words, producing predictable sequences. Human writing makes unexpected choices — odd words, abrupt shifts, specific details over generic ones.

**What it can't see (blind spot):**
**Predictability is not authorship.** The signal actually rewards *common words in short, ordinary sentences* — which many real humans use:
- Someone writing in a second language, sticking to vocabulary they're certain of
- Younger writers with simpler sentence structures
- Anyone intentionally writing plainly (accessibility, clarity, plain-language policies)

These writers score as "machine-like" not because they used AI, but because their natural style is predictable. Dense, ornate prose with rare words often scores as human because rare words are exactly what models fail to predict.

**The writers most likely to be falsely accused are the ones with least room to argue back.**

## 3. Signal Two: The Style Signal

**What it measures:**
The shape of text without understanding meaning:
- Sentence length variation (do sentences vary or march in lockstep?)
- Vocabulary diversity (type-token ratio: unique/total words)
- Punctuation patterns (density and variety)

**Why this might differ between human and AI:**
Generated text tends toward even, mid-length sentences and narrower vocabulary bands, because "most likely next word" produces average patterns. Human writing is lumpier — a three-word sentence next to a forty-word one, vocabulary that repeats less mechanically.

**What it can't see (blind spot):**
**This signal cannot read.** It has no idea what the text says. Anything that changes shape without changing substance moves the score:
- Adding typos ("writting" instead of "writing")
- Breaking up or combining sentences
- Pasting in quoted text
- Inserting random punctuation

This is trivially cheap to do on purpose, and an attacker can manipulate this signal without changing what their AI-generated text actually says.

## 4. The False Positive Trace

**Scenario:** A college student submits homework they wrote themselves. They're writing in their second language (English), using vocabulary they're confident about to avoid mistakes.

**What happens:**

1. **Route entry:** Text arrives — simple sentences, common vocabulary, careful grammar
2. **Model signal:** Returns 0.75 — text is highly predictable (common words, plain structure)
3. **Style signal:** Returns 0.60 — moderate scores (sentences vary somewhat, but vocabulary repeats)
4. **Combined score:** 0.68 (weighted average favoring model signal)
5. **Label:** Falls into "unsure" band (0.35-0.65) or possibly "high-confidence AI" if threshold is 0.65
6. **Audit log:** Records all scores, marks as "ai" or "unsure"
7. **Response:** Student sees "We detected patterns commonly associated with AI-generated text" or "This submission is uncertain"

**What the student can do:**
- Appeal via POST /appeal with reasoning explaining their writing process
- Status changes to "under_review" in audit log
- But the original accusation remains visible
- They cannot "prove" they wrote it — the burden is on them to argue

**Why this matters:**
Students writing carefully in a second language are *trying* to write correctly and clearly. The system punishes them for exactly the care they're taking. This is the trade-off at the heart of the project.

## 5. Endpoint Shapes

### POST /submit

**Expects:**
```json
{
  "text": string (required, non-empty),
  "creator_id": string (required, non-empty)
}
```

**Returns:**
```json
{
  "content_id": string (UUID),
  "guess": "human" | "ai" | "unsure",
  "confidence": float (0.0-1.0),
  "label": string (full human-readable sentence),
  "model_score": float (0.0-1.0, signal one result),
  "style_score": float (0.0-1.0, signal two result)
}
```

**Edge cases to handle:**
- Missing text → error response
- Empty text → error response  
- Extremely long text (>10,000 words) → truncate or reject
- Missing creator_id → error response

### POST /appeal

**Expects:**
```json
{
  "content_id": string (required, must exist in log),
  "reasoning": string (required, writer's explanation)
}
```

**Returns:**
```json
{
  "ok": true,
  "content_id": string (echoed back),
  "old_status": "flagged" | "human" | "unsure",
  "new_status": "under_review",
  "message": string (confirmation text)
}
```

**Edge cases:**
- content_id doesn't exist → error response
- content_id already under review → accept anyway, log new reasoning
- Missing reasoning → accept with empty reasoning (writer doesn't owe us an explanation)

---

## Key Decision: Threshold Placement

The false positive scenario depends entirely on where we put the thresholds:

- **Lower AI threshold (0.50)** → More false positives, catches more AI text
- **Higher AI threshold (0.75)** → Fewer false positives, more AI text passes through
- **Wider "unsure" band** → Safer but less useful ("we don't know" helps nobody)

This is the choice Milestone 2's criteria will force us to make explicitly.
