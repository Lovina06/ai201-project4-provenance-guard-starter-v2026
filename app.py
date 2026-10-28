#!/usr/bin/env python3
"""
Provenance Guard — the web service.

    python app.py

Then, in another terminal:

    curl -X POST http://127.0.0.1:5000/ping \
      -H "Content-Type: application/json" \
      -d '{"message": "hello"}'

That's the example route. It works right now, before you've written anything.
**Leave it alone** — it's your control. When something breaks later, check that
`/ping` still answers: if it does, the problem is in your handler; if it
doesn't, it's the service itself.

Routes:

    POST /ping        the worked example. Already works. Don't edit it
    POST /submit      ← YOU BUILD THIS (Milestone 3, 4, 5)
    POST /appeal      ← YOU BUILD THIS (Milestone 5)
    GET  /log         the audit log. Already works
    GET  /health      is the service up, and is the model loaded
"""

import uuid

from flask import Flask, jsonify, request

import audit
import config

app = Flask(__name__)


# ── Rate limiting — UNIT 8 ────────────────────────────────────────────────────
# Off until you turn it on. In unit 8, Milestone 1:
#
#   1. Set RATE_LIMITING_ENABLED = True in config.py (or AI201_RATE_LIMITS=1)
#   2. Choose your numbers there
#   3. Uncomment the @limiter.limit(...) line on /submit below
#
# The order doesn't matter. While limiting is off, that decorator is a no-op
# that quietly does nothing, so uncommenting it early costs you nothing — but
# it also means no 429 until you've done step 1.
#
# The storage backend is preconfigured, which stops Flask-Limiter printing a
# warning on every start. In-memory is right for one laptop and wrong for
# anything real — a restart forgets every count.

class _LimiterOff:
    """
    Stands in for the real limiter while rate limiting is off.

    It makes @limiter.limit(...) a decorator that returns the route
    untouched, so uncommenting the line before you flip the setting is
    harmless instead of a crash on startup.
    """

    def limit(self, *args, **kwargs):
        return lambda view: view


limiter = _LimiterOff()
if config.RATE_LIMITING_ENABLED:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def rate_limit_key():
        """
        Who a request counts against.

        Falling back to the caller's address is the easy version. Unit 8's
        stretch asks about per-creator limits instead — and the difference
        matters: one script can look like a thousand callers, and one household
        can look like one.
        """
        payload = request.get_json(silent=True)
        # A body that parses as JSON but isn't an object — a bare list or
        # string — has no .get. Without this guard the key function raises
        # BEFORE the route runs, and a malformed request becomes a 500 that
        # looks like your handler crashed when your handler never ran.
        if not isinstance(payload, dict):
            return get_remote_address()
        creator = payload.get("creator_id")
        return creator if isinstance(creator, str) and creator.strip() else get_remote_address()

    limiter = Limiter(
        key_func=rate_limit_key,
        app=app,
        storage_uri=config.RATE_LIMIT_STORAGE,
        default_limits=[],
    )

    @app.errorhandler(429)
    def rate_limited(exc):
        """
        A rejected request still leaves a trace.

        ⚠️ An attack that shows up only as an absence is one you'll never find.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="rate_limited",
            limit=str(exc.description),
        )
        return jsonify({
            "error": "rate_limited",
            "message": "Too many submissions. Try again shortly.",
            "limit": str(exc.description),
        }), 429


# ── The worked example. Already works. Don't edit. ────────────────────────────

@app.post("/ping")
def ping():
    """
    Everything a route needs, in six lines.

    JSON arrives as a dict. You pull things out of it. You return a dict and
    the framework turns it into a response. That's the whole idea.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "ok": True,
        "you_sent": payload.get("message"),
        "service": "provenance-guard",
    })


@app.get("/health")
def health():
    """Is the service up, and has the model been downloaded yet?"""
    import detector

    loaded = detector._model is not None
    return jsonify({
        "ok": True,
        "detector_model": config.DETECTOR_MODEL,
        "detector_loaded": loaded,
        "rate_limiting": config.RATE_LIMITING_ENABLED,
        "log_entries": len(audit.read_entries()),
    })


# ── YOU BUILD THIS ────────────────────────────────────────────────────────────

