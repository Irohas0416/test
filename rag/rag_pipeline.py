import os
import time
import argparse
from google import genai
from google.genai import types

def get_api_client():
    """Initializes and returns the GenAI client."""
    api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyCAThbtQng5E7RAtigtITQ3Q3GVEsGr9xQ")
    if not api_key:
        raise ValueError("Error: GOOGLE_API_KEY environment variable not set.")
    return genai.Client(api_key=api_key)

def get_completion_tuples():
    """Returns the list of patching tasks and their corresponding data files."""
    tasks = [
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

    # Replace None with actual file paths as needed (e.g., 'data/branches.csv')
    data = [
        "", None, "", None, "", None, "", "", None, ""
    ]

    return list(zip(tasks, data))

def initialize_checkpoint(source_path, dest_path):
    """Copies the base KG file to the output path and adds a header."""
    with open(source_path, 'r', encoding='utf-8') as src, open(dest_path, 'w', encoding='utf-8') as dst:
        dst.write(src.read())
        dst.write("\n\n# === AUTOMATED RAG PATCHES START HERE ===\n")
    print(f"Initialized checkpoint at {dest_path}")

def upload_file(client, file_path, mime_type='text/plain'):
    """Uploads a file to GenAI and waits for it to finish processing."""
    if not file_path or not os.path.exists(file_path):
        return None
        
    print(f"Uploading {os.path.basename(file_path)}...")
    uploaded_file = client.files.upload(
        file=file_path, 
        config={'mime_type': mime_type}
    )
    
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)
        
    return uploaded_file

def generate_patch(client, uploaded_kg, uploaded_data, task):
    """Prompts the LLM to generate the RDF/Turtle patch using the KG and optional data."""
    rag_prompt = f"""
    You are an expert Semantic Web and Knowledge Graph engineer. 
    Attached is our current Knowledge Graph in Turtle (.ttl) format.
    """
    
    if uploaded_data:
        rag_prompt += "\nAlso attached is a supplementary data file to use as context for this task.\n"
        
    rag_prompt += f"""
    TASK:
    {task}
    
    INSTRUCTIONS:
    - Write ONLY the exact missing RDF/Turtle triples required to resolve this specific task.
    - Use the prefixes already defined in the attached file.
    - Generate ONLY valid Turtle syntax (.ttl). Do not output markdown code blocks.
    - Do not output the entire file again. Only output the NEW triples.
    """

    # Bundle the contents depending on whether data was uploaded
    contents = [uploaded_kg]
    if uploaded_data:
        contents.append(uploaded_data)
    contents.append(rag_prompt)

    response = client.models.generate_content(
        model="gemini-3.5-pro",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction="You output perfectly formatted, syntactically valid Turtle code to patch Knowledge Graphs. No markdown formatting.",
            temperature=0.2, 
        ),
    )
    return response.text

def clean_markdown(text_output):
    """Removes markdown code blocks from the LLM output."""
    if text_output.startswith("```turtle"):
        return text_output.replace("```turtle", "", 1).replace("```", "")
    elif text_output.startswith("```"):
        return text_output.replace("```", "", 2)
    return text_output

def append_patch(file_path, task_index, task_desc, patch_text):
    """Appends the generated patch to the checkpoint file."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"\n# Patch for Task {task_index}: {task_desc[:40]}...\n")
        f.write(patch_text.strip() + "\n")

def run_pipeline(client, tuples, base_kg_path, current_kg_path):
    """Orchestrates the entire task looping process."""
    initialize_checkpoint(base_kg_path, current_kg_path)
    print(f"Starting Iterative RAG Pipeline. Total tasks: {len(tuples)}\n")

    for index, (task, data_path) in enumerate(tuples, 1):
        print("-" * 50)
        print(f"Executing Task {index}/{len(tuples)}: {task[:60]}...")
        if data_path:
            print(f"Associated Data: {data_path}")
            
        uploaded_kg = None
        uploaded_data = None
        
        try:
            # 1. Upload Base KG
            uploaded_kg = upload_file(client, current_kg_path)
            
            # 2. Upload Task Data (if provided)
            if data_path:
                uploaded_data = upload_file(client, data_path)
            
            # 3. Generate
            print("Generating patch...")
            raw_output = generate_patch(client, uploaded_kg, uploaded_data, task)
            
            # 4. Clean
            cleaned_patch = clean_markdown(raw_output)
            
            # 5. Save
            append_patch(current_kg_path, index, task, cleaned_patch)
            print(f"Task {index} complete! Patch appended to '{current_kg_path}'.")
            
        except Exception as e:
            print(f"Error during Task {index}: {e}")
            print("Skipping to next task...")
            
        finally:
            # 6. Cleanup files from server
            print("Cleaning up uploaded files...")
            if uploaded_kg:
                client.files.delete(name=uploaded_kg.name)
            if uploaded_data:
                client.files.delete(name=uploaded_data.name)
                
            # 7. Respect Rate Limits
            print("Pausing for 10 seconds to respect API rate limits...")
            time.sleep(10)

    print("\n" + "=" * 50)
    print(f"PIPELINE COMPLETE! Final updated KG saved to: {current_kg_path}")

def main(args):
    tasks_with_data = get_completion_tuples()
    
    try:
        client = get_api_client()
        run_pipeline(client, tasks_with_data, args.kg_file, args.output)
    except ValueError as ve:
        print(ve)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iteratively loop through completion tasks to patch a KG.")
    parser.add_argument("--kg_file", required=True, help="Path to your base knowledge graph file.")
    parser.add_argument("--output", default="ontology/final_iterative_kg.ttl", help="Output file that gets built over time.")
    args = parser.parse_args()
    main(args)