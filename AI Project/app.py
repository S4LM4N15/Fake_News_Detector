"""
app.py — Flask backend for the Fake News Detector.

Routes
------
GET  /           → serves index.html
POST /api/check  → { query } → { score, verdict, breakdown, sources }
GET  /api/health → health check
"""

import os
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from search_engine import search_duckduckgo
from scorer import calculate_score

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route("/api/check", methods=["POST"])
def check_news():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    if len(query) > 500:
        return jsonify({"error": "Query too long (max 500 chars)"}), 400

    try:
        # 1. Search
        t0 = time.time()
        results = search_duckduckgo(query, max_results=10)
        search_time = round(time.time() - t0, 2)

        # 2. Score
        scored = calculate_score(query, results)
        scored["search_time_seconds"] = search_time
        scored["query"] = query

        return jsonify(scored)

    except Exception as e:
        print(f"[app] Error processing query: {e}")
        return jsonify({"error": "Internal error while checking news. Please try again."}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
