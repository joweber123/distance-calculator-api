#!/usr/bin/env python3
"""
Distance Calculator Flask API

Provides geocoding and distance calculation endpoints using city databases
from the sdr-bridge-city-databases repository.
"""

import json
import math
import os
from functools import wraps
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/joweber123/"
    "sdr-bridge-city-databases/main"
)
SUPPORTED_COUNTRIES = os.environ.get("SUPPORTED_COUNTRIES", "IN,CA,GB,AU,JP,DE,FR,NL,NZ,SG")
API_TOKEN = os.environ.get("API_TOKEN")

# ---------------------------------------------------------------------------
# City name variations (per-country, expandable)
# ---------------------------------------------------------------------------

VARIATIONS = {
    "IN": {
        "bengaluru": "bangalore",
        "bangalore": "bengaluru",
        "ahmadabad": "ahmedabad",
        "calcutta": "kolkata",
        "delhi": "new delhi",
        "gurugram": "gurgaon",
        "gurgaon": "gurugram",
        "vizag": "visakhapatnam",
        "pondicherry": "puducherry",
        "trivandrum": "thiruvananthapuram",
        "madras": "chennai",
        "bombay": "mumbai",
        "ahmeadabad": "ahmedabad",
        "banaglore": "bengaluru",
        "ghaaziabad": "ghaziabad",
        "gurgoan": "gurugram",
        "mubmai": "mumbai",
        "jaiipur": "jaipur",
        "vijapuer": "vijayapura",
        "mysore": "mysuru",
        "trichy": "tiruchirappalli",
        "margao": "madgaon",
        "panaji": "panjim",
        "north goa": "panaji",
    },
    # Add other country variations here as needed, e.g.:
    # "GB": {"centre": "center", ...},
}

# Flattened variations for when no country filter is applied
ALL_VARIATIONS = {}
for _cc, _v in VARIATIONS.items():
    ALL_VARIATIONS.update(_v)

# ---------------------------------------------------------------------------
# In-memory city store
# ---------------------------------------------------------------------------

# Structure: {
#   "city,state,country": {"lat": float, "lon": float, "population": int, "country_code": "XX"}
# }
CITY_DB: dict = {}
LOADED_COUNTRIES: list = []

# ---------------------------------------------------------------------------
# Core math & geocoding (extracted from calculate_distances.py)
# ---------------------------------------------------------------------------

KM_PER_MILE = 1.60934
EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_MILES = 3958.8


def calculate_distance(lat1, lon1, lat2, lon2, unit="km"):
    """
    Calculate distance between two points using the Haversine formula.

    Args:
        lat1, lon1: Coordinates of point 1.
        lat2, lon2: Coordinates of point 2.
        unit: "km" or "miles" (default "km").

    Returns:
        dict with distance_km and distance_miles.
    """
    R = EARTH_RADIUS_KM if unit == "km" else EARTH_RADIUS_MILES

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance_primary = R * c

    if unit == "km":
        distance_km = distance_primary
        distance_miles = distance_primary / KM_PER_MILE
    else:
        distance_miles = distance_primary
        distance_km = distance_primary * KM_PER_MILE

    return {
        "distance_km": round(distance_km, 2),
        "distance_miles": round(distance_miles, 2),
    }


def normalize_city_name(city):
    """Normalize city name for matching."""
    if not city:
        return ""
    city = city.lower().strip()
    city = city.replace(" city", "")
    return city


