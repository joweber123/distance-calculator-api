# Distance Calculator API

Flask API for geocoding cities and calculating distances using the Haversine formula. City databases are loaded from [sdr-bridge-city-databases](https://github.com/joweber123/sdr-bridge-city-databases) on startup, with local file fallback.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SUPPORTED_COUNTRIES` | `IN,CA,GB,AU,JP,DE,FR,NL,NZ,SG` | Comma-separated ISO-2 country codes to load |
| `API_TOKEN` | *(none)* | Bearer token for auth. If unset, auth is disabled |
| `PORT` | `5000` | Server port |

## Endpoints

### `GET /health`

```json
{"status": "ok", "countries_loaded": ["IN", "CA"], "total_cities": 12345}
```

### `POST /geocode`

Find coordinates for a city name.

```json
// Request
{"city": "Mumbai", "country_code": "IN"}

// Response
{"lat": 19.07283, "lon": 72.88261, "matched_city": "mumbai,maharashtra,india", "match_type": "exact", "country_code": "IN"}
```

`country_code` is optional -- omit it to search all loaded countries.

### `POST /distance`

Calculate distance between two coordinate pairs.

```json
// Request
{"lat1": 19.07, "lon1": 72.88, "lat2": 28.61, "lon2": 77.23, "unit": "km"}

// Response
{"distance_km": 1153.17, "distance_miles": 716.58}
```

### `POST /distances`

Calculate distances from a reference point to multiple cities.

```json
// Request
{
  "ref_lat": 19.07,
  "ref_lon": 72.88,
  "cities": [
    {"city": "Delhi", "country_code": "IN"},
    {"city": "Bangalore", "country_code": "IN"}
  ],
  "unit": "km"
}

// Response
{
  "results": [
    {"city": "Delhi", "lat": 28.65, "lon": 77.23, "distance_km": 1153.17, "distance_miles": 716.58, "match_type": "exact", "matched_city": "new delhi,delhi,india", "country_code": "IN"},
    ...
  ]
}
```

### `POST /geocode-and-distance`

Geocode a reference city, then calculate distances to a list of target cities.

```json
// Request
{
  "ref_city": "Mumbai",
  "ref_country_code": "IN",
  "cities": [
    {"city": "Delhi", "country_code": "IN"},
    {"city": "Pune", "country_code": "IN"}
  ],
  "unit": "km"
}

// Response
{
  "reference": {"city": "Mumbai", "matched_city": "mumbai,maharashtra,india", "lat": 19.07, "lon": 72.88, "country_code": "IN"},
  "results": [...]
}
```

## Authentication

Set `API_TOKEN` to require a Bearer token on all endpoints except `/health`:

```
Authorization: Bearer your-token-here
```

## Deployment

```bash
# Heroku / Railway / Render
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Utilities

`convert_geonames_to_json.py` converts raw GeoNames data into the JSON format used by this API.

```bash
python convert_geonames_to_json.py IN/IN.txt in-cities5000.json
```

## Data Source

City data from [GeoNames](https://www.geonames.org/) (Creative Commons Attribution 4.0).
