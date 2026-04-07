import os
import time
import argparse
from google import genai
from google.genai import types

    

def main(args):
    api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyCAThbtQng5E7RAtigtITQ3Q3GVEsGr9xQ")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        return

    client = genai.Client(api_key=api_key)
    
    # 1. Break the analysis down into individual, focused tasks
    completion_tasks = [
        "Create real-world instances for the Branch class (e.g., Northern Line's Charing Cross and Bank branches, District Line's Richmond and Ealing Broadway branches).",
        "Re-type the DLR weekend closure (disruption_0004) specifically as a TemporaryClosure rather than a generic ClosureEvent.",
        "Create instances linking lines or stations to lpt:frequencyMinutes, lpt:validDuring, and lpt:operatingHoursText using the FrequencyRecord and OperatingPeriod classes.",
        "Populate the hasConnection property by creating instances of the Connection class to model interchanges at stations.",
        "Connect National Rail services to stations (like Victoria) by creating RailService and Stop instances and using connectsToService.",
        "Consolidate multiple URIs for Canary Wharf (e.g., station_Canary_Wharf, station_Canary_Wharf_DLR) using owl:sameAs or by merging properties, and standardize the rdfs:label.",
        "Assign lpt:hasAccessibilityFeature to stations and explicitly type them as AccessibleStation, InterchangeStation, or TerminusStation where applicable.",
        "Create an instance of lpt:SevereDelay to ensure competency questions filtering for severe delays return valid results.",
        "Refactor nextStation / previousStation adjacency triples so they are scoped to specific lines. Remove global adjacency links that cross lines (e.g., King's Cross to Latimer Road)."
    ]

    # We will modify a copy of your KG so we don't accidentally ruin the original
    current_kg_path = args.output
    
    # Setup the initial checkpoint file by copying the base file
    with open(args.kg_file, 'r', encoding='utf-8') as src, open(current_kg_path, 'w', encoding='utf-8') as dst:
        dst.write(src.read())
        dst.write("\n\n# === AUTOMATED RAG PATCHES START HERE ===\n")

    print(f"Starting Iterative RAG Pipeline. Total tasks: {len(completion_tasks)}\n")

    # 2. Loop through each task one by one
    for index, task in enumerate(completion_tasks, 1):
        print("-" * 50)
        print(f"Executing Task {index}/{len(completion_tasks)}: {task[:60]}...")
        
        # Upload the CURRENT state of the KG (the checkpoint)
        try:
            uploaded_kg = client.files.upload(
                file=current_kg_path, 
                config={'mime_type': 'text/plain'}
            )
            while uploaded_kg.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_kg = client.files.get(name=uploaded_kg.name)
        except Exception as e:
            print(f"Failed to upload KG checkpoint: {e}")
            continue

        # Create a highly focused prompt for just this ONE task
        rag_prompt = f"""
        You are an expert Semantic Web and Knowledge Graph engineer. 
        Attached is our current Knowledge Graph in Turtle (.ttl) format. 
        
        TASK:
        {task}
        
        INSTRUCTIONS:
        - Write ONLY the exact missing RDF/Turtle triples required to resolve this specific task.
        - Use the prefixes already defined in the attached file.
        - Generate ONLY valid Turtle syntax (.ttl). Do not output markdown code blocks.
        - Do not output the entire file again. Only output the NEW triples.
        """

        try:
            response = client.models.generate_content(
                model="gemini-3.5-pro", # Using Pro for better reasoning
                contents=[uploaded_kg, rag_prompt],
                config=types.GenerateContentConfig(
                    system_instruction="You output perfectly formatted, syntactically valid Turtle code to patch Knowledge Graphs. No markdown formatting.",
                    temperature=0.2, 
                ),
            )

            # Clean the output just in case
            text_output = response.text
            if text_output.startswith("```turtle"):
                text_output = text_output.replace("```turtle", "", 1).replace("```", "")
            elif text_output.startswith("```"):
                text_output = text_output.replace("```", "", 2)

            # 3. Save the Checkpoint (Append directly to the active file)
            with open(current_kg_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Patch for Task {index}: {task[:40]}...\n")
                f.write(text_output.strip() + "\n")
            
            print(f"Task {index} complete! Patch appended to '{current_kg_path}'.")
            
            # Delete the file from Google's servers to free up space/quota before the next loop
            client.files.delete(name=uploaded_kg.name)
            
            # Sleep to respect free-tier rate limits
            print("Pausing for 10 seconds to respect API rate limits...")
            time.sleep(10)
            
        except Exception as e:
            print(f"Error during Task {index}: {e}")
            print("Skipping to next task...")

    print("\n" + "=" * 50)
    print(f"PIPELINE COMPLETE! Final updated KG saved to: {current_kg_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iteratively loop through completion tasks to patch a KG.")
    parser.add_argument("--kg_file", required=True, help="Path to your base knowledge graph file.")
    parser.add_argument("--output", default="ontology/final_iterative_kg.ttl", help="Output file that gets built over time.")
    
    args = parser.parse_args()
    main(args)