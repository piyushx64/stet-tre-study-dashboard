import os, json, sqlite3, hmac
from pathlib import Path
from flask import Flask, request, session, redirect, url_for, jsonify, render_template_string, send_from_directory

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE / "study_dashboard.sqlite3"))
app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY") or "local-development-only-change-me"
PASSWORD = os.environ.get("DASHBOARD_PASSWORD") or "change-this-password"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS dashboard_state (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL)")
    conn.commit()
    return conn

LOGIN = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Study Dashboard Login</title><style>body{font:16px system-ui;background:#101827;color:#edf2ff;display:grid;place-items:center;min-height:100vh;margin:0}.card{background:#1b2639;padding:28px;border:1px solid #34425c;border-radius:18px;width:min(380px,calc(100% - 40px))}input,button{font:inherit;width:100%;padding:12px;border-radius:10px;box-sizing:border-box;margin-top:10px}input{border:1px solid #52617a;background:#101827;color:white}button{background:#8b5cf6;color:white;border:0;font-weight:700;cursor:pointer}.error{color:#fca5a5}</style><div class="card"><h1>STET + TRE</h1><p>Private study dashboard</p>{% if error %}<p class="error">{{error}}</p>{% endif %}<form method="post"><label for="password">Dashboard password</label><input id="password" name="password" type="password" required autofocus><button>Sign in</button></form></div></html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), PASSWORD):
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("home"))
        error = "Incorrect password. Try again."
    return render_template_string(LOGIN, error=error)

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/")
def home():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return send_from_directory(BASE, "index.html")

@app.route("/api/state", methods=["GET", "PUT"])
def state_api():
    if not session.get("authenticated"):
        return jsonify({"error": "Authentication required"}), 401
    conn = db()
    if request.method == "GET":
        row = conn.execute("SELECT payload FROM dashboard_state WHERE id=1").fetchone()
        conn.close()
        return jsonify(json.loads(row[0]) if row else {})
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        conn.close()
        return jsonify({"error": "Expected JSON object"}), 400
    conn.execute("INSERT INTO dashboard_state(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (json.dumps(payload),))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
