import sqlite3
import datetime
import requests
from flask import (
    Flask, render_template, request, g,
    redirect, url_for, session
)

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY"  # required for session

DATABASE = "farm_calc.db"
SOLAR_SAVINGS_RATE = 0.20  # 20%

# =========================
#  CROP YIELD + NUTRIENTS
# =========================

CROP_PARAMS = {
    "GLOBAL": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 30, "nutrients_kg_m2_crop": 0.6},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 25, "nutrients_kg_m2_crop": 0.55},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 1,  "yield_per_m2_per_crop": 32, "nutrients_kg_m2_crop": 0.55},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 20, "nutrients_kg_m2_crop": 0.40},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 4,  "yield_per_m2_per_crop": 2.5,"nutrients_kg_m2_crop": 0.15},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 4,  "yield_per_m2_per_crop": 2.3,"nutrients_kg_m2_crop": 0.15},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 5,  "nutrients_kg_m2_crop": 0.45},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 3,  "yield_per_m2_per_crop": 1.6,"nutrients_kg_m2_crop": 0.18},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 4,  "yield_per_m2_per_crop": 1.2,"nutrients_kg_m2_crop": 0.12},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 4,  "yield_per_m2_per_crop": 1.8,"nutrients_kg_m2_crop": 0.16},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 2,  "yield_per_m2_per_crop": 0.7,"nutrients_kg_m2_crop": 0.35},
        },
        "soilless": {
            "tomato":         {"plants_per_m2": 2.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 55, "nutrients_kg_m2_crop": 0.9},
            "pepper":         {"plants_per_m2": 3.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 45, "nutrients_kg_m2_crop": 0.85},
            "cucumber":       {"plants_per_m2": 2.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 65, "nutrients_kg_m2_crop": 0.85},
            "strawberry":     {"plants_per_m2": 8.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 35, "nutrients_kg_m2_crop": 0.55},
            "lettuce":        {"plants_per_m2": 20,  "crops_per_year": 7,  "yield_per_m2_per_crop": 3.0,"nutrients_kg_m2_crop": 0.20},
            "spinach":        {"plants_per_m2": 20,  "crops_per_year": 6,  "yield_per_m2_per_crop": 2.8,"nutrients_kg_m2_crop": 0.20},
            "potato":         {"plants_per_m2": 4.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 6.0,"nutrients_kg_m2_crop": 0.55},
            "fluted_pumpkin": {"plants_per_m2": 4.0, "crops_per_year": 4,  "yield_per_m2_per_crop": 2.0,"nutrients_kg_m2_crop": 0.22},
            "basil":          {"plants_per_m2": 25,  "crops_per_year": 6,  "yield_per_m2_per_crop": 1.5,"nutrients_kg_m2_crop": 0.16},
            "water_leaf":     {"plants_per_m2": 16,  "crops_per_year": 6,  "yield_per_m2_per_crop": 2.0,"nutrients_kg_m2_crop": 0.20},
            "cannabis":       {"plants_per_m2": 6.0, "crops_per_year": 3,  "yield_per_m2_per_crop": 1.0,"nutrients_kg_m2_crop": 0.40},
        },
        "vertical": {
            "tomato":         {"plants_per_m2": 4.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 75, "nutrients_kg_m2_crop": 1.4},
            "pepper":         {"plants_per_m2": 5.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 60, "nutrients_kg_m2_crop": 1.2},
            "cucumber":       {"plants_per_m2": 3.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 85, "nutrients_kg_m2_crop": 1.3},
            "strawberry":     {"plants_per_m2": 16,  "crops_per_year": 1,  "yield_per_m2_per_crop": 50, "nutrients_kg_m2_crop": 0.9},
            "lettuce":        {"plants_per_m2": 60,  "crops_per_year": 9,  "yield_per_m2_per_crop": 3.0,"nutrients_kg_m2_crop": 0.35},
            "spinach":        {"plants_per_m2": 60,  "crops_per_year": 8,  "yield_per_m2_per_crop": 2.8,"nutrients_kg_m2_crop": 0.35},
            "potato":         {"plants_per_m2": 6.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 7.0,"nutrients_kg_m2_crop": 0.65},
            "fluted_pumpkin": {"plants_per_m2": 8.0, "crops_per_year": 5,  "yield_per_m2_per_crop": 2.2,"nutrients_kg_m2_crop": 0.30},
            "basil":          {"plants_per_m2": 70,  "crops_per_year": 7,  "yield_per_m2_per_crop": 1.6,"nutrients_kg_m2_crop": 0.24},
            "water_leaf":     {"plants_per_m2": 40,  "crops_per_year": 7,  "yield_per_m2_per_crop": 2.2,"nutrients_kg_m2_crop": 0.30},
            "cannabis":       {"plants_per_m2": 12,  "crops_per_year": 4,  "yield_per_m2_per_crop": 1.4,"nutrients_kg_m2_crop": 0.55},
        },
        "hydroponics": {
            "tomato":         {"plants_per_m2": 2.7, "crops_per_year": 1,  "yield_per_m2_per_crop": 60, "nutrients_kg_m2_crop": 1.0},
            "pepper":         {"plants_per_m2": 3.2, "crops_per_year": 1,  "yield_per_m2_per_crop": 50, "nutrients_kg_m2_crop": 0.95},
            "cucumber":       {"plants_per_m2": 2.2, "crops_per_year": 1,  "yield_per_m2_per_crop": 70, "nutrients_kg_m2_crop": 0.95},
            "strawberry":     {"plants_per_m2": 9.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 40, "nutrients_kg_m2_crop": 0.65},
            "lettuce":        {"plants_per_m2": 24,  "crops_per_year": 8,  "yield_per_m2_per_crop": 3.2,"nutrients_kg_m2_crop": 0.22},
            "spinach":        {"plants_per_m2": 24,  "crops_per_year": 7,  "yield_per_m2_per_crop": 3.0,"nutrients_kg_m2_crop": 0.22},
            "potato":         {"plants_per_m2": 4.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 6.5,"nutrients_kg_m2_crop": 0.60},
            "fluted_pumpkin": {"plants_per_m2": 4.5, "crops_per_year": 4,  "yield_per_m2_per_crop": 2.1,"nutrients_kg_m2_crop": 0.24},
            "basil":          {"plants_per_m2": 28,  "crops_per_year": 6,  "yield_per_m2_per_crop": 1.6,"nutrients_kg_m2_crop": 0.18},
            "water_leaf":     {"plants_per_m2": 18,  "crops_per_year": 6,  "yield_per_m2_per_crop": 2.1,"nutrients_kg_m2_crop": 0.22},
            "cannabis":       {"plants_per_m2": 7.0, "crops_per_year": 3,  "yield_per_m2_per_crop": 1.1,"nutrients_kg_m2_crop": 0.45},
        },
        "aeroponics": {
            "tomato":         {"plants_per_m2": 2.8, "crops_per_year": 1,  "yield_per_m2_per_crop": 65, "nutrients_kg_m2_crop": 1.1},
            "pepper":         {"plants_per_m2": 3.3, "crops_per_year": 1,  "yield_per_m2_per_crop": 52, "nutrients_kg_m2_crop": 1.0},
            "cucumber":       {"plants_per_m2": 2.3, "crops_per_year": 1,  "yield_per_m2_per_crop": 72, "nutrients_kg_m2_crop": 1.0},
            "strawberry":     {"plants_per_m2": 9.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 42, "nutrients_kg_m2_crop": 0.70},
            "lettuce":        {"plants_per_m2": 26,  "crops_per_year": 9,  "yield_per_m2_per_crop": 3.3,"nutrients_kg_m2_crop": 0.24},
            "spinach":        {"plants_per_m2": 26,  "crops_per_year": 8,  "yield_per_m2_per_crop": 3.1,"nutrients_kg_m2_crop": 0.24},
            "potato":         {"plants_per_m2": 4.8, "crops_per_year": 1,  "yield_per_m2_per_crop": 6.8,"nutrients_kg_m2_crop": 0.62},
            "fluted_pumpkin": {"plants_per_m2": 4.8, "crops_per_year": 4,  "yield_per_m2_per_crop": 2.2,"nutrients_kg_m2_crop": 0.26},
            "basil":          {"plants_per_m2": 30,  "crops_per_year": 6,  "yield_per_m2_per_crop": 1.7,"nutrients_kg_m2_crop": 0.19},
            "water_leaf":     {"plants_per_m2": 20,  "crops_per_year": 6,  "yield_per_m2_per_crop": 2.2,"nutrients_kg_m2_crop": 0.24},
            "cannabis":       {"plants_per_m2": 7.5, "crops_per_year": 3,  "yield_per_m2_per_crop": 1.2,"nutrients_kg_m2_crop": 0.48},
        },
    },
    "NG": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 2,  "yield_per_m2_per_crop": 25, "nutrients_kg_m2_crop": 0.55},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 2,  "yield_per_m2_per_crop": 22, "nutrients_kg_m2_crop": 0.50},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 2,  "yield_per_m2_per_crop": 28, "nutrients_kg_m2_crop": 0.50},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 18, "nutrients_kg_m2_crop": 0.38},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 6,  "yield_per_m2_per_crop": 2.4,"nutrients_kg_m2_crop": 0.16},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 6,  "yield_per_m2_per_crop": 2.3,"nutrients_kg_m2_crop": 0.16},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 4.5,"nutrients_kg_m2_crop": 0.40},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 4,  "yield_per_m2_per_crop": 1.8,"nutrients_kg_m2_crop": 0.20},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 5,  "yield_per_m2_per_crop": 1.1,"nutrients_kg_m2_crop": 0.13},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 5,  "yield_per_m2_per_crop": 1.9,"nutrients_kg_m2_crop": 0.18},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 2,  "yield_per_m2_per_crop": 0.6,"nutrients_kg_m2_crop": 0.33},
        }
    },
    "US": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 32, "nutrients_kg_m2_crop": 0.60},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 27, "nutrients_kg_m2_crop": 0.56},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 1,  "yield_per_m2_per_crop": 34, "nutrients_kg_m2_crop": 0.58},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1,  "yield_per_m2_per_crop": 22, "nutrients_kg_m2_crop": 0.42},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 4,  "yield_per_m2_per_crop": 2.6,"nutrients_kg_m2_crop": 0.16},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 4,  "yield_per_m2_per_crop": 2.4,"nutrients_kg_m2_crop": 0.16},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1,  "yield_per_m2_per_crop": 5.2,"nutrients_kg_m2_crop": 0.47},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 3,  "yield_per_m2_per_crop": 1.6,"nutrients_kg_m2_crop": 0.18},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 4,  "yield_per_m2_per_crop": 1.3,"nutrients_kg_m2_crop": 0.13},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 4,  "yield_per_m2_per_crop": 1.8,"nutrients_kg_m2_crop": 0.17},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 3,  "yield_per_m2_per_crop": 0.8,"nutrients_kg_m2_crop": 0.40},
        }
    },
}


