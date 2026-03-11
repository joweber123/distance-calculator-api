# Distance Calculation System - Documentation

## Overview

This document describes the distance calculation functionality from the SDR Bridge extension, which can be adapted for a standalone Python program that processes CSV files with company location data.

**Source:** `/Users/jamesweber/Documents/Code/sdr_bridge/sidepanel.js` (lines 12074-12301)

---

## Core Algorithm: Haversine Formula

The system uses the **Haversine formula** to calculate the great-circle distance between two points on Earth.

### JavaScript Implementation (from extension)

```javascript
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 3958.8; // Earth's radius in miles
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}
```

### Key Constants

- **Earth's radius**: 3958.8 miles
- **Output**: Distance in miles
- **Unit conversion**: `kilometers = miles * 1.60934`

### Python Equivalent

```python
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1: Latitude of point 1 (decimal degrees)
        lon1: Longitude of point 1 (decimal degrees)
        lat2: Latitude of point 2 (decimal degrees)
        lon2: Longitude of point 2 (decimal degrees)

    Returns:
        Distance in miles (float)
    """
    R = 3958.8  # Earth's radius in miles

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
```

---

## Geocoding Strategy

The extension uses a **3-tier geocoding approach** optimized for speed and reliability:

### Tier 1: City Database (Primary - Fastest)

**Data Source:** `us-cities5000.json` (embedded in extension)

**Structure:**
```json
{
  "san francisco,california,united states": {
    "lat": 37.7749,
    "lon": -122.4194,
    "population": 805235
  },
  "new york city,new york,united states": {
    "lat": 40.7128,
    "lon": -74.0060,
    "population": 8175133
  }
}
```

**Coverage:**
- US: 7,494 cities
- Canada: 1,051 cities
- UK: 1,864 cities
- Australia: 1,453 cities
- Japan: 1,678 cities
- Germany: 2,989 cities
- France: 2,012 cities
- Netherlands: 527 cities
- New Zealand: 236 cities
- Singapore: 95 cities

**Key Format:** `"city,state,country"` (all lowercase)

**Location:** `/Users/jamesweber/Documents/Code/sdr_bridge/us-cities5000.json`

### Tier 2: Fuzzy Matching (Fallback)

If no exact match is found in the database, the system performs fuzzy matching:
- City name contains query
- State/province matching (if provided)
- Country matching (if provided)
- Results sorted by population (highest first)

### Tier 3: Nominatim API (Last Resort)

**Service:** OpenStreetMap's free geocoding API

**Endpoint:** `https://nominatim.openstreetmap.org/search`

**Parameters:**
```
q={city}, {state}, {country}
format=json
limit=1
```

**Headers:**
```
User-Agent: 'SDR Bridge Chrome Extension' (or custom for Python)
```

**Rate Limiting:**
- Free tier has usage limits
- Extension adds 100ms delay between API calls
- Only called when database lookup fails

**Authentication:** None required (public service)

---

## Data Structures

### Input: Location Data

```python
# CSV Input Format
{
    'domain': 'example.com',
    'city': 'San Francisco',
    'state': 'California',
    'country': 'United States'
}
```

### Output: Geocoding Result

```python
{
    'has_location': bool,      # Whether coordinates were found
    'distance': float or None, # Distance in miles
    'lat': float or None,      # Latitude
    'lon': float or None       # Longitude
}
```

### Reference Location (Event/Office)

```python
{
    'lat': 37.7749,           # Reference latitude
    'lon': -122.4194,         # Reference longitude
    'display_name': 'San Francisco, CA',
    'unit': 'miles'           # or 'km'
}
```

---

## Workflow

### 1. Load City Database

```python
import json

def load_city_database(db_path):
    """Load city database JSON file."""
    with open(db_path, 'r') as f:
        return json.load(f)
```

### 2. Geocode Location (Database First)

```python
def geocode_from_database(city, state, country, city_db):
    """
    Look up location in city database.

    Returns:
        dict: {lat, lon} or None if not found
    """
    # Normalize key
    key = f"{city},{state},{country}".lower()

    if key in city_db:
        return {
            'lat': city_db[key]['lat'],
            'lon': city_db[key]['lon']
        }

    return None
```

### 3. Geocode Location (API Fallback)

```python
import requests
import time

def geocode_from_nominatim(city, state, country, delay=0.1):
    """
    Geocode location using Nominatim API.

    Args:
        city: City name
        state: State/province name
        country: Country name
        delay: Delay in seconds between calls (rate limiting)

    Returns:
        dict: {lat, lon} or None if not found
    """
    # Build query
    query_parts = [p for p in [city, state, country] if p]
    query = ', '.join(query_parts)

    # Make API request
    url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': query,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'Distance Calculator Python Script'
    }

    try:
        time.sleep(delay)  # Rate limiting
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        results = response.json()
        if results:
            return {
                'lat': float(results[0]['lat']),
                'lon': float(results[0]['lon'])
            }
    except Exception as e:
        print(f"Error geocoding {query}: {e}")

    return None
```