@app.post("/submit")
@limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute;{config.RATE_LIMIT_PER_DAY}/day")
def submit():
    """
    Take a piece of text, decide about it, log the decision, answer.

    Expects JSON:
        {"text": "...", "creator_id": "..."}

    Returns JSON with:
        {"content_id": "...", "guess": "...", "confidence": 0.0, "label": "...",
         "model_score": 0.0, "style_score": 0.0}
    """
    import detector
    import stylometry
    import scoring

    payload = request.get_json(silent=True) or {}

    # Input validation (Criterion 5: bad input handling)
    text = payload.get("text")
    creator_id = payload.get("creator_id")

    if not text or not isinstance(text, str):
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="missing_or_invalid_text",
        )
        return jsonify({
            "error": "invalid_input",
            "message": "Field 'text' is required and must be a non-empty string",
        }), 400

    text = text.strip()
    if not text:
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="empty_text",
        )
        return jsonify({
            "error": "invalid_input",
            "message": "Field 'text' cannot be empty or whitespace only",
        }), 400

    if len(text) > 50000:
        audit.log_rejection(
            creator_id=payload.get("creator_id", "unknown"),
            reason="text_too_long",
            text_length=len(text),
        )
        return jsonify({
            "error": "invalid_input",
            "message": "Field 'text' exceeds maximum length of 50,000 characters",
        }), 400

    if not creator_id or not isinstance(creator_id, str) or not creator_id.strip():
        audit.log_rejection(
            creator_id="unknown",
            reason="missing_or_invalid_creator_id",
        )
        return jsonify({
            "error": "invalid_input",
            "message": "Field 'creator_id' is required and must be a non-empty string",
        }), 400

    # Generate content ID
    content_id = str(uuid.uuid4())

    # Run signal one (Milestone 3)
    model_score = detector.model_signal(text)

    # Run signal two (Milestone 4)
    style_score = stylometry.style_signal(text)

    # Combine signals (Milestone 4)
    confidence = scoring.combine_signals(model_score, style_score)

    # Get label (Milestone 5)
    guess, label = scoring.score_to_label(confidence)

    # Log the decision
    audit.log_decision(
        content_id=content_id,
        creator_id=creator_id.strip(),
        text=text[:200],  # Log first 200 chars for reference
        guess=guess,
        combined_score=confidence,
        model_score=model_score,
        style_score=style_score,
        label=label,
    )

    return jsonify({
        "content_id": content_id,
        "guess": guess,
        "confidence": confidence,
        "label": label,
        "model_score": model_score,
        "style_score": style_score,
    })


@app.post("/appeal")
def appeal():
    """
    A writer says you got it wrong.

    Expects JSON:
        {"content_id": "...", "reasoning": "..."}

    Records the appeal and changes status to "under_review".
    """
    payload = request.get_json(silent=True) or {}

    # Extract fields
    content_id = payload.get("content_id")
    reasoning = payload.get("reasoning", "")

    # Validate content_id
    if not content_id or not isinstance(content_id, str):
        return jsonify({
            "error": "invalid_input",
            "message": "Field 'content_id' is required and must be a non-empty string",
        }), 400

    # Check if content_id exists in log
    existing_entries = audit.entries_for(content_id)
    if not existing_entries:
        return jsonify({
            "error": "not_found",
            "message": f"No submission found with content_id '{content_id}'",
        }), 404

    # Find the original decision (status='decided')
    original = None
    for entry in existing_entries:
        if entry.get("status") == "decided":
            original = entry
            break

    old_status = original.get("guess") if original else "unknown"

    # Log the appeal (changes status to under_review)
    creator_id = original.get("creator_id") if original else payload.get("creator_id", "unknown")
    audit.log_appeal(
        content_id=content_id,
        creator_id=creator_id,
        reasoning=reasoning,
    )

    return jsonify({
        "ok": True,
        "content_id": content_id,
        "old_status": old_status,
        "new_status": "under_review",
        "message": "Your appeal has been recorded and the submission is now under review.",
    })


# ── Already works ─────────────────────────────────────────────────────────────

@app.get("/log")
def get_log():
    """
    The audit log, most recent last.

        curl "http://127.0.0.1:5000/log?limit=10"

    You need this in unit 8 to paste entries into your README, and you need it
    now to see whether your logging is actually working.
    """
    limit = request.args.get("limit", type=int)
    entries = audit.read_entries(limit=limit)
    return jsonify({"count": len(entries), "entries": entries})


def main():
    print(f"Provenance Guard on http://{config.HOST}:{config.PORT}")
    print(f"  detector model:  {config.DETECTOR_MODEL}")
    print(f"  rate limiting:   {'ON' if config.RATE_LIMITING_ENABLED else 'off (unit 8)'}")
    print(f"  audit log:       {config.AUDIT_LOG}")
    print()
    print("Check it's alive:")
    print(f'  curl -X POST http://{config.HOST}:{config.PORT}/ping \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"message\": \"hello\"}'")
    print()
    # debug=True hands out an interactive debugger, so it's local-only — see config.py
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
