import argparse
import requests
from typing import List
from schema.schema import ServiceStatusCSVRow
from tfl_api.functions import get_tfl_modes, save_to_csv


def get_tfl_service_status(modes: List[str] = ["tube", "overground", "dlr", "elizabeth-line", "national-rail"]) -> List[ServiceStatusCSVRow]:
    url = f"https://api.tfl.gov.uk/Line/Mode/{','.join(modes)}/Status"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        rows = []
        for line in data:
            for status in line.get('lineStatuses', []):
                
                # FIX: Safely handle the list of validity periods
                validity_list = status.get('validityPeriods', [])
                validity = validity_list[0] if validity_list else {}
                
                row = ServiceStatusCSVRow(
                    affected_entity=line.get('name'),
                    status_text=status.get('statusSeverityDescription'),
                    severity_level=status.get('statusSeverity'),
                    closure_reason=status.get('reason'),

                    # Safely parse dates only if they exist
                    start_date=validity.get('fromDate')[:10] if validity.get('fromDate') else None,
                    end_date=validity.get('toDate')[:10] if validity.get('toDate') else None
                )
                rows.append(row)
        
        return rows

    except Exception as e:
        # This will now catch actual request errors, not index errors
        print(f"Error processing data: {e}")
        return []


def main(args):
    """
    Main function to drive the data extraction and saving process.
    """
    modes_to_fetch = get_tfl_modes(args.modes)

    results = get_tfl_service_status(modes_to_fetch)

    output = args.output if args.output.endswith('.csv') else f"{args.output}.csv"

    save_to_csv(results, output)
    print(f"Successfully saved status data to {output}")



if __name__ == "__main__":
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Fetch and collate Transport for London (TfL) status data."
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
        default="status.csv",
        help="The file path where the extracted station data will be saved."
    )

    # Parse arguments and pass them to the main function
    parsed_args = parser.parse_args()
    main(parsed_args)