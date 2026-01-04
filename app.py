import os
import sqlite3
import requests
from math import cos, radians

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

PLANTS_PER_M2 = 2.0

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
            annual_profit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# =====================
# Countries
# =====================
def fetch_countries():
    try:
        r = requests.get(
            "https://restcountries.com/v3.1/all?fields=name,cca2,currencies,latlng",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    countries = []
    for c in data:
        latlng = c.get("latlng", [0, 0])
        currencies = c.get("currencies", {})
        code = list(currencies.keys())[0] if currencies else "USD"

        countries.append({
            "code": c.get("cca2"),
            "name": c.get("name", {}).get("common"),
            "currency_code": code,
            "lat": latlng[0] if latlng else 0,
        })

    return countries


COUNTRIES = fetch_countries()


def find_country(code):
    return next((c for c in COUNTRIES if c["code"] == code), None)

# =====================
# GLOBAL COUNTRY ECONOMICS (auto‑generated)
# =====================
def generate_country_economics(country):
    """
    Produces reasonable defaults for ANY country.
    """
    lat = abs(country.get("lat", 0))

    # Solar potential (higher near equator)
    solar_index = max(0.6, min(1.4, cos(radians(lat)) + 0.4))

    # Income proxy
    if lat < 30:
        labor_index = 0.5
        price_index = 0.7
        capex_index = 1.2
    elif lat < 50:
        labor_index = 1.0
        price_index = 1.0
        capex_index = 1.0
    else:
        labor_index = 1.3
        price_index = 1.3
        capex_index = 0.95

    return {
        "labor_index": labor_index,
        "energy_index": 0.9,
        "yield_index": 1.0,
        "price_index": price_index,
        "capex_index": capex_index,
        "solar_index": solar_index,
    }

# =====================
# Crop & system baselines
# =====================
BASE_YIELD_KG_PER_M2 = {
    "tomato": 25,
    "pepper": 20,
    "cucumber": 30,
    "strawberry": 18,
    "lettuce": 40,
    "spinach": 35,
    "basil": 50,
    "cannabis": 12,
}

SYSTEM_YIELD_MULTIPLIER = {
    "soil": 0.85,
    "soilless": 1.00,
    "hydroponics": 1.15,
    "aeroponics": 1.25,
    "vertical": 1.40,
}

# =====================
# Dropdowns
# =====================
def populate_dropdowns(form):
    form.country.choices = [(c["code"], c["name"]) for c in COUNTRIES]
    form.setup_level.choices = [("local", "Local"), ("standard", "Standard"), ("hightech", "Hi‑tech")]
    form.system_type.choices = list(SYSTEM_YIELD_MULTIPLIER.items())
    form.crop.choices = [(k, k.capitalize()) for k in BASE_YIELD_KG_PER_M2]

# =====================
# Helpers
# =====================
def normalize_form_data(form):
    for k in ("annual_production_cost", "price_per_unit", "capex_per_m2", "area_m2"):
        if not form.get(k):
            form[k] = 0
    return form

# =====================
# CORE CALCULATION (override‑safe)
# =====================
def compute_results(form):
    try:
        area = float(form.get("area_m2"))
        if area <= 0:
            return None, "Invalid area"

        country = find_country(form.get("country"))
        econ = generate_country_economics(country) if country else {}

        plants = area * PLANTS_PER_M2

        # Yield
        base_yield = BASE_YIELD_KG_PER_M2.get(form.get("crop"), 20)
        system_mult = SYSTEM_YIELD_MULTIPLIER.get(form.get("system_type"), 1.0)
        annual_yield = area * base_yield * system_mult * econ.get("yield_index", 1)

        # Costs (USER OVERRIDES respected)
        labor_cost = float(form.get("annual_production_cost"))
        if labor_cost == 0:
            labor_cost = area * 20 * econ.get("labor_index", 1)

        energy_cost = labor_cost * econ.get("energy_index", 1)
        gross_cost = labor_cost + energy_cost

        solar_savings = gross_cost * SOLAR_SAVINGS_RATE * econ.get("solar_index", 1) if form.get("use_solar") else 0
        net_cost = gross_cost - solar_savings

        # Revenue
        price = float(form.get("price_per_unit"))
        if price == 0:
            price = 2.5 * econ.get("price_index", 1)

        revenue = annual_yield * price
        profit = revenue - net_cost

        # CapEx
        capex = float(form.get("capex_per_m2"))
        if capex == 0:
            capex = 300 * econ.get("capex_index", 1)

        total_capex = capex * area

        return {
            "plants": plants,
            "annual_yield": round(annual_yield, 2),
            "yield_per_plant": round(annual_yield / plants, 3),

            "gross_cost": round(gross_cost, 2),
            "net_cost": round(net_cost, 2),
            "cost_per_plant": round(net_cost / plants, 2),

            "revenue": round(revenue, 2),
            "revenue_per_plant": round(revenue / plants, 2),

            "profit": round(profit, 2),
            "profit_per_plant": round(profit / plants, 2),

            "total_capex": round(total_capex, 2),
            "capex_per_plant": round(total_capex / plants, 2),

            "currency": country["currency_code"] if country else "USD",
        }, None

    except Exception as e:
        return None, str(e)

# =====================
# Routes
# =====================
@app.route("/", methods=["GET", "HEAD"])
def home():
    if request.method == "HEAD":
        return ("", 200)

    form = MyForm()
    populate_dropdowns(form)
    return render_template("index.html", form=form)


@app.route("/calculate", methods=["POST"])
def calculate():
    form = MyForm()
    populate_dropdowns(form)

    data = normalize_form_data(request.form.to_dict())
    results, error = compute_results(data)

    if results:
        # ✅ SAVE TO HISTORY HERE
        db = get_db()
        db.execute(
            """
            INSERT INTO history (area_m2, system_type, crop, country, annual_profit)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                float(data.get("area_m2", 0)),
                data.get("system_type"),
                data.get("crop"),
                data.get("country"),
                results.get("annual_profit"),
            ),
        )
        db.commit()

        session["last_results"] = results
        return redirect(url_for("results_page"))

    return render_template(
        "index.html",
        form=form,
        error=error,
    )


@app.route("/results")
def results_page():
    return render_template("results.html", results=session.get("last_results"))


# =====================
# Init
# =====================
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)