def find_city_in_database(city_name, city_db, country_code=None):
    """
    Try to find a city in the database with various matching strategies.

    Args:
        city_name: Name to search for.
        city_db: The city database dict.
        country_code: Optional ISO-2 code to restrict the search.

    Returns:
        tuple: (match_key, data_dict, match_type) or (None, None, "not_found")
    """
    normalized = normalize_city_name(city_name)
    if not normalized:
        return None, None, "empty"

    # Optionally filter the DB to entries for a given country
    if country_code:
        cc_upper = country_code.upper()
        subset = {
            k: v for k, v in city_db.items() if v.get("country_code") == cc_upper
        }
    else:
        subset = city_db

    # Strategy 1: Exact match on the city part of the key
    for key, data in subset.items():
        city_part = key.split(",")[0]
        if city_part == normalized:
            return key, data, "exact"

    # Strategy 2: Partial / substring match
    # Only match when the search term contains the DB entry or vice-versa,
    # but require sufficient overlap to avoid false positives.
    partial_matches = []
    for key, data in subset.items():
        city_part = key.split(",")[0]
        if normalized in city_part or city_part in normalized:
            shorter = min(len(normalized), len(city_part))
            longer = max(len(normalized), len(city_part))
            # Require the shorter string to be at least 70% of the longer
            # to avoid "banga" matching "bangalore" etc.
            if shorter >= 4 and shorter / longer >= 0.7:
                partial_matches.append((key, data))

    if len(partial_matches) == 1:
        return partial_matches[0][0], partial_matches[0][1], "partial"
    elif len(partial_matches) > 1:
        best = max(partial_matches, key=lambda x: x[1]["population"])
        return best[0], best[1], "partial_multiple"

    # Strategy 3: Known variations / misspellings
    variations = {}
    if country_code:
        variations = VARIATIONS.get(country_code.upper(), {})
    else:
        variations = ALL_VARIATIONS

    if normalized in variations:
        alt_name = variations[normalized]
        for key, data in subset.items():
            city_part = key.split(",")[0]
            if city_part == alt_name or alt_name in city_part:
                return key, data, "variation"

    return None, None, "not_found"


# ---------------------------------------------------------------------------
# Database loading helpers
# ---------------------------------------------------------------------------


def load_city_database(path):
    """Load a city database JSON file from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_city_database_from_github(country_code):
    """Download a city database JSON from the GitHub repo."""
    url = f"{GITHUB_RAW_BASE}/{country_code.lower()}-cities5000.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        app.logger.warning("Failed to fetch %s from GitHub: %s", url, e)
        return None


def merge_into_db(data, country_code):
    """Merge a country's city dict into the global CITY_DB."""
    cc = country_code.upper()
    count = 0
    for key, entry in data.items():
        entry["country_code"] = cc
        CITY_DB[key] = entry
        count += 1
    return count


def load_all_databases():
    """Load city databases for all supported countries on startup."""
    global LOADED_COUNTRIES

    countries = [c.strip().upper() for c in SUPPORTED_COUNTRIES.split(",") if c.strip()]
    app_dir = Path(__file__).resolve().parent

    for cc in countries:
        data = None

        # 1) Check for a local file first
        local_path = app_dir / f"{cc.lower()}-cities5000.json"
        if local_path.exists():
            app.logger.info("Loading %s from local file: %s", cc, local_path)
            data = load_city_database(str(local_path))

        # 2) Fall back to GitHub
        if data is None:
            app.logger.info("Fetching %s from GitHub...", cc)
            data = fetch_city_database_from_github(cc)

        if data:
            n = merge_into_db(data, cc)
            LOADED_COUNTRIES.append(cc)
            app.logger.info("Loaded %d cities for %s", n, cc)
        else:
            app.logger.warning("Could not load database for %s", cc)

    app.logger.info(
        "City database ready: %d countries, %d total cities",
        len(LOADED_COUNTRIES),
        len(CITY_DB),
    )


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------


