import argparse
import requests
import re
from typing import List, Dict, Set

# Import required schema and functions
from tfl_api.functions import save_to_csv, get_tfl_modes, load_stations_csv

def build_master_zone_map(modes: Set[str]) -> Dict[str, int]:
    """
    Build a comprehensive dictionary mapping NaPTAN IDs to their respective TfL travel zones.
    Queries the Transport for London (TfL) API for the explicitly provided transport modes.
    """
    zone_map = {}
    
    # Return early if no modes are provided to avoid unnecessary API calls
    if not modes:
        print("No valid transport modes found to query. Skipping API call.")
        return zone_map
        
    modes_str = ",".join(modes)
    print(f"Fetching zone data for modes: {modes_str}...")
    
    url = f"https://api.tfl.gov.uk/StopPoint/Mode/{modes_str}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        stop_points = data.get('stopPoints', []) if isinstance(data, dict) else data
        
        for stop in stop_points:
            parent_id = stop.get('naptanId')
            station_zone = None
            
            # 1. Extract the travel zone from the additionalProperties array
            for prop in stop.get('additionalProperties', []):
                if prop.get('key', '').lower() == 'zone':
                    zone_str = str(prop.get('value', ''))
                    # Use regex to find the primary zone number (e.g., extracting 2 from '2/3')
                    match = re.search(r'\d+', zone_str)
                    if match:
                        station_zone = int(match.group())
                    break 
            
            # 2. Apply the extracted zone to the parent station and its children
            if station_zone is not None:
                if parent_id:
                    zone_map[parent_id] = station_zone
                
                for child in stop.get('children', []):
                    child_id = child.get('naptanId')
                    if child_id:
                        zone_map[child_id] = station_zone
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from TfL API: {e}")
        
    return zone_map


def main(args):
    """
    Primary execution function to read the CSV, filter modes, update zones, and save the output.
    """
    # Ensure proper file extensions
    input_file = args.input if args.input.endswith('.csv') else f"{args.input}.csv"
    output_file = args.output if args.output.endswith('.csv') else f"{args.output}.csv"
    
    print(f"Loading station data from {input_file}...")
    stations, unique_modes_in_csv = load_stations_csv(input_file)
    
    # Filter the modes using the configured translation function
    allowed_modes = set(get_tfl_modes(args.modes))
    
    # Isolate modes that are present in both the allowed list and the source CSV
    modes_to_query = unique_modes_in_csv.intersection(allowed_modes)
    
    print("Building the master zone map from the TfL API...")
    master_zone_map = build_master_zone_map(modes_to_query)
    
    print("Assigning zones to stations...")
    mapped_count = 0
    for station in stations:
        station.zone = master_zone_map.get(station.naptan_id, 0)
        if station.zone != 0:
            mapped_count += 1
            
    print(f"Successfully mapped zones for {mapped_count} out of {len(stations)} stations.")
        
    print(f"Saving updated data to '{output_file}'...")
    save_to_csv(stations, output_file)
    print("Station dataset successfully updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reads a TfL stations CSV, fetches zone data from the API, and saves an updated CSV."
    )
    
    parser.add_argument(
        "--input", 
        type=str, 
        default="stations.csv", 
        help="File path to the existing station data."
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="stations.csv", 
        help="File path where the updated data will be saved."
    )
    parser.add_argument(
        "--modes",
        type=str,
        default="toden",
        help="A string containing the initial letter of each transport mode to include (e.g., 'td' for Tube and DLR)."
    )
    
    parsed_args = parser.parse_args()
    main(parsed_args)