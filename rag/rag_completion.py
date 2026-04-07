import os
import time
import argparse
from google import genai
from google.genai import types

def main(args):
    # Ensure your API key is set in your environment variables
    # e.g., export GOOGLE_API_KEY="your_api_key"
    api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyCAThbtQng5E7RAtigtITQ3Q3GVEsGr9xQ")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        return

    # Initialize the Gemini Client
    client = genai.Client(api_key=api_key)
    
    # 1. Upload the base Knowledge Graph (Retrieval Context)
    print(f"Uploading Knowledge Graph '{args.kg_file}' to Gemini...")
    try:
        uploaded_kg = client.files.upload(
            file=args.kg_file, 
            config={'mime_type': 'text/plain'}
        )
        print(f"File uploaded successfully! Name: {uploaded_kg.name}")
        
        while uploaded_kg.state.name == "PROCESSING":
            print("Waiting for KG processing to complete...")
            time.sleep(2)
            uploaded_kg = client.files.get(name=uploaded_kg.name)
            
    except Exception as e:
        print(f"Failed to upload KG to Gemini: {e}")
        return

    # 2. Define the Completion Analysis (The Gaps)
    # This directly uses the analysis you provided to instruct the LLM on what is missing.
    completion_analysis = """
    We have identified several incomplete elements in our ontology and instance data that need to be resolved:

    Incomplete Ontology Elements:
    1. Branch class: Needs real-world instances (e.g., Northern Line's Charing Cross/Bank branches, District Line's Richmond/Ealing Broadway branches).
    2. TemporaryClosure / PermanentClosure subclasses: The DLR weekend closure (disruption_0004) needs to be re-typed specifically as a TemporaryClosure rather than a generic ClosureEvent.
    3. FrequencyRecord and OperatingPeriod classes: Need instances linking lines/stations to lpt:frequencyMinutes, lpt:validDuring, and lpt:operatingHoursText.
    4. Connection class: Needs instances populating the hasConnection property to model interchanges at stations.
    5. RailService and Stop classes: Connect National Rail services to stations (e.g., Victoria) using connectsToService.

    Incomplete Instance Elements:
    1. Duplicate/inconsistent labels: Consolidate multiple URIs (e.g., station_Canary_Wharf, station_Canary_Wharf_DLR) using owl:sameAs or by merging properties, and standardize rdfs:label.
    2. Missing accessibility: Assign lpt:hasAccessibilityFeature to stations and type them as AccessibleStation, InterchangeStation, or TerminusStation where applicable.
    3. Severe delays missing: Create an instance of lpt:SevereDelay to satisfy competency questions filtering for severe delays.
    4. Incorrect nextStation / previousStation: Refactor adjacency triples to be scoped to specific lines, removing global adjacency links that cross lines (e.g., King's Cross to Latimer Road).
    """

    # 3. Formulate the RAG Prompt
    rag_prompt = f"""
    You are an expert Semantic Web and Knowledge Graph engineer. 
    Attached is our current Knowledge Graph in Turtle (.ttl) format. 
    
    Based on the following Completion Analysis:
    {completion_analysis}
    
    TASK:
    Write the exact missing RDF/Turtle triples required to resolve these gaps. 
    - Use the prefixes already defined in the attached file.
    - Generate ONLY valid Turtle syntax (.ttl).
    - Do not include explanatory text outside of the Turtle code block. Use standard RDF comments (#) if explanations are needed.
    """

    print("Executing Gemini RAG completion request...")
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Using Pro for complex reasoning and coding
            contents=[
                uploaded_kg, 
                rag_prompt
            ],
            config=types.GenerateContentConfig(
                system_instruction="You are a strict RDF/Turtle generation engine. You output perfectly formatted, syntactically valid Turtle code to patch Knowledge Graphs.",
                temperature=0.2, # Low temperature for deterministic code generation
            ),
        )

        # 4. Save the generated patches
        output_file = args.output
        with open(output_file, "w", encoding="utf-8") as f:
            # Strip markdown formatting if the model wraps it in ```turtle
            text_output = response.text
            if text_output.startswith("```turtle"):
                text_output = text_output.replace("```turtle", "", 1).replace("```", "")
            f.write(text_output.strip())
            
        print(f"\nSuccess! Generated RDF patches saved to '{output_file}'.")
        print("Review the generated file and append it to your main knowledge graph.")
            
    except Exception as e:
        print(f"An error occurred during the Gemini API call: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Use Gemini RAG to complete missing Knowledge Graph elements.")
    parser.add_argument("--kg_file", required=True, help="Path to your current knowledge graph file (e.g., base_kg.ttl).")
    parser.add_argument("--output", default="kg_patches.ttl", help="Output file for the generated Turtle patches.")
    
    args = parser.parse_args()
    main(args)