def get_crop_params(country_code, system_type, crop):
    country_table = CROP_PARAMS.get(country_code) or CROP_PARAMS["GLOBAL"]
    system_table = country_table.get(system_type)
    if not system_table or crop not in system_table:
        system_table = CROP_PARAMS["GLOBAL"].get(system_type, {})
    params = system_table.get(crop)
    if not params:
        params = CROP_PARAMS["GLOBAL"]["soilless"]["tomato"]
    return params


# =====================
#  ECONOMIC PARAMETERS
# =====================

SETUP_LEVEL_LABELS = {
    "local":    "Local (low-tech, locally sourced materials)",
    "standard": "Standard (commercial greenhouse technology)",
    "hightech": "Hi-tech (fully automated indoor/CEA)",
}

PRODUCTION_COST_PER_M2_USD = {
    "soil":        6.0,
    "soilless":   10.0,
    "vertical":   30.0,
    "hydroponics":18.0,
    "aeroponics": 22.0,
}

PRICE_PER_KG_USD = {
    "GLOBAL": {
        "tomato":         2.0,
        "pepper":         2.5,
        "cucumber":       2.0,
        "strawberry":     5.0,
        "lettuce":        3.0,
        "spinach":        3.0,
        "potato":         1.0,
        "fluted_pumpkin": 2.0,
        "basil":         12.0,
        "water_leaf":     2.5,
        "cannabis":    1500.0,
    },
    "US": {
        "tomato":         2.5,
        "pepper":         3.0,
        "cucumber":       2.3,
        "strawberry":     6.0,
        "lettuce":        3.5,
        "spinach":        3.5,
        "potato":         1.2,
        "fluted_pumpkin": 2.2,
        "basil":         14.0,
        "water_leaf":     2.7,
        "cannabis":    1800.0,
    },
    "CA": {
        "tomato":         2.7,
        "pepper":         3.1,
        "cucumber":       2.4,
        "strawberry":     6.5,
        "lettuce":        3.7,
        "spinach":        3.7,
        "potato":         1.3,
        "fluted_pumpkin": 2.3,
        "basil":         15.0,
        "water_leaf":     2.8,
        "cannabis":    1700.0,
    },
    "NG": {
        "tomato":         1.4,
        "pepper":         1.8,
        "cucumber":       1.3,
        "strawberry":     3.5,
        "lettuce":        2.0,
        "spinach":        2.0,
        "potato":         0.7,
        "fluted_pumpkin": 1.4,
        "basil":          6.0,
        "water_leaf":     1.5,
        "cannabis":     900.0,
    },
}

