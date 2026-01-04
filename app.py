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

        currencies = c.get("currencies", {})
    if currencies:
     currency_code = list(currencies.keys())[0]
     currency_symbol = currencies[currency_code].get("symbol", currency_code)
    else:
     currency_code = "USD"
     currency_symbol = "$"

     countries.append({
    "code": c.get("cca2"),
    "name": c.get("name", {}).get("common"),
    "currency_code": currency_code,
    "currency_symbol": currency_symbol,
    "lat": latlng[0] if latlng else 0,
})

    return sorted(countries, key=lambda c: c["name"])


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
    form.system_type.choices = [
    ("soil", "Greenhouse soil"),
    ("soilless", "Greenhouse soilless"),
    ("hydroponics", "Hydroponics"),
    ("aeroponics", "Aeroponics"),
    ("vertical", "Vertical farming"),
]
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
    """
    Core economics engine.
    Country-aware, override-safe, per-plant transparent.
    """

    try:
        # -------------------------
        # Basic inputs
        # -------------------------
        area_m2 = float(form.get("area_m2") or 0)
        if area_m2 <= 0:
            return None, "Please enter a valid greenhouse area."

        crop = form.get("crop")
        system_type = form.get("system_type")
        setup_level = form.get("setup_level")
        use_solar = bool(form.get("use_solar"))
        country_code = form.get("country")

        # -------------------------
        # Country & currency
        # -------------------------
        country = find_country(country_code)
        if not country:
            return None, "Invalid country selected."

        currency_code = country.get("currency_code", "USD")
        currency_symbol = country.get("currency_symbol", "")

        # Generate country economics (works for ALL countries)
        economics = generate_country_economics(country)

        # -------------------------
        # Plant density
        # -------------------------
        plants_per_m2 = PLANTS_PER_M2
        total_plants = area_m2 * plants_per_m2

        # -------------------------
        # Yield calculation
        # -------------------------
        base_yield_per_m2 = BASE_YIELD_KG_PER_M2.get(crop, 20)

        system_multiplier = SYSTEM_YIELD_MULTIPLIER.get(system_type, 1.0)

        annual_yield_kg = (
            area_m2
            * base_yield_per_m2
            * system_multiplier
            * economics["yield_index"]
        )

        yield_per_plant_kg = (
            annual_yield_kg / total_plants if total_plants else 0
        )

        # -------------------------
        # COSTS (user overrides win)
        # -------------------------
        # Labor / operating cost
        user_annual_cost = float(form.get("annual_production_cost") or 0)

        if user_annual_cost > 0:
            gross_production_cost = user_annual_cost
        else:
            # Default: cost per m² adjusted by country
            base_cost_per_m2 = 20  # conservative global baseline
            gross_production_cost = (
                base_cost_per_m2
                * area_m2
                * economics["labor_index"]
            )

        # Energy cost (derived)
        energy_cost = gross_production_cost * economics["energy_index"]

        gross_production_cost += energy_cost

        # Solar savings
        solar_savings = 0
        if use_solar:
            solar_savings = (
                gross_production_cost
                * SOLAR_SAVINGS_RATE
                * economics["solar_index"]
            )

        net_production_cost = gross_production_cost - solar_savings

        cost_per_plant = (
            net_production_cost / total_plants if total_plants else 0
        )

        # -------------------------
        # REVENUE (user overrides win)
        # -------------------------
        user_price = float(form.get("price_per_unit") or 0)

        if user_price > 0:
            price_per_kg = user_price
        else:
            # Default farm-gate price baseline
            base_price_per_kg = 2.5
            price_per_kg = (
                base_price_per_kg
                * economics["price_index"]
            )

        annual_revenue = annual_yield_kg * price_per_kg
        revenue_per_plant = (
            annual_revenue / total_plants if total_plants else 0
        )

        # -------------------------
        # PROFIT
        # -------------------------
        annual_profit = annual_revenue - net_production_cost
        profit_per_plant = (
            annual_profit / total_plants if total_plants else 0
        )

        # -------------------------
        # CAPEX (user overrides win)
        # -------------------------
        user_capex_per_m2 = float(form.get("capex_per_m2") or 0)

        if user_capex_per_m2 > 0:
            capex_per_m2 = user_capex_per_m2
        else:
            base_capex_per_m2 = 300
            capex_per_m2 = (
                base_capex_per_m2
                * economics["capex_index"]
            )

        total_setup_cost = capex_per_m2 * area_m2
        capex_per_plant = (
            total_setup_cost / total_plants if total_plants else 0
        )

        payback_years = (
            total_setup_cost / annual_profit
            if annual_profit > 0
            else None
        )

        # -------------------------
        # FINAL RESULTS OBJECT
        # -------------------------
        results = {
            # Context
            "country_code": country_code,
            "currency_code": currency_code,
            "currency_symbol": currency_symbol,

            # Scale
            "area_m2": round(area_m2, 2),
            "plants_per_m2": plants_per_m2,
            "plants": round(total_plants, 0),

            # Production
            "crop": crop,
            "system_type": system_type,
            "annual_yield_kg": round(annual_yield_kg, 2),
            "yield_per_plant_kg": round(yield_per_plant_kg, 3),

            # Costs
            "gross_production_cost": round(gross_production_cost, 2),
            "solar_savings": round(solar_savings, 2),
            "net_production_cost": round(net_production_cost, 2),
            "cost_per_plant": round(cost_per_plant, 2),

            # Revenue
            "price_per_kg": round(price_per_kg, 2),
            "annual_revenue": round(annual_revenue, 2),
            "revenue_per_plant": round(revenue_per_plant, 2),

            # Profit
            "annual_profit": round(annual_profit, 2),
            "profit_per_plant": round(profit_per_plant, 2),

            # CapEx
            "capex_per_m2": round(capex_per_m2, 2),
            "total_setup_cost": round(total_setup_cost, 2),
            "capex_per_plant": round(capex_per_plant, 2),

            # Payback
            "simple_payback_years": (
                round(payback_years, 2) if payback_years else None
            ),

            # Transparency
            "economics_profile": economics,
            "SOLAR_SAVINGS_RATE": SOLAR_SAVINGS_RATE,
        }

        return results, None

    except Exception as e:
        return None, f"Calculation error: {str(e)}"

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