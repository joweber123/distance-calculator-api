#!/usr/bin/env python3
"""
Convert GeoNames data to city database JSON format.

Usage:
    python convert_geonames_to_json.py IN/IN.txt in-cities5000.json
"""

import csv
import json
import sys

# Mapping of Indian state codes to names
# Source: GeoNames admin1CodesASCII.txt (downloaded 2026-02-13)
STATE_CODES = {
    '01': 'andaman and nicobar',
    '02': 'andhra pradesh',
    '03': 'assam',
    '05': 'chandigarh',
    '07': 'delhi',
    '09': 'gujarat',
    '10': 'haryana',
    '11': 'himachal pradesh',
    '12': 'jammu and kashmir',
    '13': 'kerala',
    '14': 'lakshadweep',
    '16': 'maharashtra',
    '17': 'manipur',
    '18': 'meghalaya',
    '19': 'karnataka',
    '20': 'nagaland',
    '21': 'odisha',
    '22': 'puducherry',
    '23': 'punjab',
    '24': 'rajasthan',
    '25': 'tamil nadu',
    '26': 'tripura',
    '28': 'west bengal',
    '29': 'sikkim',
    '30': 'arunachal pradesh',
    '31': 'mizoram',
    '33': 'goa',
    '34': 'bihar',
    '35': 'madhya pradesh',
    '36': 'uttar pradesh',
    '37': 'chhattisgarh',
    '38': 'jharkhand',
    '39': 'uttarakhand',
    '40': 'telangana',
    '41': 'ladakh',
    '52': 'dadra and nagar haveli and daman and diu'
}

def convert_geonames_to_json(input_file, output_file, min_population=5000):
    """
    Convert GeoNames txt to JSON format matching SDR Bridge city database.

    Args:
        input_file: Path to GeoNames .txt file
        output_file: Path to output JSON file
        min_population: Minimum population to include (default: 5000)
    """
    cities = {}
    skipped_no_pop = 0
    skipped_too_small = 0
    skipped_not_city = 0

    print(f"Reading {input_file}...")

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')

        for row in reader:
            # Skip if not enough columns
            if len(row) < 15:
                continue

            # Column indices:
            # 0: geonameid
            # 1: name
            # 2: asciiname
            # 4: latitude
            # 5: longitude
            # 6: feature_class
            # 7: feature_code
            # 10: admin1_code (state)
            # 14: population

            feature_class = row[6]

            # Only include populated places (P = city, village, etc.)
            if feature_class != 'P':
                skipped_not_city += 1
                continue

            # Get population
            try:
                population = int(row[14]) if row[14] else 0
            except ValueError:
                population = 0

            # Skip if no population data
            if population == 0:
                skipped_no_pop += 1
                continue

            # Skip if population too small
            if population < min_population:
                skipped_too_small += 1
                continue

            # Get location data
            city_name = row[2].lower()  # Use ASCII name for compatibility
            admin1_code = row[10]

            # Map state code to name
            state_name = STATE_CODES.get(admin1_code, '').lower()

            try:
                lat = float(row[4])
                lon = float(row[5])
            except ValueError:
                continue

            # Create key in format: "city,state,country"
            key = f"{city_name},{state_name},india"

            # If duplicate, keep the one with higher population
            if key in cities:
                if population > cities[key]['population']:
                    cities[key] = {
                        "lat": lat,
                        "lon": lon,
                        "population": population
                    }
            else:
                cities[key] = {
                    "lat": lat,
                    "lon": lon,
                    "population": population
                }

    # Save to JSON
    print(f"Writing {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cities, f, indent=2, ensure_ascii=False)

    # Print statistics
    print(f"\nConversion complete!")
    print(f"  Total cities included: {len(cities)}")
    print(f"  Minimum population: {min_population}")
    print(f"\nSkipped:")
    print(f"  Not a populated place: {skipped_not_city:,}")
    print(f"  No population data: {skipped_no_pop:,}")
    print(f"  Population < {min_population}: {skipped_too_small:,}")

    # Show sample entries
    print(f"\nSample entries:")
    for i, (key, data) in enumerate(list(cities.items())[:5]):
        print(f"  {key}: lat={data['lat']}, lon={data['lon']}, pop={data['population']:,}")
        if i >= 4:
            break

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert_geonames_to_json.py <input_file> <output_file> [min_population]")
        print("\nExample:")
        print("  python convert_geonames_to_json.py IN/IN.txt in-cities5000.json 5000")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    min_population = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

    convert_geonames_to_json(input_file, output_file, min_population)
