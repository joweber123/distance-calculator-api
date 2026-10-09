# Distance Calculator API

> **Retired 2026-10-09: Railway project `distance-calculator-api` deleted.** LCC now does metro/proximity matching itself (Census metros + EU/OECD functional urban areas, LCC ADR-092/095–097). Its only caller was domain-prep's nearby-companies feature (watch city geocode + `/distances`), unused since 2026-07-07. Domain-prep's `DISTANCE_API_URL` was removed, so those steps are skipped. It stored nothing (no DB, no volume; only env var `SUPPORTED_COUNTRIES`). To run it again locally: `python app.py` (port 4102). Was `https://distance-calculator-api-production.up.railway.app`.

Reviewed on 2026-06-24 as part of the Chief of Staff Code Wiki deep dive.

This repo is a Flask API for city lookup, geocoding, and Haversine distance
calculation. It grew out of a WordCamp Asia 2026 distance-enrichment script and
now loads country city databases from local JSON files or the
`sdr-bridge-city-databases` GitHub repo.

## What It Does

- Loads one or more `*-cities5000.json` city databases on startup.
- Looks up cities by exact match, partial match, or known variation/misspelling.
- Calculates great-circle distance in kilometers and miles.
- Exposes JSON API endpoints for geocoding and batch distance calculations.
- Includes a one-off WordCamp Asia 2026 CSV script that calculated company
  distance from Mumbai.

## Main API

`app.py` is the Flask entrypoint. On import/startup it:

1. Reads `SUPPORTED_COUNTRIES` from the environment.
2. For each country, checks for a local file named `<iso2-lower>-cities5000.json`.
3. If no local file exists, fetches the JSON from
   `https://raw.githubusercontent.com/joweber123/sdr-bridge-city-databases/main/`.
4. Merges the city entries into an in-memory `CITY_DB`, adding `country_code` to
   each loaded entry.

Default countries:

`IN,CA,GB,AU,JP,DE,FR,NL,NZ,SG`

Current local city JSON files:

- `in-cities5000.json` - tracked; 6,380 Indian cities with population >= 5,000.
- `pl-cities5000.json` - untracked local file; 755 Polish cities with
  population >= 5,000.

The API uses the Haversine formula with:

- Earth radius: `6371.0` km.
- Earth radius: `3958.8` miles.
- Conversion: `1 mile = 1.60934 km`.

## Endpoints

### `GET /health`

Public. Returns loaded countries and total loaded city count.

### `GET /countries`

Public. Returns loaded countries with HubSpot-compatible ISO2 labels and city
counts.

### `GET /cities`

Public. Requires `country_code`. Optional `q` and `limit`.

Returns the most populous matching cities first.

Example:

```bash
curl "http://localhost:4102/cities?country_code=IN&q=mum&limit=5"
```

### `POST /geocode`

Bearer-token protected only when `API_TOKEN` is set.

```json
{"city": "Mumbai", "country_code": "IN"}
```

Returns latitude, longitude, matched city key, match type, and country code.

### `POST /distance`

Bearer-token protected only when `API_TOKEN` is set.

```json
{"lat1": 19.07, "lon1": 72.88, "lat2": 28.61, "lon2": 77.23, "unit": "km"}
```

Returns both `distance_km` and `distance_miles`.

### `POST /distances`

Bearer-token protected only when `API_TOKEN` is set. Calculates distance from a
coordinate pair to many city names.

### `POST /geocode-and-distance`

Bearer-token protected only when `API_TOKEN` is set. Geocodes a reference city,
then calculates distances to many target cities.

## Authentication

Set `API_TOKEN` to require a Bearer token for the POST calculation/geocoding
endpoints:

```bash
Authorization: Bearer your-token-here
```

`/health`, `/countries`, and `/cities` are not decorated with auth in the
current code.

## Running Locally

```bash
cd /Users/jamesweber/Documents/Code/distance_calculator
python3 -m pip install -r requirements.txt
python3 app.py
```

Run with only the local India database:

```bash
SUPPORTED_COUNTRIES=IN python3 app.py
```

Run with auth enabled:

```bash
SUPPORTED_COUNTRIES=IN API_TOKEN=your-token python3 app.py
```

Production command from `Procfile`:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## WordCamp Asia CSV Script

`calculate_distances.py` is a one-off script for the WordCamp Asia 2026 prospect
list. It:

1. Loads `in-cities5000.json`.
2. Verifies the `City` column in `A4A - WordCamp Asia 2026 - Sheet10.csv`.
3. Uses Mumbai as the reference city.
4. Writes `WordCamp_Asia_2026_with_distances.csv` with:
   - `Distance (miles)`
   - `Distance (km)`
   - `Geocoded City`
   - `Match Type`

Current local CSV counts:

- Input CSV: 691 rows.
- Output CSV: 691 rows.
- Geocoded rows: 658.
- Not found / no distance: 33.
- Match type counts: 584 exact, 36 partial, 16 partial multiple, 22 variation,
  33 not found.

The input and output CSVs are ignored by git but present locally.

## GeoNames Conversion Utility

`convert_geonames_to_json.py` converts raw GeoNames tab-delimited data into the
JSON shape used by this API.

Important caveat: the current converter is India-specific. It has a hardcoded
Indian state-code map and writes keys ending in `india`. It is correct for:

```bash
python3 convert_geonames_to_json.py IN/IN.txt in-cities5000.json 5000
```

It should be generalized before using it for other countries.

Local raw GeoNames data:

- `IN/IN.txt` - ignored by git; 659,916 lines.
- `IN/readme.txt` - ignored by git.

## Repository State

- Git remote: `https://github.com/joweber123/distance-calculator-api.git`
- Branch: `main`
- Latest commit at review: `bd3c13d Add /countries and /cities endpoints with HubSpot ISO2 mapping`
- Tracked source files are clean.
- Local untracked file: `pl-cities5000.json`.
- Ignored local artifacts include the WordCamp Asia CSVs, raw `IN/` GeoNames
  folder, `.DS_Store`, and `__pycache__/`.

## Related Systems

- `sdr-bridge-city-databases` - canonical city database repo used as GitHub
  fallback and deployment data source.
- WordCamp Event Playbook - distance enrichment supported the WordCamp Asia
  2026 event workflow.
- SDR Bridge - `distance_calculation_system.md` documents the original browser
  extension distance-calculation concept this repo came from.

## Verification

During review, Python syntax compilation passed for `app.py`,
`calculate_distances.py`, and `convert_geonames_to_json.py`.

A local Flask test-client check with `SUPPORTED_COUNTRIES=IN` and `API_TOKEN`
set confirmed:

- `/health` returned India loaded with 6,380 cities.
- `/countries` returned the India label and city count.
- `/cities?country_code=IN&q=mum&limit=2` returned Mumbai and Navi Mumbai.
- `/geocode` returned `401` without auth and `200` with auth.
- `/distance` returned plausible Mumbai-to-Delhi distances.

## Chief of Staff Wiki

The durable project page lives in the Obsidian vault:

`300 A8C/Chief of Staff/Reference/Code Wiki/Projects/distance_calculator.md`
