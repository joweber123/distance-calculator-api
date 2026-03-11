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

# HubSpot-compatible ISO2 country labels (full list)
COUNTRY_LABELS = {
    "AF": "Afghanistan", "AX": "\u00c5land Islands", "AL": "Albania", "DZ": "Algeria",
    "AS": "American Samoa", "AD": "Andorra", "AO": "Angola", "AI": "Anguilla",
    "AQ": "Antarctica", "AG": "Antigua and Barbuda", "AR": "Argentina", "AM": "Armenia",
    "AW": "Aruba", "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan",
    "BS": "Bahamas", "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados",
    "BY": "Belarus", "BE": "Belgium", "BZ": "Belize", "BJ": "Benin", "BM": "Bermuda",
    "BT": "Bhutan", "BO": "Bolivia (Plurinational State of)",
    "BQ": "Bonaire, Sint Eustatius and Saba", "BA": "Bosnia and Herzegovina",
    "BW": "Botswana", "BV": "Bouvet Island", "BR": "Brazil",
    "IO": "British Indian Ocean Territory", "BN": "Brunei Darussalam", "BG": "Bulgaria",
    "BF": "Burkina Faso", "BI": "Burundi", "CV": "Cabo Verde", "KH": "Cambodia",
    "CM": "Cameroon", "CA": "Canada", "KY": "Cayman Islands",
    "CF": "Central African Republic", "TD": "Chad", "CL": "Chile", "CN": "China",
    "CX": "Christmas Island", "CC": "Cocos (Keeling) Islands", "CO": "Colombia",
    "KM": "Comoros", "CG": "Congo", "CD": "Congo, Democratic Republic of the",
    "CK": "Cook Islands", "CR": "Costa Rica", "CI": "C\u00f4te d'Ivoire", "HR": "Croatia",
    "CU": "Cuba", "CW": "Cura\u00e7ao", "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark",
    "DJ": "Djibouti", "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador",
    "EG": "Egypt", "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea",
    "EE": "Estonia", "SZ": "Eswatini", "ET": "Ethiopia",
    "FK": "Falkland Islands (Malvinas)", "FO": "Faroe Islands", "FJ": "Fiji",
    "FI": "Finland", "FR": "France", "GF": "French Guiana", "PF": "French Polynesia",
    "TF": "French Southern Territories", "GA": "Gabon", "GM": "Gambia", "GE": "Georgia",
    "DE": "Germany", "GH": "Ghana", "GI": "Gibraltar", "GR": "Greece", "GL": "Greenland",
    "GD": "Grenada", "GP": "Guadeloupe", "GU": "Guam", "GT": "Guatemala",
    "GG": "Guernsey", "GN": "Guinea", "GW": "Guinea-Bissau", "GY": "Guyana",
    "HT": "Haiti", "HM": "Heard Island and McDonald Islands", "VA": "Holy See",
    "HN": "Honduras", "HK": "Hong Kong", "HU": "Hungary", "IS": "Iceland", "IN": "India",
    "ID": "Indonesia", "IR": "Iran (Islamic Republic of)", "IQ": "Iraq", "IE": "Ireland",
    "IM": "Isle of Man", "IL": "Israel", "IT": "Italy", "JM": "Jamaica", "JP": "Japan",
    "JE": "Jersey", "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya", "KI": "Kiribati",
    "KP": "Korea (Democratic People's Republic of)", "KR": "Korea, Republic of",
    "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Lao People's Democratic Republic",
    "LV": "Latvia", "LB": "Lebanon", "LS": "Lesotho", "LR": "Liberia", "LY": "Libya",
    "LI": "Liechtenstein", "LT": "Lithuania", "LU": "Luxembourg", "MO": "Macao",
    "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia", "MV": "Maldives", "ML": "Mali",
    "MT": "Malta", "MH": "Marshall Islands", "MQ": "Martinique", "MR": "Mauritania",
    "MU": "Mauritius", "YT": "Mayotte", "MX": "Mexico",
    "FM": "Micronesia (Federated States of)", "MD": "Moldova, Republic of",
    "MC": "Monaco", "MN": "Mongolia", "ME": "Montenegro", "MS": "Montserrat",
    "MA": "Morocco", "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia", "NR": "Nauru",
    "NP": "Nepal", "NL": "Netherlands", "NC": "New Caledonia", "NZ": "New Zealand",
    "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "NU": "Niue",
    "NF": "Norfolk Island", "MK": "North Macedonia", "MP": "Northern Mariana Islands",
    "NO": "Norway", "OM": "Oman", "PK": "Pakistan", "PW": "Palau",
    "PS": "Palestine, State of", "PA": "Panama", "PG": "Papua New Guinea",
    "PY": "Paraguay", "PE": "Peru", "PH": "Philippines", "PN": "Pitcairn",
    "PL": "Poland", "PT": "Portugal", "PR": "Puerto Rico", "QA": "Qatar",
    "RE": "R\u00e9union", "RO": "Romania", "RU": "Russian Federation", "RW": "Rwanda",
    "BL": "Saint Barth\u00e9lemy",
    "SH": "Saint Helena, Ascension and Tristan da Cunha",
    "KN": "Saint Kitts and Nevis", "LC": "Saint Lucia",
    "MF": "Saint Martin (French part)", "PM": "Saint Pierre and Miquelon",
    "VC": "Saint Vincent and the Grenadines", "WS": "Samoa", "SM": "San Marino",
    "ST": "Sao Tome and Principe", "SA": "Saudi Arabia", "SN": "Senegal",
    "RS": "Serbia", "SC": "Seychelles", "SL": "Sierra Leone", "SG": "Singapore",
    "SX": "Sint Maarten (Dutch part)", "SK": "Slovakia", "SI": "Slovenia",
    "SB": "Solomon Islands", "SO": "Somalia", "ZA": "South Africa",
    "GS": "South Georgia and the South Sandwich Islands", "SS": "South Sudan",
    "ES": "Spain", "LK": "Sri Lanka", "SD": "Sudan", "SR": "Suriname",
    "SJ": "Svalbard and Jan Mayen", "SE": "Sweden", "CH": "Switzerland",
    "SY": "Syrian Arab Republic", "TW": "Taiwan, Province of China",
    "TJ": "Tajikistan", "TZ": "Tanzania, United Republic of", "TH": "Thailand",
    "TL": "Timor-Leste", "TG": "Togo", "TK": "Tokelau", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "TN": "Tunisia", "TR": "Turkey", "TM": "Turkmenistan",
    "TC": "Turks and Caicos Islands", "TV": "Tuvalu", "UG": "Uganda", "UA": "Ukraine",
    "AE": "United Arab Emirates",
    "GB": "United Kingdom of Great Britain and Northern Ireland",
    "US": "United States of America", "UM": "United States Minor Outlying Islands",
    "UY": "Uruguay", "UZ": "Uzbekistan", "VU": "Vanuatu",
    "VE": "Venezuela (Bolivarian Republic of)", "VN": "Viet Nam",
    "VG": "Virgin Islands (British)", "VI": "Virgin Islands (U.S.)",
    "WF": "Wallis and Futuna", "EH": "Western Sahara", "YE": "Yemen", "ZM": "Zambia",
    "ZW": "Zimbabwe", "XK": "Kosovo",
}

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


