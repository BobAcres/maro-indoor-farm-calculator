import os
import sqlite3
import requests
from math import cos, radians
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    g,
    abort,
)

# ======================================================
# APP SETUP
# ======================================================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "farm_calc.db")

SOLAR_SAVINGS_RATE = 0.20
PLANTS_PER_M2 = 2.0
ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin123")

# ======================================================
# DATABASE
# ======================================================
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
    db = sqlite3.connect(DATABASE)
    db.execute("""
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
    db.commit()
    db.close()

# ======================================================
# COUNTRIES (SAFE, ALWAYS WORKS)
# ======================================================
COUNTRIES_CACHE = []


def fetch_countries():
    try:
        r = requests.get(
            "https://restcountries.com/v3.1/all?fields=name,cca2,currencies,latlng",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        # Hard fallback (never empty)
        return [{
            "code": "US",
            "name": "United States",
            "currency_code": "USD",
            "currency_symbol": "$",
            "lat": 38,
        }]

    countries = []
    for c in data:
        currencies = c.get("currencies", {})
        if currencies:
            code = list(currencies.keys())[0]
            symbol = currencies[code].get("symbol", code)
        else:
            code, symbol = "USD", "$"

        latlng = c.get("latlng", [0, 0])

        countries.append({
            "code": c.get("cca2"),
            "name": c.get("name", {}).get("common"),
            "currency_code": code,
            "currency_symbol": symbol,
            "lat": latlng[0] if latlng else 0,
        })

    return sorted(countries, key=lambda x: x["name"])


def get_countries():
    global COUNTRIES_CACHE
    if not COUNTRIES_CACHE:
        COUNTRIES_CACHE = fetch_countries()
    return COUNTRIES_CACHE


def find_country(code):
    return next((c for c in get_countries() if c["code"] == code), None)

# ======================================================
# CONSTANT OPTIONS (VISIBLE IN UI)
# ======================================================
SYSTEM_TYPES = [
    ("soil", "Greenhouse soil"),
    ("soilless", "Greenhouse soilless"),
    ("hydroponics", "Hydroponics"),
    ("aeroponics", "Aeroponics"),
    ("vertical", "Vertical farming"),
]

CROPS = [
    ("tomato", "Tomato"),
    ("pepper", "Pepper"),
    ("cucumber", "Cucumber"),
    ("strawberry", "Strawberry"),
    ("lettuce", "Lettuce"),
    ("spinach", "Spinach"),
    ("basil", "Basil"),
]

BASE_YIELD_KG_PER_M2 = {
    "tomato": 25,
    "pepper": 20,
    "cucumber": 30,
    "strawberry": 18,
    "lettuce": 40,
    "spinach": 35,
    "basil": 50,
}

SYSTEM_YIELD_MULTIPLIER = {
    "soil": 0.85,
    "soilless": 1.0,
    "hydroponics": 1.15,
    "aeroponics": 1.25,
    "vertical": 1.4,
}

# ======================================================
# ECONOMICS
# ======================================================
def generate_country_economics(country):
    lat = abs(country["lat"])
    solar_index = max(0.6, min(1.4, cos(radians(lat)) + 0.4))

    if lat < 30:
        labor = 0.5
        price = 0.7
        capex = 1.2
    elif lat < 50:
        labor = 1.0
        price = 1.0
        capex = 1.0
    else:
        labor = 1.3
        price = 1.3
        capex = 0.95

    return {
        "labor_index": labor,
        "energy_index": 0.9,
        "yield_index": 1.0,
        "price_index": price,
        "capex_index": capex,
        "solar_index": solar_index,
    }

# ======================================================
# CORE CALCULATION
# ======================================================
def compute_results(data):
    try:
        area = float(data.get("area_m2", 0))
        if area <= 0:
            return None, "Please enter a valid greenhouse area."

        country = find_country(data.get("country"))
        if not country:
            return None, "Please select a valid country."

        econ = generate_country_economics(country)

        crop = data.get("crop")
        system = data.get("system_type")
        use_solar = data.get("use_solar") == "on"

        plants = area * PLANTS_PER_M2

        base_yield = BASE_YIELD_KG_PER_M2.get(crop, 20)
        system_mult = SYSTEM_YIELD_MULTIPLIER.get(system, 1.0)
        annual_yield = area * base_yield * system_mult * econ["yield_index"]

        # Costs
        cost = float(data.get("annual_production_cost") or 0)
        if cost == 0:
            cost = area * 20 * econ["labor_index"]

        energy = cost * econ["energy_index"]
        gross_cost = cost + energy

        solar = (
            gross_cost * SOLAR_SAVINGS_RATE * econ["solar_index"]
            if use_solar
            else 0
        )

        net_cost = gross_cost - solar

        # Revenue
        price = float(data.get("price_per_unit") or 0)
        if price == 0:
            price = 2.5 * econ["price_index"]

        revenue = annual_yield * price
        profit = revenue - net_cost

        return {
            "country": country["name"],
            "currency_symbol": country["currency_symbol"],
            "area_m2": round(area, 2),
            "crop": crop,
            "system_type": system,
            "plants": round(plants, 0),
            "annual_yield": round(annual_yield, 2),
            "annual_profit": round(profit, 2),
            "profit_per_plant": round(profit / plants, 2) if plants else 0,
        }, None

    except Exception as e:
        return None, f"Calculation error: {str(e)}"

# ======================================================
# ROUTES
# ======================================================
@app.route("/", methods=["GET", "HEAD"])
def home():
    if request.method == "HEAD":
        return ("", 200)

    return render_template(
        "index.html",
        countries=get_countries(),
        system_types=SYSTEM_TYPES,
        crops=CROPS,
    )


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.form.to_dict()
    results, error = compute_results(data)

    if error:
        return render_template(
            "index.html",
            countries=get_countries(),
            system_types=SYSTEM_TYPES,
            crops=CROPS,
            error=error,
        )

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
            results["annual_profit"],
        ),
    )
    db.commit()

    session["results"] = results
    return redirect(url_for("results"))


@app.route("/results")
def results():
    results = session.get("results")
    if not results:
        return redirect(url_for("home"))
    return render_template("results.html", results=results)


@app.route("/admin/history")
def admin_history():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)

    rows = get_db().execute(
        "SELECT * FROM history ORDER BY created_at DESC"
    ).fetchall()

    return render_template("admin_history.html", history=rows)

# ======================================================
# INIT
# ======================================================
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)