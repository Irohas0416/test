import argparse
import requests
from typing import List, Dict

# Assuming these are imported from your local project files
from schema.schema import StationCSVRow
from tfl_api.functions import get_tfl_modes, save_to_csv

def get_tfl_stations(modes: List[str]) -> List[StationCSVRow]:
    """
    Iterates through a list of transport modes, fetches station data from the 
    TfL API, and collates them, removing any duplicates by their common name.
    
    Args:
        modes (List[str]): A list of TfL transport modes (e.g., 'tube', 'dlr').
        
    Returns:
        List[StationCSVRow]: A clean, deduplicated list of station records.
    """
    # Dictionary to store unique stations, using the STATION NAME as the key
    unique_stations: Dict[str, StationCSVRow] = {}

    for mode in modes:
        print(f"Fetching data for transport mode: {mode}...")
        url = f"https://api.tfl.gov.uk/StopPoint/Mode/{mode}"
        
        try:
            response = requests.get(url)
            # Raise an HTTPError if the HTTP request returned an unsuccessful status code
            response.raise_for_status()
            data = response.json()
            
            # TfL sometimes returns a dictionary with a 'stopPoints' key, or a direct list
            stop_points = data.get('stopPoints', []) if isinstance(data, dict) else data
            
            for stop in stop_points:
                naptan_id = stop.get('naptanId', 'Unknown')
                
                # Exclude HUB stations 
                if naptan_id.startswith("HUB"):
                    continue

                # Clean up the station name for better readability
                clean_name = stop.get('commonName', 'Unknown').replace(" Underground Station", "")
                fetched_modes = set(stop.get('modes', []))
                
                # If the station name is already in our dictionary, merge the transport modes
                if clean_name in unique_stations:
                    # Split the existing modes, combine with new modes (union), and save back
                    existing_modes = set(unique_stations[clean_name].modes.split(", "))
                    merged_modes = existing_modes.union(fetched_modes)
                    unique_stations[clean_name].modes = ", ".join(sorted(merged_modes))
                else:
                    # Create a new station record and add it to the dictionary
                    # This guarantees we only keep the first one we encounter
                    unique_stations[clean_name] = StationCSVRow(
                        naptan_id=naptan_id,
                        station_name=clean_name,
                        modes=", ".join(sorted(fetched_modes)),
                        lat=stop.get('lat'),
                        lon=stop.get('lon')
                    )
                    
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stations for {mode}: {e}")
            
    # Convert the dictionary values back into a standard list before returning
    return list(unique_stations.values())


def main(args):
    """
    Main function to drive the data extraction and saving process.
    """
    # Parse the user-defined modes using your helper function
    modes_to_fetch = get_tfl_modes(args.modes)

    print("Starting TfL station extraction...\n" + "-" * 40)
    all_stations = get_tfl_stations(modes_to_fetch)

    output = args.output if args.output.endswith('.csv') else f"{args.output}.csv"

    # Save the collated data to the specified file
    save_to_csv(all_stations, output)
    print(f"Successfully saved station data to {output}")


if __name__ == "__main__":
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Fetch and collate Transport for London (TfL) station data."
    )

    parser.add_argument(
        "--modes",
        type=str,
        default="toden",
        help="A string containing the first letter of each mode (e.g., 'td' for Tube and DLR)."
    )

    parser.add_argument(
        "--output",
        type=str,
        default="stations.csv",
        help="The file path where the extracted station data will be saved."
    )

    # Parse arguments and pass them to the main function
    parsed_args = parser.parse_args()
    main(parsed_args)