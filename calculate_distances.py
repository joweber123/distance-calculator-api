#!/usr/bin/env python3
"""
Calculate distances from Mumbai for WordCamp Asia 2026 companies.

This script:
1. Loads the city database
2. Verifies all city names can be geocoded
3. Cleans up city names that don't match
4. Calculates distances from Mumbai in miles and kilometers
5. Outputs a new CSV with distance columns
"""

import csv
import json
import math
import sys
from collections import defaultdict

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula.

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

def normalize_city_name(city):
    """Normalize city name for matching."""
    if not city:
        return ""

    # Convert to lowercase and strip whitespace
    city = city.lower().strip()

    # Remove common suffixes/qualifiers
    city = city.replace(' city', '')

    return city

def find_city_in_database(city_name, city_db):
    """
    Try to find a city in the database with various matching strategies.

    Returns:
        tuple: (match_key, {lat, lon, population}, match_type) or (None, None, None)
    """
    normalized = normalize_city_name(city_name)

    if not normalized:
        return None, None, "empty"

    # Strategy 1: Exact match with "city,state,india"
    for key in city_db:
        city_part = key.split(',')[0]
        if city_part == normalized:
            return key, city_db[key], "exact"

    # Strategy 2: Partial match (city name contains or is contained in database entry)
    partial_matches = []
    for key in city_db:
        city_part = key.split(',')[0]
        if normalized in city_part or city_part in normalized:
            partial_matches.append((key, city_db[key]))

    if len(partial_matches) == 1:
        return partial_matches[0][0], partial_matches[0][1], "partial"
    elif len(partial_matches) > 1:
        # Return the most populous city
        best_match = max(partial_matches, key=lambda x: x[1]['population'])
        return best_match[0], best_match[1], "partial_multiple"

    # Strategy 3: Common misspellings and variations
    variations = {
        # Standard variations
        'bengaluru': 'bangalore',
        'bangalore': 'bengaluru',
        'ahmadabad': 'ahmedabad',
        'mumbai': 'mumbai',
        'calcutta': 'kolkata',
        'delhi': 'new delhi',
        'gurugram': 'gurgaon',
        'gurgaon': 'gurugram',
        'vizag': 'visakhapatnam',
        'pondicherry': 'puducherry',
        'trivandrum': 'thiruvananthapuram',
        'madras': 'chennai',
        'bombay': 'mumbai',
        # Typos from CSV
        'ahmeadabad': 'ahmedabad',
        'banaglore': 'bengaluru',
        'ghaaziabad': 'ghaziabad',
        'gurgoan': 'gurugram',
        'mubmai': 'mumbai',
        'jaiipur': 'jaipur',
        'vijapuer': 'vijayapura',
        # Common alternative spellings
        'mysore': 'mysuru',
        'trichy': 'tiruchirappalli',
        'margao': 'madgaon',
        # Goa cities
        'panaji': 'panjim',
        'north goa': 'panaji',
    }

    if normalized in variations:
        alt_name = variations[normalized]
        for key in city_db:
            city_part = key.split(',')[0]
            if city_part == alt_name or alt_name in city_part:
                return key, city_db[key], "variation"

    return None, None, "not_found"

def load_city_database(db_path):
    """Load city database JSON file."""
    with open(db_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify_and_clean_cities(csv_path, city_db):
    """
    Verify all cities in CSV can be found in database.

    Returns:
        dict: Statistics about matches
    """
    stats = {
        'total': 0,
        'exact': 0,
        'partial': 0,
        'partial_multiple': 0,
        'variation': 0,
        'not_found': 0,
        'empty': 0
    }

    not_found_cities = defaultdict(list)  # city -> list of row numbers

    print("Verifying cities in database...")
    print("-" * 70)

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=2):  # Start at 2 because of header
            city = row.get('City', '').strip()
            stats['total'] += 1

            key, data, match_type = find_city_in_database(city, city_db)

            stats[match_type] += 1

            if match_type == 'not_found':
                not_found_cities[city].append(i)

    # Print statistics
    print(f"\nCity Matching Statistics:")
    print(f"  Total cities: {stats['total']}")
    print(f"  ✓ Exact matches: {stats['exact']}")
    print(f"  ✓ Partial matches: {stats['partial']}")
    print(f"  ✓ Multiple partial matches (used most populous): {stats['partial_multiple']}")
    print(f"  ✓ Variation matches: {stats['variation']}")
    print(f"  ⚠ Empty city names: {stats['empty']}")
    print(f"  ✗ Not found: {stats['not_found']}")

    if not_found_cities:
        print(f"\n⚠ Cities not found in database ({len(not_found_cities)} unique):")
        for city, rows in sorted(not_found_cities.items()):
            print(f"  - '{city}' (rows: {', '.join(map(str, rows[:5]))}{'...' if len(rows) > 5 else ''})")

    return stats, not_found_cities