CAPEX_PER_M2_USD = {
    "GLOBAL": {
        "local":    80.0,
        "standard": 150.0,
        "hightech": 400.0,
    },
    "US": {
        "local":    120.0,
        "standard": 250.0,
        "hightech": 750.0,
    },
    "CA": {
        "local":    130.0,
        "standard": 270.0,
        "hightech": 780.0,
    },
    "NG": {
        "local":    50.0,
        "standard": 110.0,
        "hightech": 250.0,
    },
}

# FX rates: how many USD is 1 unit of currency
FX_TO_USD = {
    "USD": 1.0,
    "EUR": 1.10,
    "CAD": 0.75,
    "NGN": 0.0008,
    "TRY": 0.032,
    "ANG": 0.56,
    "GBP": 1.25,
}


def usd_to_currency(amount_usd, currency_code):
    rate = FX_TO_USD.get(currency_code, 1.0)
    if rate == 0:
        return amount_usd
    return amount_usd / rate


def estimate_price_per_kg_usd(crop, country_code):
    table = PRICE_PER_KG_USD.get(country_code, PRICE_PER_KG_USD["GLOBAL"])
    return table.get(crop, PRICE_PER_KG_USD["GLOBAL"].get(crop, 2.0))


def estimate_capex_per_m2_usd(setup_level, country_code):
    table = CAPEX_PER_M2_USD.get(country_code, CAPEX_PER_M2_USD["GLOBAL"])
    return table.get(setup_level, table.get("standard", 150.0))


