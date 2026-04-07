import os
import time
import argparse
from google import genai
from google.genai import types

def wait_for_processing(client, uploaded_file):
    """Helper function to wait for documents/PDFs to process on Google's servers."""
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)
    return uploaded_file

def main(args):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        return

    client = genai.Client(api_key=api_key)
    
    # 1. The Task Array with FILE PATHS
    # Replace these dummy paths with the actual paths to your raw data files
    rag_instructions = [
        {
            "task": "Create real-world instances for the Branch class.",
            "data_file": "raw_data/branch_data.csv" 
        },
        {
            "task": "Re-type the DLR weekend closure specifically as a TemporaryClosure.",
            "data_file": "raw_data/weekend_closures.json"
        },
        # Add the rest of your tasks and their corresponding data files here...
    ]

    current_kg_path = args.output
    
    # Setup the initial checkpoint file
    with open(args.kg_file, 'r', encoding='utf-8') as src, open(current_kg_path, 'w', encoding='utf-8') as dst:
        dst.write(src.read())
        dst.write("\n\n# === AUTOMATED RAG PATCHES START HERE ===\n")

    print(f"Starting File-Based RAG Pipeline. Total tasks: {len(rag_instructions)}\n")

    # 2. Loop through each task
    for index, item in enumerate(rag_instructions, 1):
        task_desc = item["task"]
        data_file_path = item["data_file"]
        
        print("-" * 60)
        print(f"Executing Task {index}/{len(rag_instructions)}:")
        print(f"Goal: {task_desc[:60]}...")
        
        # Verify the data file actually exists before wasting API calls
        if not os.path.exists(data_file_path):
            print(f"-> ERROR: Data file '{data_file_path}' not found! Skipping task...")
            continue

        uploaded_kg = None
        uploaded_data = None
        
        try:
            # Upload 1: The current Knowledge Graph
            print(f"-> Uploading Knowledge Graph checkpoint...")
            uploaded_kg = client.files.upload(
                file=current_kg_path, 
                config={'mime_type': 'text/plain'}
            )
            uploaded_kg = wait_for_processing(client, uploaded_kg)

            # Upload 2: The actual raw data file for this specific task
            print(f"-> Uploading Raw Data file: {data_file_path}...")
            uploaded_data = client.files.upload(file=data_file_path)
            uploaded_data = wait_for_processing(client, uploaded_data)
            
        except Exception as e:
            print(f"-> Failed to upload files: {e}")
            continue

        # Formulate prompt instructing it to use BOTH attached files
        rag_prompt = f"""
        You are an expert Semantic Web and Knowledge Graph engineer. 
        
        I have attached TWO files:
        1. A Knowledge Graph in Turtle (.ttl) format (This contains the ontology rules and existing instances).
        2. A raw data file (This contains the ground-truth facts).
        
        TASK:
        {task_desc}
        
        INSTRUCTIONS:
        - Read the raw data file. Do NOT hallucinate data. Only use facts found in the attached data file.
        - Map those facts to the ontology found in the attached Knowledge Graph file.
        - Write ONLY the exact missing RDF/Turtle triples required to resolve this specific task.
        - Use the prefixes already defined in the Knowledge Graph.
        - Generate ONLY valid Turtle syntax (.ttl). Do not output markdown code blocks.
        - Do not output the entire KG file again. Only output the NEW triples.
        """

        # 3. Robust API Call with Retries and Backoff Delay
        max_retries = 3
        base_delay = 15 

        for attempt in range(max_retries):
            try:
                # Notice we pass BOTH uploaded_kg and uploaded_data into the contents array
                response = client.models.generate_content(
                    model="gemini-3.5-pro", 
                    contents=[uploaded_kg, uploaded_data, rag_prompt],
                    config=types.GenerateContentConfig(
                        system_instruction="You output perfectly formatted, syntactically valid Turtle code to patch Knowledge Graphs. No markdown formatting.",
                        temperature=0.0, 
                    ),
                )

                # Clean output
                text_output = response.text
                if text_output.startswith("```turtle"):
                    text_output = text_output.replace("```turtle", "", 1).replace("```", "")
                elif text_output.startswith("```"):
                    text_output = text_output.replace("```", "", 2)

                # Save the Checkpoint
                with open(current_kg_path, "a", encoding="utf-8") as f:
                    f.write(f"\n# Patch for Task {index}: {task_desc[:40]}...\n")
                    f.write(text_output.strip() + "\n")
                
                print(f"-> Success! Patch appended to '{current_kg_path}'.")
                break 

            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "quota" in error_msg:
                    sleep_time = base_delay * (attempt + 1)
                    print(f"-> Rate limit hit (Attempt {attempt+1}/{max_retries}). Pausing for {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    print(f"-> Error during Task {index}: {e}")
                    break 
        
        # 4. Crucial Cleanup: Delete BOTH files from Google's servers
        print("-> Cleaning up uploaded files...")
        try:
            if uploaded_kg: client.files.delete(name=uploaded_kg.name)
            if uploaded_data: client.files.delete(name=uploaded_data.name)
        except:
            pass
            
        # Standard delay
        if index < len(rag_instructions):
            print("-> Pausing for 10 seconds before next task...")
            time.sleep(10)

    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE! Final updated KG saved to: {current_kg_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iteratively patch a KG using explicit raw data files.")
    parser.add_argument("--kg_file", required=True, help="Path to your base knowledge graph file.")
    parser.add_argument("--output", default="ontology/final_iterative_kg.ttl", help="Output file that gets built over time.")
    
    args = parser.parse_args()
    main(args)