def calculate_distances_for_csv(csv_path, output_path, city_db, reference_city="mumbai"):
    """
    Calculate distances from reference city for all companies.

    Args:
        csv_path: Input CSV file
        output_path: Output CSV file
        city_db: City database
        reference_city: Reference city name (default: "mumbai")
    """
    # Find reference city coordinates
    ref_key, ref_data, _ = find_city_in_database(reference_city, city_db)

    if not ref_data:
        print(f"ERROR: Could not find reference city '{reference_city}' in database!")
        return

    ref_lat = ref_data['lat']
    ref_lon = ref_data['lon']

    print(f"\nReference city: {ref_key}")
    print(f"Coordinates: {ref_lat}, {ref_lon}")
    print(f"\nCalculating distances...")
    print("-" * 70)

    # Process CSV
    rows_processed = 0
    rows_with_distance = 0
    rows_without_distance = 0

    output_rows = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ['Distance (miles)', 'Distance (km)', 'Geocoded City', 'Match Type']

        for row in reader:
            rows_processed += 1
            city = row.get('City', '').strip()

            # Find city in database
            key, data, match_type = find_city_in_database(city, city_db)

            if data:
                # Calculate distance
                distance_miles = calculate_distance(
                    ref_lat, ref_lon,
                    data['lat'], data['lon']
                )
                distance_km = distance_miles * 1.60934

                row['Distance (miles)'] = f"{distance_miles:.1f}"
                row['Distance (km)'] = f"{distance_km:.1f}"
                row['Geocoded City'] = key
                row['Match Type'] = match_type

                rows_with_distance += 1
            else:
                row['Distance (miles)'] = 'N/A'
                row['Distance (km)'] = 'N/A'
                row['Geocoded City'] = ''
                row['Match Type'] = match_type

                rows_without_distance += 1

            output_rows.append(row)

    # Write output CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nProcessing complete!")
    print(f"  Total rows: {rows_processed}")
    print(f"  ✓ With distance: {rows_with_distance}")
    print(f"  ✗ Without distance: {rows_without_distance}")
    print(f"\nOutput written to: {output_path}")

    # Show some sample distances
    print(f"\nSample distances from {reference_city.title()}:")
    for i, row in enumerate(output_rows[:10]):
        city = row.get('City', '')
        dist_miles = row.get('Distance (miles)', 'N/A')
        dist_km = row.get('Distance (km)', 'N/A')
        geocoded = row.get('Geocoded City', '')

        if dist_miles != 'N/A':
            print(f"  {city:20} -> {dist_miles:>7} mi / {dist_km:>7} km  ({geocoded})")

def main():
    # Configuration
    csv_input = "A4A - WordCamp Asia 2026 - Sheet10.csv"
    csv_output = "WordCamp_Asia_2026_with_distances.csv"
    city_db_path = "in-cities5000.json"
    reference_city = "mumbai"

    print("=" * 70)
    print("WordCamp Asia 2026 - Distance Calculator")
    print("=" * 70)
    print()

    # Load city database
    print(f"Loading city database: {city_db_path}")
    city_db = load_city_database(city_db_path)
    print(f"  Loaded {len(city_db):,} cities")
    print()

    # Step 1: Verify cities
    stats, not_found = verify_and_clean_cities(csv_input, city_db)
    print()

    # Step 2: Calculate distances
    calculate_distances_for_csv(csv_input, csv_output, city_db, reference_city)

    print()
    print("=" * 70)
    print("Done!")
    print("=" * 70)

if __name__ == '__main__':
    main()
