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

LOGIN = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b1220"><title>Sign in · STET + TRE Study Dashboard</title>
<style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#121d30;--line:#293851;--text:#f4f7ff;--muted:#a7b5cc;--blue:#5278ff;--purple:#8b5cf6}
*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:28px 18px;display:grid;place-items:center;background:radial-gradient(ellipse at 15% 10%,#1d3670 0,transparent 38%),radial-gradient(ellipse at 90% 90%,#39245e 0,transparent 34%),var(--bg);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--text)}
.shell{width:min(100%,440px)}.brand{display:flex;align-items:center;gap:12px;margin:0 0 22px}.logo{width:46px;height:46px;display:grid;place-items:center;border-radius:15px;background:linear-gradient(135deg,#3d69ff,#8b5cf6);font-weight:900;font-size:20px;box-shadow:0 8px 24px #345dff40}.brand-name{font-weight:800;font-size:17px;letter-spacing:-.3px}.brand-sub{color:var(--muted);font-size:12px}.card{padding:30px;background:linear-gradient(160deg,#17243a,#111a2a);border:1px solid #31425e;border-radius:24px;box-shadow:0 24px 70px #0005}.eyebrow{display:inline-flex;align-items:center;gap:7px;color:#b9c9ff;background:#26365b;border:1px solid #3b4e7b;border-radius:99px;padding:5px 10px;font-size:11px;font-weight:800;letter-spacing:.7px;text-transform:uppercase}.eyebrow:before{content:"";width:6px;height:6px;background:#8ea7ff;border-radius:50%}h1{font-size:29px;line-height:1.15;letter-spacing:-.8px;margin:16px 0 9px}.intro{margin:0;color:var(--muted);font-size:14px}.error{margin:18px 0 0;padding:11px 13px;border-radius:12px;border:1px solid #8f3b54;background:#4b2032;color:#ffdce5;font-size:13px;overflow-wrap:anywhere}.google{display:flex;align-items:center;justify-content:center;gap:11px;margin-top:24px;padding:13px 16px;background:#fff;color:#172033;text-decoration:none;border-radius:12px;font-weight:750;border:1px solid #e3e8f0;transition:transform .15s,box-shadow .15s}.google:hover{transform:translateY(-1px);box-shadow:0 8px 20px #0003}.google svg{width:19px;height:19px}.divider{display:flex;align-items:center;gap:12px;margin:22px 0;color:#8fa0bb;font-size:12px}.divider:before,.divider:after{content:"";height:1px;flex:1;background:#2d3b52}.field-label{display:block;font-weight:650;font-size:13px;margin:0 0 8px}input{width:100%;padding:13px 14px;background:#0c1524;color:white;border:1px solid #3a4a64;border-radius:12px;outline:none;font:inherit;transition:border-color .15s,box-shadow .15s}input:focus{border-color:#7892ff;box-shadow:0 0 0 3px #5278ff28}button{width:100%;margin-top:13px;padding:13px;border:0;border-radius:12px;background:linear-gradient(100deg,#4269f5,#8058ee);color:white;font:inherit;font-weight:800;cursor:pointer;box-shadow:0 8px 20px #4b60db2b}button:hover{filter:brightness(1.08)}.hint{color:#8fa0bb;font-size:11px;text-align:center;margin:17px 0 0}.footer{display:flex;justify-content:center;align-items:center;gap:7px;color:#8fa0bb;font-size:12px;margin-top:18px}.footer svg{width:15px;height:15px;color:#8ca8ff}.setup{margin-top:13px;color:#f7cf8a;font-size:12px;background:#3c3021;border:1px solid #685033;border-radius:10px;padding:10px 12px}@media(max-width:420px){.card{padding:24px 20px}h1{font-size:26px}}
</style></head><body><main class="shell">
<div class="brand"><div class="logo">S+</div><div><div class="brand-name">STET + TRE Study Dashboard</div><div class="brand-sub">Your study plan, progress and next milestone</div></div></div>
<section class="card"><span class="eyebrow">Private study space</span><h1>Welcome back.</h1><p class="intro">Sign in to continue your STET preparation and keep your study progress in one place.</p>
{% if error %}<div class="error" role="alert">{{ error }}</div>{% endif %}
{% if google_enabled %}<a class="google" href="{{ url_for('google_login') }}"><svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.72 7.18l7.62 5.91c4.45-4.1 7.14-10.14 7.14-17.56z"/><path fill="#34A853" d="M24 48c6.47 0 11.9-2.13 15.86-5.8l-7.62-5.91c-2.12 1.42-4.84 2.26-8.24 2.26-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.2C6.51 42.62 14.62 48 24 48z"/><path fill="#FBBC05" d="M10.53 28.59a14.4 14.4 0 0 1 0-9.18l-7.98-6.2a23.9 23.9 0 0 0 0 21.58l7.98-6.2z"/><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/></svg>Continue with Google</a>
{% else %}<div class="setup">Google sign-in is not configured yet. You can use your dashboard password below.</div>{% endif %}
<div class="divider">OR CONTINUE WITH PASSWORD</div><form method="post"><label class="field-label" for="password">Dashboard password</label><input id="password" name="password" type="password" placeholder="Enter your password" autocomplete="current-password" required><button type="submit">Sign in securely</button></form>
<p class="hint">Use the private dashboard password set by the owner.</p></section>
<div class="footer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>Private access · Your study journey, in one place</div>
</main></body></html>"""

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
    # Public Google sign-in: allow any Google account with a verified email.
    # Only use this for a dashboard intended to be accessible to everyone.
    if not email:
        return render_template_string(LOGIN, error="Google did not provide an email address. Try again or use your password.", google_enabled=True), 403
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
