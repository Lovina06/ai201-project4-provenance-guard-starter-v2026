# Acceptance Criteria — Unit 9 Extension

Five criteria for the monitoring dashboard extension, written before testing.

At least three must be about the extension itself (the new monitoring capabilities).
Each names a target that can be measured or plainly observed.

---

## 1. Dashboard loads and displays current statistics within 2 seconds

When I open `/dashboard` in a browser with an existing audit log, the page must load and populate all 4 stat cards (total submissions, error rate, appeal rate, total appeals) with non-zero values within 2 seconds. All numbers must match what's in the current log.

**Why this target:**

A monitoring dashboard that takes >2s to load defeats its purpose - people won't wait. The page needs to feel instant because it's meant for quick checks ("is the system working?"). If I have to wait, I'll just grep the log instead. 2 seconds allows for fetching /metrics, parsing JSON, and initializing 4 charts - anything longer means I optimized wrong.

---

## 2. Metrics endpoint returns structurally valid data for empty, small, and large logs

The `/metrics` endpoint must return valid JSON with all required fields (total_submissions, total_appeals, total_rejections, label_distribution, recent_submissions, error_rate, appeal_rate, timestamp) in three scenarios:
- Empty log (0 entries) → returns zeros/empty arrays, no crash
- Small log (1-10 entries) → returns correct counts
- Large log (100+ entries) → returns only last 100 in recent_submissions

Test across 5 scenarios total. All 5 must return HTTP 200 with valid structure.

**Why this target:**

The dashboard fails silently if /metrics returns malformed data - charts just don't update and it looks like the system is frozen. Catching this requires testing edge cases: empty logs (startup state), small logs (first few submissions), large logs (production volume). The "last 100" limit prevents the response from growing unbounded. If I can't guarantee structural validity, the dashboard is unreliable.

---

## 3. Auto-refresh updates displayed data without full page reload

After the dashboard loads, if I submit 3 new texts to `/submit`, the dashboard's "Total Submissions" count must increment by 3 within 12 seconds (one auto-refresh cycle) without me refreshing the page. No browser errors in console.

**Why this target:**

Static dashboards are useless - I'd just read the log once. The 10-second auto-refresh is the whole point of "live monitoring." 12 seconds allows one full refresh cycle plus network/processing. If this doesn't work, the dashboard is just a fancy log viewer I have to manually reload, which is worse than curl because it's slower.

---

## 4. Signal score scatter plot renders correctly with mixed data

When the log contains at least 20 submissions with varying model_score and style_score values (human: low scores, AI: high scores, mixed: medium scores), the scatter plot on the dashboard must show distinct clusters. Visually checking the chart, I should see:
- Points spread across the plot (not all at origin)
- Clear separation between human cluster (bottom-left) and AI cluster (top-right)
- At least 15 points visible (some may overlap)

Test with 25 submissions: 10 clearly human, 10 clearly AI, 5 borderline.

**Why this target:**

The scatter plot's job is to surface patterns: do our signals agree? Are we scoring things consistently? A blob of overlapping points at (0.5, 0.5) means the signals don't separate, which is a problem I need to see. If the chart can't show this pattern visually, it's decorative rather than diagnostic. 20+ submissions ensures enough data for patterns to be visible.

---

## 5. Dashboard handles service errors gracefully

When the Flask service is stopped (not running), opening `/dashboard` in a browser must either:
- Return HTTP 503 (service unavailable) or connection refused error
- OR (if dashboard is static file) load the page but show "Failed to update dashboard" in browser console after fetch fails

When service is running but `/metrics` artificially returns 500 error, dashboard must not crash or hang - console must show fetch error and stats display "—" (no data).

Test: 2 error scenarios, both must degrade gracefully (no white screen, no infinite spinner).

**Why this target:**

Monitoring tools that crash when the thing they're monitoring breaks are useless. The dashboard needs to fail gracefully: if the service is down, show that; if metrics fail, say so. A white screen or infinite loading spinner gives me no information. I need to know "the service is down" vs "metrics endpoint is broken" vs "dashboard JS crashed" - different problems require different fixes. Graceful degradation means the dashboard itself never becomes a problem I have to debug.

---