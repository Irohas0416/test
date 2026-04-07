import argparse
import requests
import re
from typing import List

from schema.schema import NetworkTopologyCSVRow
from tfl_api.functions import save_to_csv, get_tfl_modes

def get_tfl_property(stop_point_json, key_name):
    """Finds values like 'Zone' or 'Step Free Access' inside the TfL list."""
    props = stop_point_json.get("additionalProperties", [])
    for p in props:
        if p.get("key") == key_name:
            return p.get("value")
    return None

def parse_zone_number(zone_val):
    """Extracts the first integer from a zone string (e.g., '2/3' -> 2)."""
    if not zone_val:
        return None
    match = re.search(r'\d+', str(zone_val))
    if match:
        return int(match.group())
    return None

def extract_detailed_topology(modes: List[str], output_file: str):
    all_records = []
    
    for mode in modes:
        print(f"--- Processing Mode: {mode} ---")
        line_url = f"https://api.tfl.gov.uk/Line/Mode/{mode}"
        line_res = requests.get(line_url)
        
        if line_res.status_code == 200:
            lines = line_res.json()
            
            for line in lines:
                line_id = line['id']
                line_name = line['name']
                print(f"Fetching sequences for {line_name}...")
                
                # Switch to the Route Sequence endpoint to get sequence and direction
                seq_url = f"https://api.tfl.gov.uk/Line/{line_id}/Route/Sequence/all"
                seq_res = requests.get(seq_url)
                
                if seq_res.status_code == 200:
                    seq_data = seq_res.json()
                    
                    # stopPointSequences holds the stations ordered by branch and direction
                    for sequence in seq_data.get("stopPointSequences", []):
                        direction = sequence.get("direction") # e.g., 'inbound', 'outbound'
                        
                        # Use enumerate to easily get the sequence_number (starting at 1)
                        for index, stop in enumerate(sequence.get("stopPoint", []), start=1):
                            
                            step_free_val = get_tfl_property(stop, "Step Free Access")
                            is_step_free = True if step_free_val == "full" else False

                            try:
                                record = NetworkTopologyCSVRow(
                                    station_name=stop.get("name", stop.get("commonName")),
                                    line_name=line_name,
                                    transport_mode=mode,
                                    operator_name="Transport for London",
                                    zone_number=parse_zone_number(get_tfl_property(stop, "Zone")),
                                    is_step_free_street_to_train=is_step_free,
                                    sequence_number=index,
                                    direction_name=direction
                                )
                                all_records.append(record)
                            except Exception as e:
                                print(f"  Skipping {stop.get('name', 'Unknown')}: {e}")

    return all_records

def main(args):
    output_file = args.output if args.output.endswith('.csv') else f"{args.output}.csv"
    modes_to_fetch = get_tfl_modes(args.modes)
    all_records = extract_detailed_topology(modes_to_fetch, output_file)
    save_to_csv(all_records, output_file)

if __name__ == "__main__":
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
        default="network_data.csv",
        help="The file path where the extracted station data will be saved."
    )
    parsed_args = parser.parse_args()
    main(parsed_args)