### 4. Complete Geocoding Function

```python
def geocode_location(city, state, country, city_db, cache):
    """
    Geocode location using database first, then API fallback.

    Args:
        city: City name
        state: State/province
        country: Country name
        city_db: City database dict
        cache: Geocoding cache dict

    Returns:
        dict: {lat, lon} or None
    """
    # Check if we have minimal data
    if not city:
        return None

    # Create cache key
    cache_key = f"{city},{state},{country}".lower()

    # Check cache
    if cache_key in cache:
        return cache[cache_key]

    # Try database lookup
    result = geocode_from_database(city, state, country, city_db)

    # Try API fallback if database failed
    if result is None:
        result = geocode_from_nominatim(city, state, country)

    # Cache result (even if None, to avoid repeated failed lookups)
    cache[cache_key] = result

    return result
```

### 5. Process CSV File

```python
import csv

def process_csv(csv_path, reference_lat, reference_lon, city_db_path):
    """
    Process CSV file and calculate distances.

    Args:
        csv_path: Path to input CSV
        reference_lat: Reference point latitude
        reference_lon: Reference point longitude
        city_db_path: Path to city database JSON

    Returns:
        list: Results with distances
    """
    # Load city database
    city_db = load_city_database(city_db_path)

    # Initialize cache
    geocode_cache = {}

    # Results
    results = []

    # Read CSV
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            domain = row.get('domain', '')
            city = row.get('city', '')
            state = row.get('state', '')
            country = row.get('country', '')

            # Geocode
            coords = geocode_location(city, state, country, city_db, geocode_cache)

            # Calculate distance
            if coords:
                distance = calculate_distance(
                    reference_lat, reference_lon,
                    coords['lat'], coords['lon']
                )

                results.append({
                    'domain': domain,
                    'city': city,
                    'state': state,
                    'country': country,
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'distance_miles': distance,
                    'has_location': True
                })
            else:
                results.append({
                    'domain': domain,
                    'city': city,
                    'state': state,
                    'country': country,
                    'lat': None,
                    'lon': None,
                    'distance_miles': None,
                    'has_location': False
                })

    return results
```

---

## Caching Strategy

### Two-Level Cache Recommended

**Level 1: In-Memory Runtime Cache**
- Stores geocoded locations during script execution
- Key: `"{city},{state},{country}".lower()`
- Value: `{lat, lon}` or `None`
- Prevents duplicate API calls in same run

**Level 2: Persistent Disk Cache (Optional)**
```python
import json
import os

def load_persistent_cache(cache_path):
    """Load geocoding cache from disk."""
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)
    return {}

def save_persistent_cache(cache, cache_path):
    """Save geocoding cache to disk."""
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)
```

---

## Performance Considerations

### Speed Benchmarks (from extension)

- **Database lookup:** < 1ms
- **Haversine calculation:** < 1ms
- **Nominatim API call:** 200-500ms
- **Batch processing 100 companies:** 2-10 seconds (depends on cache hit rate)

### Optimization Tips

1. **Load database once** at script start
2. **Use cache** to avoid duplicate geocoding
3. **Database first** (fast) before API (slow)
4. **Batch operations** to leverage cache hits
5. **Save cache to disk** between runs
6. **Rate limit API calls** (100ms delay minimum)

### Memory Usage

- Geocoding cache: ~150 bytes per unique location
- City database: ~850 KB for US cities
- Results array: ~400 bytes per company

---

## Dependencies

### Python Libraries Required

```python
# Standard library
import csv
import json
import math
import time
import os

# Third-party (install via pip)
import requests  # For Nominatim API
```

### Install Command

```bash
pip install requests
```

---

## Configuration

### Required Inputs

1. **CSV file** with columns:
   - `domain` (company domain)
   - `city` (location city)
   - `state` (location state/province)
   - `country` (location country)

2. **Reference location** (event/office):
   - Latitude (decimal degrees)
   - Longitude (decimal degrees)

3. **City database JSON** file path

### Optional Inputs

- Output file path (default: add columns to input CSV)
- Distance unit (miles or kilometers)
- Cache file path
- API delay (default: 100ms)

---

## Output Format

### CSV Output

Add these columns to input CSV:

