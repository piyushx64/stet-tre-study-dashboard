import os, json, sqlite3, hmac
from pathlib import Path
from flask import Flask, request, session, redirect, url_for, jsonify, render_template_string, send_from_directory
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BASE / "study_dashboard.sqlite3"))
app = Flask(__name__, static_folder=None)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY") or "local-development-only-change-me"
PASSWORD = os.environ.get("DASHBOARD_PASSWORD") or "change-this-password"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
ALLOWED_GOOGLE_EMAIL = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().lower()
oauth = OAuth(app)
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(name="google", client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET, server_metadata_url="https://accounts.google.com/.well-known/openid-configuration", client_kwargs={"scope": "openid email profile"})

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS dashboard_state (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL)")
    conn.commit()
    return conn

LOGIN = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Study Dashboard Login</title><style>body{font:16px system-ui;background:#101827;color:#edf2ff;display:grid;place-items:center;min-height:100vh;margin:0}.card{background:#1b2639;padding:28px;border:1px solid #34425c;border-radius:18px;width:min(380px,calc(100% - 40px))}input,button{font:inherit;width:100%;padding:12px;border-radius:10px;box-sizing:border-box;margin-top:10px}input{border:1px solid #52617a;background:#101827;color:white}button{background:#8b5cf6;color:white;border:0;font-weight:700;cursor:pointer}.error{color:#fca5a5}</style><div class="card"><h1>STET + TRE</h1><p>Private study dashboard</p>{% if google_enabled %}<p><a href="{{ url_for(&quot;google_login&quot;) }}" style="display:block;text-align:center;padding:12px;border:1px solid #d4dce9;border-radius:10px;background:white;color:#14213d;text-decoration:none;font-weight:700">Continue with Google</a></p>{% else %}<p style="color:#b42318;font-size:13px">Google sign-in needs setup in Render Environment.</p>{% endif %}<p style="text-align:center;color:#8290a6">OR sign in with password</p>{% if error %}<p class="error">{{error}}</p>{% endif %}<form method="post"><label for="password">Dashboard password</label><input id="password" name="password" type="password" required autofocus><button>Sign in</button></form></div></html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), PASSWORD):
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("home"))
        error = "Incorrect password. Try again."
    return render_template_string(LOGIN, error=error, google_enabled=bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET))

@app.get("/auth/google")
def google_login():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return redirect(url_for("login"))
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI") or url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.get("/auth/google/callback")
def google_callback():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return redirect(url_for("login"))
    try:
        token = oauth.google.authorize_access_token()
        user = token.get("userinfo") or oauth.google.userinfo()
    except Exception:
        return render_template_string(LOGIN, error="Google sign-in failed. Try again or use your password.", google_enabled=True), 400
    email = str(user.get("email", "")).strip().lower()
    verified = user.get("email_verified") is True or user.get("email_verified") == "true"
    if not verified:
        return render_template_string(LOGIN, error="Google did not verify this email address.", google_enabled=True), 403
    if not ALLOWED_GOOGLE_EMAIL or email != ALLOWED_GOOGLE_EMAIL:
        return render_template_string(LOGIN, error="This Google account is not authorised for this private dashboard.", google_enabled=True), 403
    session.clear()
    session["authenticated"] = True
    session["login_method"] = "google"
    session["user_email"] = email
    return redirect(url_for("home"))

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