def require_auth(f):
    """Optional Bearer-token authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_TOKEN:
            return f(*args, **kwargs)
        auth_header = request.headers.get("Authorization", "")
        if auth_header == f"Bearer {API_TOKEN}":
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401

    return decorated


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request", "message": str(e.description)}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "countries_loaded": LOADED_COUNTRIES,
            "total_cities": len(CITY_DB),
        }
    )


@app.route("/geocode", methods=["POST"])
@require_auth
def geocode():
    body = request.get_json(silent=True) or {}
    city = body.get("city")
    if not city:
        return jsonify({"error": "Missing required field: city"}), 400

    country_code = body.get("country_code")

    key, data, match_type = find_city_in_database(city, CITY_DB, country_code)

    if data is None:
        return jsonify(
            {"error": "City not found", "city": city, "match_type": match_type}
        ), 404

    return jsonify(
        {
            "lat": data["lat"],
            "lon": data["lon"],
            "matched_city": key,
            "match_type": match_type,
            "country_code": data.get("country_code"),
        }
    )


@app.route("/distance", methods=["POST"])
@require_auth
def distance():
    body = request.get_json(silent=True) or {}

    try:
        lat1 = float(body["lat1"])
        lon1 = float(body["lon1"])
        lat2 = float(body["lat2"])
        lon2 = float(body["lon2"])
    except (KeyError, TypeError, ValueError):
        return jsonify(
            {"error": "Missing or invalid required fields: lat1, lon1, lat2, lon2"}
        ), 400

    unit = body.get("unit", "km")
    if unit not in ("km", "miles"):
        return jsonify({"error": "unit must be 'km' or 'miles'"}), 400

    result = calculate_distance(lat1, lon1, lat2, lon2, unit=unit)
    return jsonify(result)


@app.route("/distances", methods=["POST"])
@require_auth
def distances():
    body = request.get_json(silent=True) or {}

    try:
        ref_lat = float(body["ref_lat"])
        ref_lon = float(body["ref_lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Missing or invalid required fields: ref_lat, ref_lon"}), 400

    cities = body.get("cities")
    if not cities or not isinstance(cities, list):
        return jsonify({"error": "Missing or invalid required field: cities (array)"}), 400

    unit = body.get("unit", "km")
    if unit not in ("km", "miles"):
        return jsonify({"error": "unit must be 'km' or 'miles'"}), 400

    results = []
    for entry in cities:
        city_name = entry.get("city", "")
        cc = entry.get("country_code")

        key, data, match_type = find_city_in_database(city_name, CITY_DB, cc)

        if data:
            dist = calculate_distance(ref_lat, ref_lon, data["lat"], data["lon"], unit=unit)
            results.append(
                {
                    "city": city_name,
                    "lat": data["lat"],
                    "lon": data["lon"],
                    "distance_km": dist["distance_km"],
                    "distance_miles": dist["distance_miles"],
                    "match_type": match_type,
                    "matched_city": key,
                    "country_code": data.get("country_code"),
                }
            )
        else:
            results.append(
                {
                    "city": city_name,
                    "lat": None,
                    "lon": None,
                    "distance_km": None,
                    "distance_miles": None,
                    "match_type": match_type,
                    "matched_city": None,
                    "country_code": cc,
                }
            )

    return jsonify({"results": results})


@app.route("/geocode-and-distance", methods=["POST"])
@require_auth
def geocode_and_distance():
    body = request.get_json(silent=True) or {}

    ref_city = body.get("ref_city")
    if not ref_city:
        return jsonify({"error": "Missing required field: ref_city"}), 400

    ref_cc = body.get("ref_country_code")
    ref_key, ref_data, ref_match = find_city_in_database(ref_city, CITY_DB, ref_cc)

    if ref_data is None:
        return jsonify(
            {"error": "Reference city not found", "city": ref_city, "match_type": ref_match}
        ), 404

    cities = body.get("cities")
    if not cities or not isinstance(cities, list):
        return jsonify({"error": "Missing or invalid required field: cities (array)"}), 400

    unit = body.get("unit", "km")
    if unit not in ("km", "miles"):
        return jsonify({"error": "unit must be 'km' or 'miles'"}), 400

    ref_lat = ref_data["lat"]
    ref_lon = ref_data["lon"]

    results = []
    for entry in cities:
        city_name = entry.get("city", "")
        cc = entry.get("country_code")

        key, data, match_type = find_city_in_database(city_name, CITY_DB, cc)

        if data:
            dist = calculate_distance(ref_lat, ref_lon, data["lat"], data["lon"], unit=unit)
            results.append(
                {
                    "city": city_name,
                    "lat": data["lat"],
                    "lon": data["lon"],
                    "distance_km": dist["distance_km"],
                    "distance_miles": dist["distance_miles"],
                    "match_type": match_type,
                    "matched_city": key,
                    "country_code": data.get("country_code"),
                }
            )
        else:
            results.append(
                {
                    "city": city_name,
                    "lat": None,
                    "lon": None,
                    "distance_km": None,
                    "distance_miles": None,
                    "match_type": match_type,
                    "matched_city": None,
                    "country_code": cc,
                }
            )

    return jsonify(
        {
            "reference": {
                "city": ref_city,
                "matched_city": ref_key,
                "lat": ref_lat,
                "lon": ref_lon,
                "country_code": ref_data.get("country_code"),
            },
            "results": results,
        }
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

with app.app_context():
    load_all_databases()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
