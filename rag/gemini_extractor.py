import os
import time
import argparse
import tempfile
import queue
import concurrent.futures
import pandas as pd
from typing import List, Type
from pydantic import BaseModel, Field, create_model

# NEW Gemini SDK Imports
from google import genai
from google.genai import types

# Import your split function
from src.split_pdf import split_pdf

# Import all schemas from your local file
from schema.schema import *

# =========================================================================
# DYNAMIC WRAPPER
# =========================================================================

def create_list_wrapper(schema_class: Type[BaseModel]) -> Type[BaseModel]:
    """Dynamically creates a Pydantic model that holds a list of the target schema."""
    return create_model(
        f"{schema_class.__name__}Data",
        records=(List[schema_class], Field(description=f"A list of {schema_class.__name__} records explicitly mentioned in the text."))
    )

# =========================================================================
# RETRY LOGIC (EXPONENTIAL BACKOFF)
# =========================================================================

class QuotaExhaustedError(RuntimeError):
    pass


def generate_with_retry(client, uploaded_file, extraction_prompt, TargetWrapperClass, max_retries=5):
    """Attempts to generate content, retrying automatically if the API is busy/fails."""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview", # You can also try "gemini-1.5-pro" here if you need a larger context window
                contents=[
                    uploaded_file, 
                    extraction_prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction="You are an elite data extraction system designed for flawless, exhaustive document processing. Your objective is zero-data-loss extraction.",
                    response_mime_type="application/json",
                    response_schema=TargetWrapperClass,
                    temperature=0, 
                ),
            )
            return response # Success! Return the response.
            
        except Exception as e:
            print(f"\n[!] API Error on attempt {attempt + 1}/{max_retries}: {e}")
            # Quota exhausted / billing issue: retrying is usually pointless and wastes time.
            # Fail fast so the caller can record a clear performance failure reason.
            msg = str(e)
            if "429" in msg and "RESOURCE_EXHAUSTED" in msg and "exceeded your current quota" in msg.lower():
                raise QuotaExhaustedError(f"Gemini API quota exhausted (429 RESOURCE_EXHAUSTED): {msg}") from e
            if attempt < max_retries - 1:
                # Wait 5s, then 10s, then 20s, etc.
                sleep_time = (2 ** attempt) * 5 
                print(f"[*] Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print("[-] Max retries reached. Skipping this chunk to continue the rest.")
                return None

# =========================================================================
# WORKER FUNCTION FOR PARALLEL PROCESSING
# =========================================================================

def process_single_chunk(file_path, client_queue, extraction_prompt, TargetWrapperClass, schema_name):
    """Worker function that handles a single file chunk using an available client."""
    # 1. Grab an available client from the queue
    client = client_queue.get()
    
    try:
        print(f"[*] Thread starting upload for: {os.path.basename(file_path)}")
        uploaded_file = client.files.upload(file=file_path)
        
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = client.files.get(name=uploaded_file.name)
            
        # 2. Generate with Retry Logic
        response = generate_with_retry(client, uploaded_file, extraction_prompt, TargetWrapperClass)
        
        # 3. Parse Data
        if response and response.parsed and response.parsed.records:
            return [record.model_dump() for record in response.parsed.records]
        return []
        
    except QuotaExhaustedError:
        # Bubble up to stop the whole run quickly; caller will handle cancellation.
        raise
    except Exception as e:
        print(f"[-] Failed processing chunk {file_path}: {e}")
        return []
        
    finally:
        # 4. CRITICAL: Always put the client back in the queue for the next thread
        client_queue.put(client)

# =========================================================================
# CORE LOGIC
# =========================================================================

def main(args):
    # Set your dual API keys here
    api_key_1 = os.environ.get("GOOGLE_API_KEY_1", "AIzaSyAw3VoHZLyWoO0lQP0hwkrhU91Ue5Bbrb0")
    api_key_2 = os.environ.get("GOOGLE_API_KEY_2", "AIzaSyACz7o-44dKOCygdl5dtF4webHpJWojP4A")

    input_file_path = args.input
    schema_name = args.schema
    output_csv_path = args.output

    # Validate Schema
    TargetSchema = globals().get(schema_name)
    if not TargetSchema or not issubclass(TargetSchema, BaseModel):
        print(f"Error: Unknown or invalid schema '{schema_name}'.")
        return

    TargetWrapperClass = create_list_wrapper(TargetSchema)
    
    extraction_prompt = f"""
    Analyze the attached document carefully and extract EVERY SINGLE record that matches the '{schema_name}' structure.
    
    CRITICAL INSTRUCTIONS:
    1. EXHAUSTIVE EXTRACTION: You must find and extract *all* valid instances. Do not stop early. Do not summarize. Do not skip items.
    2. SYSTEMATIC SCANNING: Read through the document carefully, ensuring absolutely nothing is missed.
    3. STRICT ACCURACY: Only extract information explicitly mentioned in the text.
    """

    # ---------------------------------------------------------------------
    # 1. FILE PREPARATION (CHUNKING)
    # ---------------------------------------------------------------------
    files_to_process = []
    
    temp_dir_context = tempfile.TemporaryDirectory()
    temp_dir = temp_dir_context.name

    if input_file_path.lower().endswith('.pdf'):
        print(f"[*] PDF detected. Splitting '{input_file_path}' into chunks...")
        try:
            # INCREASED CHUNK SIZE TO 50: Fewer chunks, faster processing, stays within token limits
            split_pdf(input_file_path, temp_dir, chunk_size=50) 
            chunk_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.pdf')])
            files_to_process = [os.path.join(temp_dir, f) for f in chunk_files]
            print(f"[*] Successfully split into {len(files_to_process)} chunks of up to 50 pages each.")
        except Exception as e:
            print(f"Error splitting PDF: {e}")
            return
    else:
        files_to_process = [input_file_path]

    # ---------------------------------------------------------------------
    # 2. SETUP CLIENT QUEUE & PARALLEL ENVIRONMENT
    # ---------------------------------------------------------------------
    client_queue = queue.Queue()
    client_queue.put(genai.Client(api_key=api_key_1))
    
    if args.parallel:
        print("[*] Parallel mode activated. Initializing dual clients...")
        client_queue.put(genai.Client(api_key=api_key_2))
        max_workers = 2
    else:
        max_workers = 1

    # ---------------------------------------------------------------------
    # 3. PROCESSING LOOP (ORDERED EVALUATION WITH EARLY EXIT)
    # ---------------------------------------------------------------------
    append_mode = args.append
    total_extracted = 0
    found_data_yet = False # Tracks if we have hit the actual tables yet

    print(f"\n[*] Starting extraction with {max_workers} worker(s)...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        
        # Submit all chunks to the executor, keeping their original page order
        futures_with_files = []
        for file_path in files_to_process:
            future = executor.submit(
                process_single_chunk, 
                file_path, 
                client_queue, 
                extraction_prompt, 
                TargetWrapperClass, 
                schema_name
            )
            futures_with_files.append((future, file_path))

        # Evaluate the results in exact page order
        for future, file_path in futures_with_files:
            chunk_name = os.path.basename(file_path)
            
            try:
                # This blocks until THIS specific chunk finishes, keeping output strictly ordered
                data_dicts = future.result() 
                
                if data_dicts:
                    found_data_yet = True # We found the tables!
                    df = pd.DataFrame(data_dicts)
                    chunk_total = len(data_dicts)
                    total_extracted += chunk_total
                    
                    if append_mode or os.path.exists(output_csv_path):
                        df.to_csv(output_csv_path, mode='a', index=False, header=False)
                        print(f"[+] Appended {chunk_total} records from {chunk_name}.")
                    else:
                        df.to_csv(output_csv_path, mode='w', index=False, header=True)
                        print(f"[+] Created file with {chunk_total} records from {chunk_name}.")
                        append_mode = True 
                
                else:
                    print(f"[-] No valid records found in {chunk_name}.")
                    
                    # EARLY EXIT TRIGGER: If we already found data in previous pages, but THIS page is empty
                    if found_data_yet:
                        print(f"\n[!] End of data tables detected. Canceling remaining chunks to save API calls...")
                        # Cancel any remaining chunks in the queue that haven't started yet
                        for f, _ in futures_with_files:
                            f.cancel()
                        break # Break out of the loop completely

            except QuotaExhaustedError as exc:
                print(f"[-] Quota exhausted while processing {chunk_name}: {exc}")
                for f, _ in futures_with_files:
                    f.cancel()
                raise
            except Exception as exc:
                print(f"[-] {chunk_name} generated an exception: {exc}")

    # Cleanup temporary directory
    temp_dir_context.cleanup()
    
    # Avoid emoji to prevent Windows console encoding issues (e.g., gbk)
    print(f"\nDONE! Finished processing. Total records extracted: {total_extracted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload any file to Gemini and extract structured data to CSV.")
    parser.add_argument("--input", required=True, help="Path to the input file (JSON, TXT, CSV, PDF, etc.).")
    parser.add_argument("--output", required=True, help="Path to the output CSV file.")
    parser.add_argument("--schema", required=True, help="The name of the Pydantic schema to extract.")
    parser.add_argument("--append", action="store_true", help="Append data to the output CSV if it already exists.")
    parser.add_argument("--parallel", action="store_true", help="Use dual API keys to process chunks in parallel to save time.")
    
    args = parser.parse_args()
    main(args)