```csv
domain,city,state,country,latitude,longitude,distance_miles,has_location
example.com,San Francisco,California,United States,37.7749,-122.4194,0.0,true
acme.com,Portland,Oregon,United States,45.5152,-122.6784,535.2,true
unknown.com,,,,,,,false
```

### Statistics to Display

```
Total companies: 100
Geocoded successfully: 85 (85%)
Failed to geocode: 15 (15%)

Cache hits: 60 (60%)
Database lookups: 25 (25%)
API calls: 15 (15%)

Within 50 miles: 12 companies
Within 100 miles: 28 companies
Within 500 miles: 67 companies
```

---

## Error Handling

### Common Issues

1. **Missing location data** (city/state/country empty)
   - Skip geocoding, mark as `has_location=False`

2. **API rate limits exceeded**
   - Increase delay between calls
   - Consider paid geocoding service for large batches

3. **Network errors**
   - Retry with exponential backoff
   - Cache failures to avoid repeated attempts

4. **Invalid coordinates**
   - Validate latitude: -90 to 90
   - Validate longitude: -180 to 180

### Example Error Handling

```python
def geocode_with_retry(city, state, country, max_retries=3):
    """Geocode with retry logic."""
    for attempt in range(max_retries):
        try:
            return geocode_from_nominatim(city, state, country)
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # Exponential backoff
                print(f"Retry {attempt + 1}/{max_retries} after {wait}s...")
                time.sleep(wait)
            else:
                print(f"Failed after {max_retries} attempts: {e}")
                return None
```

---

## Complete Example Script Structure

```python
#!/usr/bin/env python3
"""
Distance Calculator - Calculate distances from CSV location data

Usage:
    python distance_calculator.py input.csv --lat 37.7749 --lon -122.4194
"""

import argparse
import csv
import json
import math
import time
import os
import requests

# --- Haversine Distance Calculation ---
def calculate_distance(lat1, lon1, lat2, lon2):
    # Implementation here
    pass

# --- Geocoding Functions ---
def load_city_database(db_path):
    # Implementation here
    pass

def geocode_from_database(city, state, country, city_db):
    # Implementation here
    pass

def geocode_from_nominatim(city, state, country, delay=0.1):
    # Implementation here
    pass

def geocode_location(city, state, country, city_db, cache):
    # Implementation here
    pass

# --- CSV Processing ---
def process_csv(csv_path, reference_lat, reference_lon, city_db_path, output_path):
    # Implementation here
    pass

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description='Calculate distances from CSV')
    parser.add_argument('input_csv', help='Input CSV file path')
    parser.add_argument('--lat', type=float, required=True, help='Reference latitude')
    parser.add_argument('--lon', type=float, required=True, help='Reference longitude')
    parser.add_argument('--city-db', default='us-cities5000.json', help='City database JSON')
    parser.add_argument('--output', help='Output CSV file path')
    parser.add_argument('--cache', default='.geocode_cache.json', help='Cache file path')

    args = parser.parse_args()

    # Process CSV
    results = process_csv(
        args.input_csv,
        args.lat,
        args.lon,
        args.city_db
    )

    # Write output
    output_path = args.output or args.input_csv.replace('.csv', '_with_distances.csv')
    write_output_csv(results, output_path)

    # Print statistics
    print_statistics(results)

if __name__ == '__main__':
    main()
```

---

## Key Files from Extension

### Source Files
- **Main logic:** `/Users/jamesweber/Documents/Code/sdr_bridge/sidepanel.js`
  - Lines 12074-12084: `calculateDistance()` function
  - Lines 12092-12210: `geocodePerson()` function
  - Lines 12213-12254: `geocodeAndCalculateDistances()` batch processing

### Data Files
- **City database:** `/Users/jamesweber/Documents/Code/sdr_bridge/us-cities5000.json`
  - 827 KB JSON file
  - 7,494 US cities with population > 5,000

---

## Additional Resources

### Nominatim API Documentation
- **Homepage:** https://nominatim.org/
- **Usage Policy:** https://operations.osmfoundation.org/policies/nominatim/
- **API Docs:** https://nominatim.org/release-docs/latest/api/Search/

### Haversine Formula
- **Wikipedia:** https://en.wikipedia.org/wiki/Haversine_formula
- **Explanation:** Great-circle distance between two points on a sphere

---

## Next Steps for Python Implementation

1. Copy `us-cities5000.json` to new Python project
2. Implement Haversine formula function
3. Implement database lookup function
4. Implement Nominatim API fallback
5. Add caching layer
6. Create CSV processing logic
7. Add CLI argument parsing
8. Test with sample data
9. Add error handling and retry logic
10. Optimize with persistent cache

---

**Document Version:** 1.0
**Created:** 2026-02-13
**Source Extension:** SDR Bridge Chrome Extension
