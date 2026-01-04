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
        return [{
            "code": "US",
            "name": "United States",
            "currency_code": "USD",
            "currency_symbol": "$",
        }]

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
# Auto‑economics (safe defaults)
# =====================
def fill_auto_economics_for_form(form):
    for key in (
        "annual_production_cost",
        "price_per_unit",
        "capex_per_m2",
    ):
        if not form.get(key):
            form[key] = 0

# =====================
# Core calculation
# =====================
def compute_results(form):
    try:
        area = float(form.get("area_m2") or 0)
        crop = form.get("crop")
        system_type = form.get("system_type")
        setup_level = form.get("setup_level")
        use_solar = bool(form.get("use_solar"))
        country_code = form.get("country") or "US"

        if area <= 0:
            return None, "Please enter a valid greenhouse area."

        country = find_country(country_code)
        currency_code = country["currency_code"] if country else "USD"

        annual_production_cost = float(form.get("annual_production_cost") or 0)
        price_per_kg = float(form.get("price_per_unit") or 0)
        capex_per_m2 = float(form.get("capex_per_m2") or 0)

        annual_yield = area * 30  # conservative baseline
        gross_cost = annual_production_cost
        solar_savings = gross_cost * SOLAR_SAVINGS_RATE if use_solar else 0
        net_cost = gross_cost - solar_savings
        revenue = annual_yield * price_per_kg
        profit = revenue - net_cost

        total_setup_cost = capex_per_m2 * area
        payback = (
            total_setup_cost / profit if profit > 0 else None
        )

        results = {
            "area": area,
            "crop": crop,
            "system_type": system_type,
            "setup_level": setup_level,
            "setup_label": setup_level.capitalize(),
            "country_code": country_code,
            "currency_code": currency_code,

            "plants_per_m2": 2.0,
            "crops_per_year": 1,
            "yield_per_m2_per_crop": 30,
            "plants": area * 2.0,
            "annual_yield": annual_yield,

            "nutrient_per_m2_per_crop": 0.5,
            "nutrient_per_plant_per_crop": 0.25,
            "nutrient_per_crop_total": area * 0.5,
            "annual_nutrient_total": area * 0.5,

            "gross_production_cost": gross_cost,
            "solar_savings": solar_savings,
            "net_production_cost": net_cost,

            "cost_per_kg": net_cost / annual_yield if annual_yield else None,
            "cost_per_m2_per_year": net_cost / area,
            "cost_per_plant_per_year": net_cost / (area * 2.0),

            "price_per_kg": price_per_kg,
            "annual_revenue": revenue,
            "revenue_per_m2_per_year": revenue / area,
            "revenue_per_plant_per_year": revenue / (area * 2.0),

            "capex_per_m2": capex_per_m2,
            "total_setup_cost": total_setup_cost,

            "annual_profit": profit,
            "profit_per_kg": profit / annual_yield if annual_yield else None,
            "profit_per_m2_per_year": profit / area,
            "profit_per_plant_per_year": profit / (area * 2.0),

            "simple_payback_years": payback,
            "SOLAR_SAVINGS_RATE": SOLAR_SAVINGS_RATE,
        }

        return results, None

    except Exception as e:
        return None, str(e)

# =====================
# Routes
# =====================
@app.route("/", methods=["GET", "POST"])
def index():
    form = MyForm()
    form.country.choices = [(c["code"], c["name"]) for c in COUNTRIES]

    error = None

    if form.validate_on_submit():
        form_data = form.data.copy()
        fill_auto_economics_for_form(form_data)
        results, error = compute_results(form_data)

        if results and not error:
            session["last_form"] = form_data
            session["last_results"] = results

            db = get_db()
            db.execute(
                "INSERT INTO history (area_m2, system_type, crop, country, savings) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    results["area"],
                    results["system_type"],
                    results["crop"],
                    results["country_code"],
                    results["solar_savings"],
                ),
            )
            db.commit()

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
        results=session["last_results"],
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