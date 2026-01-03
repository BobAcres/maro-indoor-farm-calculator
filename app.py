import sqlite3
import datetime
import requests
import os

from flask import (
    Flask, render_template, request, g,
    redirect, url_for, session, abort
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "farm_calc.db")
SOLAR_SAVINGS_RATE = 0.20  # 20%
ADMIN_KEY = os.environ.get("ADMIN_KEY")

# =========================
#  CROP YIELD + NUTRIENTS
# =========================

CROP_PARAMS = {
    "GLOBAL": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 1, "yield_per_m2_per_crop": 30, "nutrients_kg_m2_crop": 0.6},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 1, "yield_per_m2_per_crop": 25, "nutrients_kg_m2_crop": 0.55},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 1, "yield_per_m2_per_crop": 32, "nutrients_kg_m2_crop": 0.55},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1, "yield_per_m2_per_crop": 20, "nutrients_kg_m2_crop": 0.40},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 4, "yield_per_m2_per_crop": 2.5, "nutrients_kg_m2_crop": 0.15},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 4, "yield_per_m2_per_crop": 2.3, "nutrients_kg_m2_crop": 0.15},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1, "yield_per_m2_per_crop": 5.0, "nutrients_kg_m2_crop": 0.45},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 3, "yield_per_m2_per_crop": 1.6, "nutrients_kg_m2_crop": 0.18},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.2, "nutrients_kg_m2_crop": 0.12},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.8, "nutrients_kg_m2_crop": 0.16},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 2, "yield_per_m2_per_crop": 0.7, "nutrients_kg_m2_crop": 0.35},
        },
        "soilless": {
            "tomato":         {"plants_per_m2": 2.5, "crops_per_year": 1, "yield_per_m2_per_crop": 55, "nutrients_kg_m2_crop": 0.9},
            "pepper":         {"plants_per_m2": 3.0, "crops_per_year": 1, "yield_per_m2_per_crop": 45, "nutrients_kg_m2_crop": 0.85},
            "cucumber":       {"plants_per_m2": 2.0, "crops_per_year": 1, "yield_per_m2_per_crop": 65, "nutrients_kg_m2_crop": 0.85},
            "strawberry":     {"plants_per_m2": 8.0, "crops_per_year": 1, "yield_per_m2_per_crop": 35, "nutrients_kg_m2_crop": 0.55},
            "lettuce":        {"plants_per_m2": 20,  "crops_per_year": 7, "yield_per_m2_per_crop": 3.0, "nutrients_kg_m2_crop": 0.20},
            "spinach":        {"plants_per_m2": 20,  "crops_per_year": 6, "yield_per_m2_per_crop": 2.8, "nutrients_kg_m2_crop": 0.20},
            "potato":         {"plants_per_m2": 4.0, "crops_per_year": 1, "yield_per_m2_per_crop": 6.0, "nutrients_kg_m2_crop": 0.55},
            "fluted_pumpkin": {"plants_per_m2": 4.0, "crops_per_year": 4, "yield_per_m2_per_crop": 2.0, "nutrients_kg_m2_crop": 0.22},
            "basil":          {"plants_per_m2": 25,  "crops_per_year": 6, "yield_per_m2_per_crop": 1.5, "nutrients_kg_m2_crop": 0.16},
            "water_leaf":     {"plants_per_m2": 16,  "crops_per_year": 6, "yield_per_m2_per_crop": 2.0, "nutrients_kg_m2_crop": 0.20},
            "cannabis":       {"plants_per_m2": 6.0, "crops_per_year": 3, "yield_per_m2_per_crop": 1.0, "nutrients_kg_m2_crop": 0.40},
        },
        "vertical": {
            "tomato":         {"plants_per_m2": 4.5, "crops_per_year": 1, "yield_per_m2_per_crop": 75, "nutrients_kg_m2_crop": 1.4},
            "pepper":         {"plants_per_m2": 5.0, "crops_per_year": 1, "yield_per_m2_per_crop": 60, "nutrients_kg_m2_crop": 1.2},
            "cucumber":       {"plants_per_m2": 3.0, "crops_per_year": 1, "yield_per_m2_per_crop": 85, "nutrients_kg_m2_crop": 1.3},
            "strawberry":     {"plants_per_m2": 16,  "crops_per_year": 1, "yield_per_m2_per_crop": 50, "nutrients_kg_m2_crop": 0.9},
            "lettuce":        {"plants_per_m2": 60,  "crops_per_year": 9, "yield_per_m2_per_crop": 3.0, "nutrients_kg_m2_crop": 0.35},
            "spinach":        {"plants_per_m2": 60,  "crops_per_year": 8, "yield_per_m2_per_crop": 2.8, "nutrients_kg_m2_crop": 0.35},
            "potato":         {"plants_per_m2": 6.0, "crops_per_year": 1, "yield_per_m2_per_crop": 7.0, "nutrients_kg_m2_crop": 0.65},
            "fluted_pumpkin": {"plants_per_m2": 8.0, "crops_per_year": 5, "yield_per_m2_per_crop": 2.2, "nutrients_kg_m2_crop": 0.30},
            "basil":          {"plants_per_m2": 70,  "crops_per_year": 7, "yield_per_m2_per_crop": 1.6, "nutrients_kg_m2_crop": 0.24},
            "water_leaf":     {"plants_per_m2": 40,  "crops_per_year": 7, "yield_per_m2_per_crop": 2.2, "nutrients_kg_m2_crop": 0.30},
            "cannabis":       {"plants_per_m2": 12,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.4, "nutrients_kg_m2_crop": 0.55},
        },
        "hydroponics": {
            "tomato":         {"plants_per_m2": 2.7, "crops_per_year": 1, "yield_per_m2_per_crop": 60, "nutrients_kg_m2_crop": 1.0},
            "pepper":         {"plants_per_m2": 3.2, "crops_per_year": 1, "yield_per_m2_per_crop": 50, "nutrients_kg_m2_crop": 0.95},
            "cucumber":       {"plants_per_m2": 2.2, "crops_per_year": 1, "yield_per_m2_per_crop": 70, "nutrients_kg_m2_crop": 0.95},
            "strawberry":     {"plants_per_m2": 9.0, "crops_per_year": 1, "yield_per_m2_per_crop": 40, "nutrients_kg_m2_crop": 0.65},
            "lettuce":        {"plants_per_m2": 24,  "crops_per_year": 8, "yield_per_m2_per_crop": 3.2, "nutrients_kg_m2_crop": 0.22},
            "spinach":        {"plants_per_m2": 24,  "crops_per_year": 7, "yield_per_m2_per_crop": 3.0, "nutrients_kg_m2_crop": 0.22},
            "potato":         {"plants_per_m2": 4.5, "crops_per_year": 1, "yield_per_m2_per_crop": 6.5, "nutrients_kg_m2_crop": 0.60},
            "fluted_pumpkin": {"plants_per_m2": 4.5, "crops_per_year": 4, "yield_per_m2_per_crop": 2.1, "nutrients_kg_m2_crop": 0.24},
            "basil":          {"plants_per_m2": 28,  "crops_per_year": 6, "yield_per_m2_per_crop": 1.6, "nutrients_kg_m2_crop": 0.18},
            "water_leaf":     {"plants_per_m2": 18,  "crops_per_year": 6, "yield_per_m2_per_crop": 2.1, "nutrients_kg_m2_crop": 0.22},
            "cannabis":       {"plants_per_m2": 7.0, "crops_per_year": 3, "yield_per_m2_per_crop": 1.1, "nutrients_kg_m2_crop": 0.45},
        },
        "aeroponics": {
            "tomato":         {"plants_per_m2": 2.8, "crops_per_year": 1, "yield_per_m2_per_crop": 65, "nutrients_kg_m2_crop": 1.1},
            "pepper":         {"plants_per_m2": 3.3, "crops_per_year": 1, "yield_per_m2_per_crop": 52, "nutrients_kg_m2_crop": 1.0},
            "cucumber":       {"plants_per_m2": 2.3, "crops_per_year": 1, "yield_per_m2_per_crop": 72, "nutrients_kg_m2_crop": 1.0},
            "strawberry":     {"plants_per_m2": 9.5, "crops_per_year": 1, "yield_per_m2_per_crop": 42, "nutrients_kg_m2_crop": 0.70},
            "lettuce":        {"plants_per_m2": 26,  "crops_per_year": 9, "yield_per_m2_per_crop": 3.3, "nutrients_kg_m2_crop": 0.24},
            "spinach":        {"plants_per_m2": 26,  "crops_per_year": 8, "yield_per_m2_per_crop": 3.1, "nutrients_kg_m2_crop": 0.24},
            "potato":         {"plants_per_m2": 4.8, "crops_per_year": 1, "yield_per_m2_per_crop": 6.8, "nutrients_kg_m2_crop": 0.62},
            "fluted_pumpkin": {"plants_per_m2": 4.8, "crops_per_year": 4, "yield_per_m2_per_crop": 2.2, "nutrients_kg_m2_crop": 0.26},
            "basil":          {"plants_per_m2": 30,  "crops_per_year": 6, "yield_per_m2_per_crop": 1.7, "nutrients_kg_m2_crop": 0.19},
            "water_leaf":     {"plants_per_m2": 20,  "crops_per_year": 6, "yield_per_m2_per_crop": 2.2, "nutrients_kg_m2_crop": 0.24},
            "cannabis":       {"plants_per_m2": 7.5, "crops_per_year": 3, "yield_per_m2_per_crop": 1.2, "nutrients_kg_m2_crop": 0.48},
        },
    },
    "NG": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 2, "yield_per_m2_per_crop": 25, "nutrients_kg_m2_crop": 0.55},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 2, "yield_per_m2_per_crop": 22, "nutrients_kg_m2_crop": 0.50},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 2, "yield_per_m2_per_crop": 28, "nutrients_kg_m2_crop": 0.50},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1, "yield_per_m2_per_crop": 18, "nutrients_kg_m2_crop": 0.38},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 6, "yield_per_m2_per_crop": 2.4, "nutrients_kg_m2_crop": 0.16},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 6, "yield_per_m2_per_crop": 2.3, "nutrients_kg_m2_crop": 0.16},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1, "yield_per_m2_per_crop": 4.5, "nutrients_kg_m2_crop": 0.40},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 4, "yield_per_m2_per_crop": 1.8, "nutrients_kg_m2_crop": 0.20},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 5, "yield_per_m2_per_crop": 1.1, "nutrients_kg_m2_crop": 0.13},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 5, "yield_per_m2_per_crop": 1.9, "nutrients_kg_m2_crop": 0.18},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 2, "yield_per_m2_per_crop": 0.6, "nutrients_kg_m2_crop": 0.33},
        }
    },
    "US": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 1, "yield_per_m2_per_crop": 32, "nutrients_kg_m2_crop": 0.60},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 1, "yield_per_m2_per_crop": 27, "nutrients_kg_m2_crop": 0.56},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 1, "yield_per_m2_per_crop": 34, "nutrients_kg_m2_crop": 0.58},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1, "yield_per_m2_per_crop": 22, "nutrients_kg_m2_crop": 0.42},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 4, "yield_per_m2_per_crop": 2.6, "nutrients_kg_m2_crop": 0.16},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 4, "yield_per_m2_per_crop": 2.4, "nutrients_kg_m2_crop": 0.16},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1, "yield_per_m2_per_crop": 5.2, "nutrients_kg_m2_crop": 0.47},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 3, "yield_per_m2_per_crop": 1.6, "nutrients_kg_m2_crop": 0.18},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.3, "nutrients_kg_m2_crop": 0.13},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.8, "nutrients_kg_m2_crop": 0.17},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 3, "yield_per_m2_per_crop": 0.8, "nutrients_kg_m2_crop": 0.40},
        }
    },
    "CA": {
        "soil": {
            "tomato":         {"plants_per_m2": 2.0, "crops_per_year": 1, "yield_per_m2_per_crop": 30, "nutrients_kg_m2_crop": 0.60},
            "pepper":         {"plants_per_m2": 2.5, "crops_per_year": 1, "yield_per_m2_per_crop": 26, "nutrients_kg_m2_crop": 0.55},
            "cucumber":       {"plants_per_m2": 1.8, "crops_per_year": 1, "yield_per_m2_per_crop": 32, "nutrients_kg_m2_crop": 0.56},
            "strawberry":     {"plants_per_m2": 7.0, "crops_per_year": 1, "yield_per_m2_per_crop": 21, "nutrients_kg_m2_crop": 0.41},
            "lettuce":        {"plants_per_m2": 16,  "crops_per_year": 4, "yield_per_m2_per_crop": 2.5, "nutrients_kg_m2_crop": 0.16},
            "spinach":        {"plants_per_m2": 16,  "crops_per_year": 4, "yield_per_m2_per_crop": 2.3, "nutrients_kg_m2_crop": 0.16},
            "potato":         {"plants_per_m2": 3.5, "crops_per_year": 1, "yield_per_m2_per_crop": 5.0, "nutrients_kg_m2_crop": 0.46},
            "fluted_pumpkin": {"plants_per_m2": 3.5, "crops_per_year": 3, "yield_per_m2_per_crop": 1.5, "nutrients_kg_m2_crop": 0.18},
            "basil":          {"plants_per_m2": 20,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.2, "nutrients_kg_m2_crop": 0.13},
            "water_leaf":     {"plants_per_m2": 14,  "crops_per_year": 4, "yield_per_m2_per_crop": 1.7, "nutrients_kg_m2_crop": 0.17},
            "cannabis":       {"plants_per_m2": 5.0, "crops_per_year": 3, "yield_per_m2_per_crop": 0.8, "nutrients_kg_m2_crop": 0.40},
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

# FX: how many USD is 1 unit of that currency
FX_TO_USD = {
    "USD": 1.0,
    "EUR": 1.10,
    "CAD": 0.75,
    "NGN": 0.0008,  # ~1 USD / 1250 NGN
    "TRY": 0.032,
    "ANG": 0.56,
    "GBP": 1.25,
}


def convert_currency(amount, from_code, to_code):
    if from_code == to_code:
        return amount
    from_rate = FX_TO_USD.get(from_code)
    to_rate = FX_TO_USD.get(to_code)
    if not from_rate or not to_rate:
        return amount
    amount_usd = amount * from_rate
    return amount_usd / to_rate


# Prices per kg in local currency
PRICE_PER_KG_LOCAL = {
    "GLOBAL": {  # USD/kg fallback
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
    "US": {  # USD/kg
        "tomato":         3.0,
        "pepper":         4.0,
        "cucumber":       2.5,
        "strawberry":     8.0,
        "lettuce":        4.0,
        "spinach":        4.5,
        "potato":         1.8,
        "fluted_pumpkin": 3.0,
        "basil":         18.0,
        "water_leaf":     3.0,
        "cannabis":    1800.0,
    },
    "CA": {  # CAD/kg
        "tomato":         4.0,
        "pepper":         5.0,
        "cucumber":       3.5,
        "strawberry":     9.0,
        "lettuce":        4.5,
        "spinach":        5.0,
        "potato":         2.2,
        "fluted_pumpkin": 3.5,
        "basil":         20.0,
        "water_leaf":     3.5,
        "cannabis":    1700.0,
    },
    "NG": {  # NGN/kg (indicative)
        "tomato":          900.0,
        "pepper":         1300.0,
        "cucumber":        700.0,
        "strawberry":     2500.0,
        "lettuce":         900.0,
        "spinach":         700.0,
        "potato":          700.0,   # potato example
        "fluted_pumpkin":  600.0,
        "basil":          4000.0,
        "water_leaf":      500.0,
        "cannabis":    300000.0,
    },
}


def estimate_price_per_kg_local(crop, country_code):
    table = PRICE_PER_KG_LOCAL.get(country_code)
    if table and crop in table:
        return table[crop], country_code
    price = PRICE_PER_KG_LOCAL["GLOBAL"].get(crop, 0.0)
    return price, "USD"


# Annual production cost per m² (variable) in base currency
PRODUCTION_COST_PER_M2_LOCAL = {
    "GLOBAL": {  # USD/m²/year
        "soil":        {"local": 3.0,  "standard": 4.0,  "hightech": 5.0},
        "soilless":    {"local": 5.0,  "standard": 7.0,  "hightech": 9.0},
        "hydroponics": {"local": 6.0,  "standard": 8.0,  "hightech":10.0},
        "aeroponics":  {"local": 7.0,  "standard": 9.0,  "hightech":11.0},
        "vertical":    {"local":10.0,  "standard":14.0,  "hightech":18.0},
    },
    "US": {  # USD/m²/year
        "soil":        {"local": 4.0,  "standard": 5.5,  "hightech": 7.0},
        "soilless":    {"local": 6.0,  "standard": 8.0,  "hightech":11.0},
        "hydroponics": {"local": 7.0,  "standard": 9.0,  "hightech":12.0},
        "aeroponics":  {"local": 8.0,  "standard":10.0,  "hightech":13.0},
        "vertical":    {"local":12.0,  "standard":16.0,  "hightech":21.0},
    },
    "CA": {  # CAD/m²/year
        "soil":        {"local": 4.5,  "standard": 6.0,  "hightech": 7.5},
        "soilless":    {"local": 6.5,  "standard": 8.5,  "hightech":11.5},
        "hydroponics": {"local": 7.5,  "standard": 9.5,  "hightech":12.5},
        "aeroponics":  {"local": 8.5,  "standard":10.5,  "hightech":13.5},
        "vertical":    {"local":13.0,  "standard":17.0,  "hightech":22.0},
    },
    "NG": {  # NGN/m²/year (indicative)
        "soil":        {"local":  500.0, "standard":  800.0, "hightech": 1200.0},
        "soilless":    {"local": 1000.0, "standard": 1400.0, "hightech": 2000.0},
        "hydroponics": {"local": 1100.0, "standard": 1600.0, "hightech": 2200.0},
        "aeroponics":  {"local": 1200.0, "standard": 1700.0, "hightech": 2400.0},
        "vertical":    {"local": 1800.0, "standard": 2400.0, "hightech": 3500.0},
    },
}


def farm_size_factor(area_m2):
    if area_m2 <= 0:
        return 1.0
    if area_m2 < 500:
        return 1.15
    if area_m2 < 2000:
        return 1.00
    if area_m2 < 5000:
        return 0.90
    return 0.80


def estimate_annual_production_cost(country_code, system_type, setup_level,
                                    area_m2, display_currency, base_currency_code):
    if area_m2 <= 0:
        return 0.0
    country_table = PRODUCTION_COST_PER_M2_LOCAL.get(country_code) or PRODUCTION_COST_PER_M2_LOCAL["GLOBAL"]
    system_table = country_table.get(system_type) or country_table.get("soil")
    if not system_table:
        system_table = PRODUCTION_COST_PER_M2_LOCAL["GLOBAL"]["soil"]
    base_per_m2 = system_table.get(setup_level, list(system_table.values())[0])
    size_mult = farm_size_factor(area_m2)
    base_total = base_per_m2 * size_mult * area_m2
    return convert_currency(base_total, base_currency_code, display_currency)


# CAPEX per m² in base currency
CAPEX_PER_M2_LOCAL = {
    "GLOBAL": {"local": 80.0,   "standard": 150.0,  "hightech": 400.0},   # USD
    "US":     {"local":120.0,   "standard": 250.0,  "hightech": 750.0},   # USD
    "CA":     {"local":130.0,   "standard": 270.0,  "hightech": 780.0},   # CAD
    "NG":     {"local":62500.0, "standard":137500.0,"hightech":312500.0}, # NGN
}


def estimate_capex_per_m2_display(setup_level, country_code,
                                  display_currency, base_currency_code):
    table = CAPEX_PER_M2_LOCAL.get(country_code, CAPEX_PER_M2_LOCAL["GLOBAL"])
    base_val = table.get(setup_level, table.get("standard", 150.0))
    return convert_currency(base_val, base_currency_code, display_currency)


# ================
#  DB helper funcs
# ================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE history (
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
    try:
        area = float(form_dict.get("area_m2", 0) or 0)
    except ValueError:
        area = 0

    crop = form_dict.get("crop", "tomato")
    system_type = form_dict.get("system_type", "soilless")
    setup_level = form_dict.get("setup_level", "standard")
    country_code = form_dict.get("country") or "US"

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
        total_display = estimate_annual_production_cost(
            country_code=country_code,
            system_type=system_type,
            setup_level=setup_level,
            area_m2=area,
            display_currency=display_curr,
            base_currency_code=base_curr,
        )
        form_dict["annual_production_cost"] = f"{total_display:.2f}"

    # Price per kg
    raw_price = (form_dict.get("price_per_unit") or "").strip()
    try:
        price_val = float(raw_price) if raw_price else 0
    except ValueError:
        price_val = 0

    if price_val <= 0:
        base_price_per_kg, base_price_curr = estimate_price_per_kg_local(crop, country_code)
        price_display_per_kg = convert_currency(base_price_per_kg, base_price_curr, display_curr)
        form_dict["price_per_unit"] = f"{price_display_per_kg:.3f}"

    # CAPEX per m²
    raw_capex = (form_dict.get("capex_per_m2") or "").strip()
    try:
        capex_val = float(raw_capex) if raw_capex else 0
    except ValueError:
        capex_val = 0

    if capex_val <= 0:
        capex_display = estimate_capex_per_m2_display(
            setup_level=setup_level,
            country_code=country_code,
            display_currency=display_curr,
            base_currency_code=base_curr,
        )
        form_dict["capex_per_m2"] = f"{capex_display:.0f}"


# =====================
#  Core calculation
# =====================
def compute_results(form):
    try:
        area = float(form.get("area_m2", 0) or 0)
    except ValueError:
        area = 0

    crop = form.get("crop", "tomato")
    system_type = form.get("system_type", "soilless")
    setup_level = form.get("setup_level", "standard")
    use_solar = form.get("use_solar") == "on"
    country_code = form.get("country", "") or "US"
    currency_override = (form.get("currency_override") or "").strip()

    if not area:
        return None, "Please fill in the greenhouse area."

    country = find_country(country_code)
    base_currency_code = country["currency_code"] if country else "USD"
    base_currency_symbol = country["currency_symbol"] if country else "$"

    if currency_override:
        currency_code = currency_override.upper()
        currency_symbol = currency_code
    else:
        currency_code = base_currency_code
        currency_symbol = base_currency_symbol

    # Crop params
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

    # Price (per kg)
    raw_price = (form.get("price_per_unit") or "").strip()
    try:
        price_per_kg = float(raw_price) if raw_price else 0
    except ValueError:
        price_per_kg = 0

    # Production cost
    raw_cost = (form.get("annual_production_cost") or "").strip()
    try:
        gross_production_cost = float(raw_cost) if raw_cost else 0
    except ValueError:
        gross_production_cost = 0

    # CAPEX per m²
    raw_capex = (form.get("capex_per_m2") or "").strip()
    try:
        capex_per_m2 = float(raw_capex) if raw_capex else 0
    except ValueError:
        capex_per_m2 = 0

    # Solar
    solar_savings = gross_production_cost * SOLAR_SAVINGS_RATE if use_solar else 0.0
    net_production_cost = gross_production_cost - solar_savings

    # Economics
    cost_per_kg = (net_production_cost / annual_yield) if annual_yield > 0 else None
    annual_revenue = annual_yield * price_per_kg
    annual_profit = annual_revenue - net_production_cost

    cost_per_m2_per_year = net_production_cost / area if area > 0 else 0
    cost_per_plant_per_year = net_production_cost / plants if plants > 0 else 0

    profit_per_kg = (annual_profit / annual_yield) if annual_yield > 0 else None
    profit_per_m2_per_year = annual_profit / area if area > 0 else 0
    profit_per_plant_per_year = annual_profit / plants if plants > 0 else 0

    revenue_per_m2_per_year = annual_revenue / area if area > 0 else 0
    revenue_per_plant_per_year = annual_revenue / plants if plants > 0 else 0

    total_setup_cost = capex_per_m2 * area
    simple_payback_years = (total_setup_cost / annual_profit) if annual_profit > 0 else None

    setup_label = SETUP_LEVEL_LABELS.get(setup_level, setup_level)

    results = {
        "currency_code": currency_code,
        "currency_symbol": currency_symbol,
        "plants_per_m2": plants_per_m2,
        "crops_per_year": crops_per_year,
        "yield_per_m2_per_crop": yield_per_m2_per_crop,
        "plants": plants,
        "annual_yield": annual_yield,
        "gross_production_cost": gross_production_cost,
        "solar_savings": solar_savings,
        "net_production_cost": net_production_cost,
        "cost_per_kg": cost_per_kg,
        "cost_per_m2_per_year": cost_per_m2_per_year,
        "cost_per_plant_per_year": cost_per_plant_per_year,
        "price_per_kg": price_per_kg,
        "price_per_unit_used": price_per_kg,
        "annual_revenue": annual_revenue,
        "annual_profit": annual_profit,
        "profit_per_kg": profit_per_kg,
        "profit_per_m2_per_year": profit_per_m2_per_year,
        "profit_per_plant_per_year": profit_per_plant_per_year,
        "total_setup_cost": total_setup_cost,
        "simple_payback_years": simple_payback_years,
        "setup_label": setup_label,
        "capex_per_m2": capex_per_m2,
        "setup_level": setup_level,
        "area": area,
        "crop": crop,
        "system_type": system_type,
        "use_solar": use_solar,
        "country_code": country_code,
        "currency_override": currency_override,
        "SOLAR_SAVINGS_RATE": SOLAR_SAVINGS_RATE,
        "nutrient_per_m2_per_crop": nutrient_per_m2_per_crop,
        "nutrient_per_crop_total": nutrient_per_crop_total,
        "annual_nutrient_total": annual_nutrient_total,
        "nutrient_per_plant_per_crop": nutrient_per_plant_per_crop,
        "revenue_per_m2_per_year": revenue_per_m2_per_year,
        "revenue_per_plant_per_year": revenue_per_plant_per_year,
    }

    return results, None


# =============
#  Routes
# =============
@app.route("/", methods=["GET", "POST"])
def index():
    

    default_country = ""
    if not any(c["code"] == "" for c in COUNTRIES) and COUNTRIES:
        default_country = COUNTRIES[0]["code"]

    form_defaults = {
        "area_m2": "",
        "system_type": "soil",
        "crop": "",
        "annual_production_cost": "",
        "use_solar": False,
        "price_per_unit": "",
        "setup_level": "standard",
        "capex_per_m2": "",
        "country": default_country,
        "currency_override": "",
        "use_custom_production_cost": False,
        "use_custom_price": False,
        "use_custom_capex": False,
    }

    result = None
    error = None

    if request.method == "POST":
        form_data = {**form_defaults, **request.form.to_dict()}

        try:
            area_m2 = float(form_data.get("area_m2", 0))
            system_type = form_data.get("system_type", "")
            crop = form_data.get("crop", "")
            country = form_data.get("country", "")

            # ---- calculation (example) ----
            savings = round(area_m2 * SOLAR_SAVINGS_RATE, 2)
            result = savings

            # ---- store session (optional) ----
            session["last_form"] = form_data
            session["last_results"] = {"savings": savings}

            # ✅ SAVE TO HISTORY (THIS IS THE IMPORTANT PART)
            conn = get_db()
            conn.execute(
                """
                INSERT INTO history (
                    area_m2, system_type, crop, country, savings
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (area_m2, system_type, crop, country, savings)
            )
            conn.commit()

            return redirect(url_for("results_page"))

        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        defaults=form_defaults,
        result=result,
        error=error,
        countries=COUNTRIES,
    )


@app.route("/results")
def results_page():
    return render_template(
        "results.html",
        form=session.get("last_form"),
        results=session.get("last_results"),
    )


@app.route("/admin/history")
def admin_history():
    key = request.args.get("key", "")

    if not ADMIN_KEY or key != ADMIN_KEY:
        abort(403)

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history ORDER BY id DESC"
    ).fetchall()

    return render_template(
        "admin_history.html",
        history=rows
    )

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)