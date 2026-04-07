import requests
from typing import List

def get_all_tfl_modes() -> List[str]:
    """
    Fetches all available transport modes from the TfL API.
    Returns a list of strings representing valid mode names.
    """
    url = "https://api.tfl.gov.uk/Line/Meta/Modes"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # We extract 'modeName' from each object in the response
        # Examples: 'tube', 'bus', 'elizabeth-line', 'cycle', etc.
        modes = [mode_info.get('modeName') for mode_info in data if 'modeName' in mode_info]
        return modes

    except Exception as e:
        print(f"Error fetching modes: {e}")
        return []

# Example Usage
if __name__ == "__main__":
    available_modes = get_all_tfl_modes()
    
    print(f"Total modes found: {len(available_modes)}")
    for mode in available_modes:
        print(mode)
    
    # You can now use this to get status for EVERYTHING
    # status_data = get_tfl_service_status(modes=available_modes)