@app.route("/countries", methods=["GET"])
def countries():
    """Return list of supported countries (those with loaded city databases)."""
    result = []
    for cc in sorted(LOADED_COUNTRIES):
        label = COUNTRY_LABELS.get(cc, cc)
        # Count cities for this country
        count = sum(1 for v in CITY_DB.values() if v.get("country_code") == cc)
        result.append({"code": cc, "label": f"{cc} - {label}", "name": label, "city_count": count})
    return jsonify({"countries": result})


@app.route("/cities", methods=["GET"])
def cities():
    """Return cities for a given country code.

    Query params:
        country_code (required): ISO2 country code
        q (optional): search/filter string
        limit (optional): max results (default 50)
    """
    cc = request.args.get("country_code", "").upper()
    if not cc:
        return jsonify({"error": "country_code query param required"}), 400
    if cc not in LOADED_COUNTRIES:
        return jsonify({"error": f"Country {cc} not loaded", "available": LOADED_COUNTRIES}), 404

    q = (request.args.get("q", "") or "").lower().strip()
    limit = min(int(request.args.get("limit", 50)), 500)

    results = []
    for key, data in CITY_DB.items():
        if data.get("country_code") != cc:
            continue
        city_name = key.split(",")[0]
        # If there's a query, filter
        if q and q not in city_name:
            continue
        # Use the full key parts for display
        parts = key.split(",")
        display_city = parts[0].title()
        state = parts[1].strip().title() if len(parts) > 1 else ""
        results.append({
            "city": display_city,
            "state": state,
            "key": key,
            "lat": data["lat"],
            "lon": data["lon"],
            "population": data["population"],
        })

    # Sort by population descending so biggest cities come first
    results.sort(key=lambda x: x["population"], reverse=True)
    results = results[:limit]

    return jsonify({"cities": results, "total": len(results), "country_code": cc})


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
