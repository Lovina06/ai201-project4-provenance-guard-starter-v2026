# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. False positive rate: At most 2 of 10 pieces I wrote myself are labeled "high-confidence AI"

Of 10 genuine human-written pieces (varying in style from plain to complex), no more than 2 may receive the "high-confidence AI" label. Pieces labeled "unsure" do not count as false positives for this criterion.

**Why this target:**

A wrong accusation of AI use is the most damaging outcome of this system. On a writing platform, falsely flagging real work destroys trust and can have academic or professional consequences for the writer. However, 0/10 is unrealistic — some plain, predictable human writing genuinely looks machine-like by any measure. Allowing 2/10 acknowledges that ambiguity exists while keeping false accusations rare enough that the system doesn't cry wolf constantly. The "high-confidence" distinction matters: calling something "unsure" admits uncertainty; calling it "AI" is an accusation.

---

## 2. Score separation: Clearly-AI and clearly-human text score at least 0.30 apart

When I test with one piece of unedited AI-generated text and one piece of complex human writing with varied vocabulary, their combined confidence scores must differ by at least 0.30 (e.g., AI scores 0.75+, human scores 0.45 or below).

**Why this target:**

If the system can't reliably separate obvious cases, it has no business judging borderline ones. A 0.30 gap ensures the signals are actually detecting something real rather than just returning noise around 0.5 for everything. This is a sanity check on whether the signals work at all. The gap must hold in the direction expected: AI should score higher, not lower.

---

## 3. Label coverage: All three labels appear in a set of 15 diverse test submissions

When I submit 15 different pieces (5 clearly AI, 5 clearly human, 5 borderline or edited), all three labels must appear at least once: "high-confidence human," "unsure," and "high-confidence AI."

**Why this target:**

Unreachable labels indicate broken thresholds. If every submission lands in "unsure," the system is useless. If "unsure" never appears, the thresholds are too aggressive and the system is overconfident. All three labels should be reachable with reasonable inputs. Requiring diversity in the test set (clear AI, clear human, mixed/edited cases) ensures we're not just testing edge cases.

---

## 4. Appeal path: 100% of appeals with valid content_id change status to "under_review" and appear in log

Every appeal submitted with a content_id that exists in the audit log must: (1) change that entry's status to "under_review," (2) record the appeal reasoning in the log, and (3) return confirmation to the caller. No exceptions.

**Why this target:**

The appeal path is the only recourse a wrongly-accused writer has. If it silently fails, accepts appeals for nonexistent IDs without recording them, or loses the reasoning, the system has violated the one mechanism that makes false positives survivable. 100% reliability is non-negotiable here because this affects real people who were already harmed by a wrong decision. Partial credit ("works most of the time") is unacceptable.

---

## 5. Bad input handling: Empty, missing, or oversized text returns error response without crashing

The service must handle all of these without returning HTTP 500: (1) request with no `text` field, (2) `text` is empty string or only whitespace, (3) `text` exceeds 50,000 characters. Each should return 400-level error with clear message; none should crash the service or write invalid entries to the audit log.

**Why this target:**

A production system that crashes on malformed input is not production-ready. These are the most common attack vectors (fuzzing, payload testing, accident) and also the most common user errors. A 500 error exposes internal details and looks like the system broke; a 400 error with a clear message ("text is required" or "text too long") is correct behavior. The 50,000 character limit is chosen to allow long essays but reject obviously abusive payloads without burning resources on tokenization.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
