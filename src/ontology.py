import rdflib
from rdflib.namespace import RDF, OWL, RDFS
import re

import os

def extract_ontology_keywords(ontology_file):
    """Reads a Turtle/OWL ontology and extracts a list of domain keywords."""
    g = rdflib.Graph()
    g.parse(ontology_file, format="turtle")
    
    keywords = set()
    
    # Extract Subjects (Classes, Properties, Individuals)
    for s, p, o in g:
        # Get the actual name from the URI (e.g., http://example.org/lpt-ontology#FareZone -> FareZone)
        uri_name = s.split('#')[-1] if '#' in s else s.split('/')[-1]
        
        # Split CamelCase into separate words (e.g., 'FareZone' -> 'Fare', 'Zone')
        words = re.sub('([A-Z])', r' \1', uri_name).split()
        for word in words:
            if len(word) > 2: # Ignore tiny words
                keywords.add(word.lower())

    # Add specific terms we know are critical based on your ontology file
    custom_terms = ['tube', 'line', 'interchange', 'delay', 'closure', 'route', 'terminus']
    keywords.update(custom_terms)
    
    return list(keywords)


if __name__ == "__main__":
    # 1. Get the exact path of the folder this script is in (the 'src' folder)
    current_folder = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Build the path: go up one level (".."), into "ontology", to the file
    file_path = os.path.join(current_folder, "..", "ontology", "KNE_ontology_v0.2")
    
    # 3. Clean up the path so it looks nice (removes the "..")
    file_path = os.path.normpath(file_path)
    
    print(f"Looking for ontology file at: {file_path}")
    print(extract_ontology_keywords(file_path))