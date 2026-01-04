import os
import sqlite3
import requests

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, g, abort
)

from forms import MyForm

# =====================
# App setup
# =====================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "farm_calc.db")
SOLAR_SAVINGS_RATE = 0.20
ADMIN_KEY = os.environ.get("ADMIN_KEY")

# =====================
# DB helpers
# =====================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_m2 REAL,
            system_type TEXT,
            crop TEXT,
            country TEXT,
            savings REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# =====================
# Country lookup
# =====================
def fetch_countries():
    try:
        r = requests.get(
            "https://restcountries.com/v3.1/all?fields=name,cca2,currencies",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return [{"code": "US", "name": "United States", "currency_code": "USD", "currency_symbol": "$"}]

    countries = []
    for c in data:
        currencies = c.get("currencies", {})
        if currencies:
            code = list(currencies.keys())[0]
            symbol = currencies[code].get("symbol", code)
        else:
            code, symbol = "USD", "$"

        countries.append({
            "code": c.get("cca2", ""),
            "name": c.get("name", {}).get("common", ""),
            "currency_code": code,
            "currency_symbol": symbol,
        })

    return sorted(countries, key=lambda x: x["name"])


COUNTRIES = fetch_countries()


def find_country(code):
    return next((c for c in COUNTRIES if c["code"] == code), None)


# =====================
# ROUTES
# =====================
def fill_auto_economics_for_form(form_dict):
    ...


def compute_results(form_data):
    """Compute calculation results based on form data."""
    try:
        # Add your calculation logic here
        results = {}
        error = None
        return results, error
    except Exception as e:
        return None, str(e)


@app.route("/", methods=["GET", "POST"])
def index():
    form = MyForm()

    # Populate country choices
    form.country.choices = [(c["code"], c["name"]) for c in COUNTRIES]

    error = None
    results = None

    if form.validate_on_submit():
        form_data = form.data.copy()

        # ✅ MUST be inside the if
        fill_auto_economics_for_form(form_data)

        results, error = compute_results(form_data)

        if results and not error:
            session["last_form"] = form_data
            session["last_results"] = results
        return redirect(url_for("results_page"))

    return render_template(
        "index.html",
        form=form,
        error=error,
        SOLAR_SAVINGS_RATE=SOLAR_SAVINGS_RATE,
    )


@app.route("/results")
def results_page():
    if "last_results" not in session:
        return redirect(url_for("index"))

    return render_template(
        "results.html",
        form=session.get("last_form"),
        results=session.get("last_results"),
    )


@app.route("/admin/history")
def admin_history():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)

    rows = get_db().execute(
        "SELECT * FROM history ORDER BY id DESC"
    ).fetchall()

    return render_template("admin_history.html", history=rows)


# =====================
# Init
# =====================
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)