def current_price_unit_for_crop(crop):
    if crop in {
        "cannabis", "lettuce", "spinach", "basil", "water_leaf", "fluted_pumpkin"
    }:
        return "kg"


# ================
#  DB helper funcs
# ================
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            country_code TEXT,
            currency_code TEXT,
            crop TEXT,
            system_type TEXT,
            area_m2 REAL,
            annual_yield REAL,
            annual_revenue REAL,
            annual_profit REAL
        )
        """
    )
    conn.commit()

def normalize_checkboxes(form_data, keys):
    for k in keys:
        form_data[k] = k in form_data

# ==========================
#  Country / currency lookup
# ==========================
def fetch_countries():
    try:
        url = "https://restcountries.com/v3.1/all?fields=name,currencies,cca2"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return [
            {
                "code": "US",
                "name": "United States",
                "currency_code": "USD",
                "currency_symbol": "$",
            }
        ]

    countries = []
    for c in data:
        name = c.get("name", {}).get("common", "Unknown")
        cca2 = c.get("cca2", "")
        currencies = c.get("currencies", {})
        if currencies:
            code = list(currencies.keys())[0]
            symbol = currencies[code].get("symbol", code)
        else:
            code, symbol = "USD", "$"
        countries.append(
            {
                "code": cca2,
                "name": name,
                "currency_code": code,
                "currency_symbol": symbol,
            }
        )

    countries.sort(key=lambda x: x["name"])
    return countries


COUNTRIES = fetch_countries()


def find_country(cca2):
    for c in COUNTRIES:
        if c["code"] == cca2:
            return c
    return None


# =========================
#  Auto economics defaults
# =========================
def fill_auto_economics_for_form(form_dict):
    """
    Fill in default annual_production_cost, price_per_unit, capex_per_m2
    if user left them blank/0. Textboxes may be hidden; values are used
    only for calculations.
    """
    try:
        area = float(form_dict.get("area_m2", 0) or 0)
    except ValueError:
        area = 0

    crop = form_dict.get("crop", "tomato")
    system_type = form_dict.get("system_type", "soilless")
    setup_level = form_dict.get("setup_level", "standard")
    country_code = form_dict.get("country") or "US"

    # Determine display currency
    country = find_country(country_code)
    base_curr = country["currency_code"] if country else "USD"
    override = (form_dict.get("currency_override") or "").strip().upper()
    display_curr = override or base_curr

    # Production cost
    raw_cost = (form_dict.get("annual_production_cost") or "").strip()
    try:
        cost_val = float(raw_cost) if raw_cost else 0
    except ValueError:
        cost_val = 0

    if area > 0 and cost_val <= 0:
        per_m2_usd = PRODUCTION_COST_PER_M2_USD.get(system_type, PRODUCTION_COST_PER_M2_USD["soilless"])
        total_usd = per_m2_usd * area
        form_dict["annual_production_cost"] = f"{usd_to_currency(total_usd, display_curr):.2f}"

    # Price per unit
    raw_price = (form_dict.get("price_per_unit") or "").strip()
    try:
        price_val = float(raw_price) if raw_price else 0
    except ValueError:
        price_val = 0

    if price_val <= 0:
        price_unit = current_price_unit_for_crop(crop)
        price_usd_per_kg = estimate_price_per_kg_usd(crop, country_code)
        price_local_per_kg = usd_to_currency(price_usd_per_kg, display_curr)
        if price_unit == "g":
            est_unit = price_local_per_kg / 1000.0
        else:
            est_unit = price_local_per_kg
        form_dict["price_per_unit"] = f"{est_unit:.3f}"

    # CAPEX per m²
    raw_capex = (form_dict.get("capex_per_m2") or "").strip()
    try:
        capex_val = float(raw_capex) if raw_capex else 0
    except ValueError:
        capex_val = 0

    if capex_val <= 0:
        capex_usd = estimate_capex_per_m2_usd(setup_level, country_code)
        form_dict["capex_per_m2"] = f"{usd_to_currency(capex_usd, display_curr):.0f}"


# =====================
#  Core calculation
# =====================
def compute_results(form):
    # -------------------
    # Basic inputs
    # -------------------
    try:
        area = float(form.get("area_m2", 0) or 0)
    except ValueError:
        area = 0

    if area <= 0:
        return None, "Please fill in the greenhouse area."

    crop = form.get("crop", "tomato")
    system_type = form.get("system_type", "soilless")
    setup_level = form.get("setup_level", "standard")
    use_solar = form.get("use_solar") is True
    country_code = form.get("country", "US")
    currency_override = (form.get("currency_override") or "").strip().upper()

    country = find_country(country_code)
    base_currency_code = country["currency_code"] if country else "USD"
    base_currency_symbol = country["currency_symbol"] if country else "$"

    currency_code = currency_override or base_currency_code
    currency_symbol = currency_override or base_currency_symbol

    fx_rate = FX_TO_USD.get(currency_code, 1.0)

    # -------------------
    # Crop parameters
    # -------------------
    p = get_crop_params(country_code, system_type, crop)

    plants_per_m2 = p["plants_per_m2"]
    crops_per_year = p["crops_per_year"]
    yield_per_m2_per_crop = p["yield_per_m2_per_crop"]
    nutrient_per_m2_per_crop = p["nutrients_kg_m2_crop"]

    plants = area * plants_per_m2
    annual_yield = area * yield_per_m2_per_crop * crops_per_year

    nutrient_per_crop_total = nutrient_per_m2_per_crop * area
    annual_nutrient_total = nutrient_per_crop_total * crops_per_year
    nutrient_per_plant_per_crop = (
        nutrient_per_m2_per_crop / plants_per_m2 if plants_per_m2 > 0 else 0
    )

    # -------------------
    # PRICE (INPUT IS LOCAL → CONVERT TO USD)
    # -------------------
    try:
        price_per_kg_local = float(form.get("price_per_unit") or 0)
    except ValueError:
        price_per_kg_local = 0

    price_per_kg_usd = price_per_kg_local * fx_rate

    # -------------------
    # PRODUCTION COST (LOCAL → USD)
    # -------------------
    try:
        gross_cost_local = float(form.get("annual_production_cost") or 0)
    except ValueError:
        gross_cost_local = 0

    gross_cost_usd = gross_cost_local * fx_rate
    solar_savings_usd = gross_cost_usd * SOLAR_SAVINGS_RATE if use_solar else 0
    net_cost_usd = gross_cost_usd - solar_savings_usd

    # -------------------
    # CAPEX (LOCAL → USD)
    # -------------------
    try:
        capex_per_m2_local = float(form.get("capex_per_m2") or 0)
    except ValueError:
        capex_per_m2_local = 0

    capex_per_m2_usd = capex_per_m2_local * fx_rate
    total_setup_cost_usd = capex_per_m2_usd * area

    # -------------------
    # CORE ECONOMICS (USD)
    # -------------------
    annual_revenue_usd = annual_yield * price_per_kg_usd
    annual_profit_usd = annual_revenue_usd - net_cost_usd

    cost_per_kg_usd = net_cost_usd / annual_yield if annual_yield > 0 else None
    profit_per_kg_usd = annual_profit_usd / annual_yield if annual_yield > 0 else None

    simple_payback_years = (
        total_setup_cost_usd / annual_profit_usd
        if annual_profit_usd > 0
        else None
    )

    # -------------------
    # CONVERT BACK TO DISPLAY CURRENCY
    # -------------------
    annual_revenue = usd_to_currency(annual_revenue_usd, currency_code)
    annual_profit = usd_to_currency(annual_profit_usd, currency_code)
    net_production_cost = usd_to_currency(net_cost_usd, currency_code)
    solar_savings = usd_to_currency(solar_savings_usd, currency_code)

    cost_per_kg = (
        usd_to_currency(cost_per_kg_usd, currency_code)
        if cost_per_kg_usd is not None
        else None
    )

    profit_per_kg = (
        usd_to_currency(profit_per_kg_usd, currency_code)
        if profit_per_kg_usd is not None
        else None
    )

    total_setup_cost = usd_to_currency(total_setup_cost_usd, currency_code)

    setup_label = SETUP_LEVEL_LABELS.get(setup_level, setup_level)

    # -------------------
    # FINAL RESULTS DICT
    # -------------------
    results = {
        "currency_code": currency_code,
        "currency_symbol": currency_symbol,
        "country_code": country_code,

        "area": area,
        "crop": crop,
        "system_type": system_type,
        "setup_level": setup_level,
        "setup_label": setup_label,
        "use_solar": use_solar,

        "plants_per_m2": plants_per_m2,
        "crops_per_year": crops_per_year,
        "yield_per_m2_per_crop": yield_per_m2_per_crop,
        "plants": plants,
        "annual_yield": annual_yield,

        "nutrient_per_m2_per_crop": nutrient_per_m2_per_crop,
        "nutrient_per_crop_total": nutrient_per_crop_total,
        "annual_nutrient_total": annual_nutrient_total,
        "nutrient_per_plant_per_crop": nutrient_per_plant_per_crop,

        "gross_production_cost": usd_to_currency(gross_cost_usd, currency_code),
        "solar_savings": solar_savings,
        "net_production_cost": net_production_cost,

        "price_per_kg": usd_to_currency(price_per_kg_usd, currency_code),

        "annual_revenue": annual_revenue,
        "annual_profit": annual_profit,

        "cost_per_kg": cost_per_kg,
        "profit_per_kg": profit_per_kg,

        "cost_per_m2_per_year": net_production_cost / area if area > 0 else 0,
        "profit_per_m2_per_year": annual_profit / area if area > 0 else 0,

        "cost_per_plant_per_year": net_production_cost / plants if plants > 0 else 0,
        "profit_per_plant_per_year": annual_profit / plants if plants > 0 else 0,

        "revenue_per_m2_per_year": annual_revenue / area if area > 0 else 0,
        "revenue_per_plant_per_year": annual_revenue / plants if plants > 0 else 0,

        "capex_per_m2": usd_to_currency(capex_per_m2_usd, currency_code),
        "total_setup_cost": total_setup_cost,
        "simple_payback_years": simple_payback_years,

        "SOLAR_SAVINGS_RATE": SOLAR_SAVINGS_RATE,
    }

    return results, None

# =============
#  Routes
# =============
@app.route("/", methods=["GET", "POST"])
def index():
    init_db()

    default_country = COUNTRIES[0]["code"] if COUNTRIES else "US"

    form_defaults = {
        "area_m2": "2000",
        "system_type": "soil",
        "crop": "tomato",
        "annual_production_cost": "",
        "use_solar": False,
        "price_per_unit": "",
        "setup_level": "standard",
        "capex_per_m2": "",
        "country": default_country,
        "currency_override": "",
        # NEW: checkbox states for optional fields
        "use_custom_production_cost": False,
        "use_custom_price": False,
        "use_custom_capex": False,
    }

    error = None
    if request.method == "POST":
     form_data = {**form_defaults, **request.form.to_dict()}

     normalize_checkboxes(
        form_data,
        [
            "use_custom_production_cost",
            "use_custom_price",
            "use_custom_capex",
            "use_solar",
        ],
    )

     if not form_data["use_custom_production_cost"]:
        form_data["annual_production_cost"] = ""

     if not form_data["use_custom_price"]:
        form_data["price_per_unit"] = ""

     if not form_data["use_custom_capex"]:
        form_data["capex_per_m2"] = ""

     fill_auto_economics_for_form(form_data)
     results, error = compute_results(form_data)

     if results and not error:
        session["last_form"] = form_data
        session["last_results"] = results

        conn = get_db()
        conn.execute(
            """
            INSERT INTO calculations (
                created_at,
                country_code,
                currency_code,
                crop,
                system_type,
                area_m2,
                annual_yield,
                annual_revenue,
                annual_profit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.datetime.utcnow().isoformat(),
                results["country_code"],
                results["currency_code"],
                results["crop"],
                results["system_type"],
                results["area"],
                results["annual_yield"],
                results["annual_revenue"],
                results["annual_profit"],
            ),
        )
        conn.commit()
        return redirect(url_for("results_page"))

         # ✅ THIS LINE MUST BE HERE
     form_defaults.update(form_data)

    else:
     fill_auto_economics_for_form(form_defaults)

    return render_template(
    "index.html",
    countries=COUNTRIES,
    form=form_defaults,
    error=error,
)

@app.route("/results")
def results_page():
    init_db()
    results = session.get("last_results")
    form = session.get("last_form")

    if not results or not form:
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.execute(
        """
        SELECT id, created_at, country_code, currency_code, crop,
               system_type, area_m2, annual_yield, annual_profit
        FROM calculations
        ORDER BY id DESC
        LIMIT 10
        """
    )
    history = cur.fetchall()

    return render_template(
        "results.html",
        results=results,
        form=form,
        history=history,
    )

@app.route("/admin/history")
def admin_history_page():
    init_db()

    conn = get_db()
    cur = conn.execute(
        """
        SELECT id,
               created_at,
               country_code,
               currency_code,
               crop,
               system_type,
               area_m2,
               annual_yield,
               annual_revenue,
               annual_profit
        FROM calculations
        ORDER BY id DESC
        LIMIT 50
        """
    )
    history = cur.fetchall()

    return render_template(
        "admin_history.html",
        history=history,
    )


if __name__ == "__main__":
    app.run(debug=False)