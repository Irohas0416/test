import argparse
import requests
from typing import List

# Import required schema and functions
from schema.schema import FareCSVRow
from tfl_api.functions import save_to_csv


def get_tfl_fares(zone_stations: dict) -> List[FareCSVRow]:
    """
    Fetches fare information across travel zones.
    Optimised to only calculate i -> j where i <= j to prevent duplicate reverse queries.
    """
    rows = []

    # Loop through TfL Travel Zones 1 to 9
    for from_zone in range(1, 10):
        
        # OPTIMISATION: Start the inner loop at 'from_zone' instead of 1.
        # This creates a triangular loop (1->1, 1->2... then 2->2, 2->3... etc.)
        for to_zone in range(from_zone, 10):

            # Always assign the first station in the list as the origin
            from_station = zone_stations[from_zone][0]

            # If the zones are identical, pick the SECOND station in the list for the destination
            # This prevents the API from returning empty when origin == destination
            if from_zone == to_zone:
                to_station = zone_stations[to_zone][1]
            else:
                to_station = zone_stations[to_zone][0]

            url = f"https://api.tfl.gov.uk/Stoppoint/{from_station}/FareTo/{to_station}"
    
            try:
                response = requests.get(url)
        
                if response.status_code == 404:
                    print(f"Error: Stations {from_station} or {to_station} not found.")
                    continue
            
                response.raise_for_status()
                data = response.json()
        
                if not data:
                    print(f"Warning: Empty fare data for Zone {from_zone} to {to_zone} ({from_station} to {to_station}).")
                    continue
        
                for journey in data:
                    for fare_row in journey.get('rows', []):
                        for ticket in fare_row.get('ticketsAvailable', []):
                            
                            # Safely extract the time type (Peak / Off Peak)
                            time_data = ticket.get('ticketTime', {})
                            time_str = time_data.get('type', '') if isinstance(time_data, dict) else str(time_data)
                            desc_str = ticket.get('description', 'Adult PAYG')
                            
                            row = FareCSVRow(
                                fare_product=f"{desc_str} - {time_str}".strip(" -"),
                                fare_amount=float(ticket.get('cost', 0.0)),
                                currency="GBP",
                                applies_from_zone=from_zone, 
                                applies_to_zone=to_zone
                            )
                            rows.append(row)
                
            except Exception as e:
                print(f"Request failed for Zone {from_zone} to {to_zone}: {e}")

    return rows


def main(args):
    # Dictionary mapping explicit Zone numbers (1-9) to a list of two distinct Hub NaPTAN IDs
    zone_stations = {
        1: ["940GZZLUCHX", "940GZZLUOXC"], # Charing Cross, Oxford Circus
        2: ["940GZZLUHPK", "940GZZLUSWC"], # Holland Park, Swiss Cottage
        3: ["940GZZLUEBY", "940GZZLUACT"], # Ealing Broadway, Acton Town
        4: ["940GZZLUBOS", "940GZZLUSNB"], # Boston Manor, Snaresbrook
        5: ["940GZZLUHWT", "940GZZLUSTM"], # Hounslow West, Stanmore
        6: ["940GZZLUHRC", "940GZZLUUXB"], # Heathrow T2&3, Uxbridge
        7: ["940GZZLUCXY", "940GZZLURKW"], # Croxley, Rickmansworth
        8: ["910GWATFDHS", "910GCHESHNT"], # FIX: Watford High Street, Cheshunt (Overground Hubs)
        9: ["940GZZLUAMS", "940GZZLUCSM"]  # Amersham, Chesham
    }

    # Ensure proper file extension
    output_file = args.output if args.output.endswith('.csv') else f"{args.output}.csv"

    print("Fetching TfL fare matrices...")
    fare_results = get_tfl_fares(zone_stations)

    if fare_results:
        print(f"\nSuccessfully retrieved {len(fare_results)} fare options:")
        print("-" * 55)
        for fare in fare_results[:5]:
            print(f"Product: {fare.fare_product:35} | Price: £{fare.fare_amount:.2f}")
    else:
        print("\nNo fares found. Ensure the API is accessible and Hub IDs are valid.")

    save_to_csv(fare_results, output_file)
    print(f"Successfully saved fare data to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and collate Transport for London (TfL) fare price matrices across zones."
    )

    parser.add_argument(
        "--output",
        type=str,
        default="fares.csv",
        help="The file path where the extracted fare data will be saved."
    )

    parsed_args = parser.parse_args()
    main(parsed_args)