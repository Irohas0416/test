import os
import csv
from typing import List, Set
from pydantic import BaseModel

from schema.schema import StationCSVRow




def save_to_csv(records: List[BaseModel], filename: str):
    """
    Saves ANY list of Pydantic BaseModel objects to a CSV file inside the 'data' folder.
    Extracts columns dynamically based on the specific model passed to it.
    """
    if not records:
        print(f"No data to save for {filename}.")
        return

    # Ensure the 'data' directory exists
    os.makedirs("data", exist_ok=True)
    filepath = os.path.join("data", filename)

    # Dynamically grab the headers from the first record in the list
    headers = list(records[0].model_dump().keys())

    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            
            # Write each Pydantic model as a dictionary row
            for record in records:
                writer.writerow(record.model_dump())
                
        print(f"Success! Saved {len(records)} records to '{filepath}'.")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def load_stations_csv(input_file: str) -> List[StationCSVRow]:
    """
    Loads a CSV file into a list of StationCSVRow objects.
    """
    stations: List[StationCSVRow] = []
    unique_modes_in_csv: Set[str] = set()
    
    print(f"1. Reading existing station data from '{input_file}'...")
    
    try:
        with open(input_file, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                # Extract all modes present in the CSV
                row_modes = [m.strip() for m in row.get('modes', '').split(',') if m.strip()]
                unique_modes_in_csv.update(row_modes)
                
                # Reconstruct the StationCSVRow object
                station = StationCSVRow(
                    naptan_id=row['naptan_id'],
                    station_name=row['station_name'],
                    modes=row['modes'],
                    lat=float(row['lat']) if row.get('lat') else None,
                    lon=float(row['lon']) if row.get('lon') else None,
                    zone=None
                )
                stations.append(station)
                
    except FileNotFoundError:
        print(f"Error: Could not find the file '{input_file}'. Please check the path.")
        return
    except KeyError as e:
        print(f"Error: Missing column {e} in your CSV. Ensure headers match the schema.")
        return
    
    return stations, unique_modes_in_csv




def get_tfl_modes(mode_string: str) -> List[str]:
    """
    Returns an array of modes, from the string passed in.
    """
    modes = ["tube", "overground", "dlr", "elizabeth-line", "national-rail"]
    modes_to_fetch = []

    if mode_string:
        if "t" in mode_string:
            modes_to_fetch.append("tube")
        if "o" in mode_string:
            modes_to_fetch.append("overground")
        if "d" in mode_string:
            modes_to_fetch.append("dlr")
        if "e" in mode_string:
            modes_to_fetch.append("elizabeth-line")
        if "n" in mode_string:
            modes_to_fetch.append("national-rail")
    else:
        modes_to_fetch = modes

    return modes_to_fetch
    

