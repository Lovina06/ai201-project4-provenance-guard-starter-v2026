# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

A piece of text moves through the system in seven stages:

1. **Route entry** — POST /submit receives JSON with `text` and `creator_id`, validates input
2. **Signal one (model)** — `detector.py` runs perplexity calculation on text, returns 0-1 score (higher = more AI-likely)
3. **Signal two (style)** — `stylometry.py` measures text shape (sentence variation, vocabulary diversity, punctuation), returns 0-1 score
4. **Score combination** — `scoring.py::combine_signals` combines both signals using weighted average with disagreement handling
5. **Label mapping** — `scoring.py::score_to_label` converts score to one of three human-readable labels
6. **Audit logging** — `audit.py` writes complete entry to `logs/audit.jsonl` with all scores and decision
7. **Response** — JSON returned with `content_id`, `guess`, `confidence`, `label`, `model_score`, and `style_score`



---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:**

Text predictability using perplexity. A language model (gpt2) tries to predict each word — low perplexity (easy to predict) produces a high AI-likelihood score.

**Why that might differ between human and AI writing:**

AI models write by repeatedly choosing likely next words, producing predictable sequences. Human writing makes unexpected choices — odd words, abrupt shifts, specific details over generic ones.

**What it can't see:**

**Predictability is not authorship.** This signal actually rewards *common words in short, ordinary sentences* — which many real humans use. Someone writing in a second language (sticking to vocabulary they're sure of), younger writers, or anyone writing plainly on purpose all score as "machine-like" not because they used AI, but because their natural style is predictable. Dense, ornate prose with rare words often scores as human because rare words are exactly what models fail to predict. **The writers most likely to be falsely accused are the ones with least room to argue back.**

### Signal two — the style signal

**What it measures:**

The shape of text without understanding meaning:
- **Sentence length variation** (coefficient of variation: stdev/mean of word counts)
- **Vocabulary diversity** (type-token ratio: unique words / total words)
- **Punctuation patterns** (density of "interesting" punctuation: commas, semicolons, colons, dashes)

**Why that might differ between human and AI writing:**

Generated text tends toward even, mid-length sentences and narrower vocabulary bands because "most likely next word" produces average patterns. Human writing is lumpier — a three-word sentence next to a forty-word one, vocabulary that repeats less mechanically, more varied punctuation use.

**What it can't see:**

**This signal cannot read.** It has no idea what the text says. Anything that changes shape without changing substance moves the score: adding typos, breaking up or combining sentences, pasting quoted text, inserting random punctuation. This is trivially cheap to do on purpose, and an attacker can manipulate this signal without changing what their AI-generated text actually says.

### The combining rule

**The rule:**

Weighted average favoring the model signal (0.6 model, 0.4 style), with disagreement handling. When the two signals strongly disagree (difference > 0.4), the combined score pulls toward 0.5 (unsure) to acknowledge uncertainty. This favors false negatives (letting AI through) over false positives (accusing humans).

**The numbers:**

- Model signal weight: **0.6** (more robust, harder to manipulate)
- Style signal weight: **0.4** (useful but easily fooled)
- Disagreement threshold: **0.4** difference triggers uncertainty adjustment
- Human threshold: **≤ 0.35** → "high-confidence human"
- Unsure band: **0.35 – 0.65** → "unsure"
- AI threshold: **≥ 0.65** → "high-confidence AI"

**Where it lives:** `scoring.py::combine_signals`

**A case where my two signals split, and what my rule does with it:**

**Test text:** "The quick brown fox jumps over the lazy dog. This is a simple sentence."

- Model score: 0.22 (human-like — simple, predictable)
- Style score: 0.66 (AI-like — low vocabulary diversity, simple structure)
- **Disagreement:** 0.44 (strongly disagree!)
- **Combined:** 0.40 (pulled toward 0.5 from base weighted average of 0.40)
- **Result:** "unsure" — which is exactly right. Two signals disagreeing IS uncertainty.



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.35 | This text appears to have been written by a person. |
| unsure | 0.35 – 0.65 | We're uncertain about this text. It has some patterns that could go either way. This isn't an accusation — just means our system can't make a confident call here. |
| high-confidence AI | 0.65 – 1.00 | This text shows patterns commonly found in AI-generated writing. If you wrote this yourself, you can appeal this decision. |

**Why I worded the "unsure" one this way:**

This label is the hardest because it has to admit uncertainty without sounding like an accusation. The person reading it may well have written every word themselves — the score landed in the middle because their writing style happens to be ambiguous to the system, not because they did anything wrong. The phrase "This isn't an accusation" is explicit because someone who got flagged unfairly will be defensive, and they need to hear directly that we're not accusing them. "Could go either way" is honest: the system genuinely doesn't know, and pretending otherwise would be worse.



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "The quick brown fox jumps over the lazy dog. This is a simple sentence written by me.", "creator_id": "test_user_1"}'
```

```json
{
  "confidence": 0.3959346265072606,
  "content_id": "10f4dfd0-b67e-42fd-aa5a-d0a329bbdfe9",
  "guess": "unsure",
  "label": "We're uncertain about this text. It has some patterns that could go either way. This isn't an accusation — just means our system can't make a confident call here.",
  "model_score": 0.2172,
  "style_score": 0.6585448321103314
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "10f4dfd0-b67e-42fd-aa5a-d0a329bbdfe9", "reasoning": "I wrote this text myself. It is simple because English is my second language."}'
```

```json
{
  "content_id": "10f4dfd0-b67e-42fd-aa5a-d0a329bbdfe9",
  "message": "Your appeal has been recorded and the submission is now under review.",
  "new_status": "under_review",
  "ok": true,
  "old_status": "unsure"
}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json
{
  "count": 3,
  "entries": [
    {
      "combined_score": 0.3959346265072606,
      "content_id": "10f4dfd0-b67e-42fd-aa5a-d0a329bbdfe9",
      "creator_id": "test_user_1",
      "guess": "unsure",
      "label": "We're uncertain about this text. It has some patterns that could go either way. This isn't an accusation — just means our system can't make a confident call here.",
      "model_score": 0.2172,
      "status": "decided",
      "style_score": 0.6585448321103314,
      "text": "The quick brown fox jumps over the lazy dog. This is a simple sentence written by me.",
      "timestamp": "2026-10-28T11:32:21+00:00"
    },
    {
      "combined_score": 0.6879253398912926,
      "content_id": "fa8d40ad-1553-440c-852f-3b9350fedaf5",
      "creator_id": "test_user_2",
      "guess": "ai",
      "label": "This text shows patterns commonly found in AI-generated writing. If you wrote this yourself, you can appeal this decision.",
      "model_score": 0.7558,
      "status": "decided",
      "style_score": 0.5861133497282313,
      "text": "The implementation of machine learning algorithms requires careful consideration of various factors. These include data preprocessing, model selection, and hyperparameter tuning. By following best pra",
      "timestamp": "2026-10-28T11:33:02+00:00"
    },
    {
      "content_id": "10f4dfd0-b67e-42fd-aa5a-d0a329bbdfe9",
      "creator_id": "test_user_1",
      "event": "appeal",
      "reasoning": "I wrote this text myself. It is simple because English is my second language.",
      "status": "under_review",
      "timestamp": "2026-10-28T11:34:39+00:00"
    }
  ]
}
```

---

## How I Used AI

**Moment 1: Designing the combining rule**

- *What I asked for:* Asked Claude to help me think through how to handle disagreement between the two signals. Specifically: "When model signal says 0.9 (AI-like) but style signal says 0.2 (human-like), what should the combined score be?"
- *What came back:* Claude suggested three approaches: (1) weighted average (simple but ignores disagreement), (2) take the minimum (conservative, favors human), (3) pull toward 0.5 when disagreement is large (acknowledges uncertainty). Provided code for option 3.
- *What I changed:* Kept the weighted average as the base (0.6 model, 0.4 style) but added the disagreement adjustment. Changed the disagreement threshold from Claude's suggestion of 0.3 to 0.4 — I wanted to trigger uncertainty only on *strong* disagreement, not moderate splits. Also adjusted the uncertainty blending factor from 0.5 to 0.3 so it doesn't pull too hard toward middle.

**Moment 2: Writing the "unsure" label text**

- *What I asked for:* "Write label text for 'unsure' that admits uncertainty without sounding like an accusation. The reader may have written this themselves."
- *What came back:* "This submission shows mixed signals. Our system cannot determine with confidence whether this was written by a person or generated by AI."
- *What I changed:* The phrase "mixed signals" felt too technical. Changed to "patterns that could go either way" (more concrete). Added explicit disclaimer "This isn't an accusation" because Claude's version was too neutral — someone who got flagged unfairly needs to hear directly that we're not accusing them. The final version is more conversational and explicitly reassuring.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 10 per minute, 200 per day

**Why those numbers and not others:**

A legitimate writer might submit a draft, revise it, and resubmit a couple times per hour (maybe 5-10 submissions/hour peak). 10/minute allows bursts but blocks scripts that hammer the endpoint. 200/day = ~8 submissions/hour sustained over 24 hours, which is generous for real use but hostile to threshold-mapping attacks that need hundreds of variations. A script sending 1000 test inputs hits the daily limit in 5 minutes and gets cut off.

**What a caller counts as:**

Per `creator_id`. The rate_limit_key() function in app.py checks the `creator_id` field first, falling back to IP address only when creator_id is missing or invalid. This means:
- One person submitting from different devices (same creator_id) shares one limit
- Different people behind one NAT/proxy (same IP, different creator_ids) each get their own limit
- One script spoofing thousands of creator_ids looks like thousands of callers and avoids the limit (acknowledged trade-off)

This favors real users over IP-based blocking, at the cost of being bypassable by attackers who randomize creator_id. Alternative would be IP-based (harder to bypass, but household/campus shares one limit).

**The run of status codes when I pushed past it:**

```
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
