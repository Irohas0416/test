import argparse
import os

def merge_turtle_files(base_file, patch_file, output_file):
    """Appends the generated patch file to the base knowledge graph."""
    
    # 1. Check if files exist
    if not os.path.exists(base_file):
        print(f"Error: Base file '{base_file}' not found.")
        return
    if not os.path.exists(patch_file):
        print(f"Error: Patch file '{patch_file}' not found.")
        return

    try:
        # 2. Read the base Knowledge Graph
        print(f"Reading base KG: {base_file}...")
        with open(base_file, 'r', encoding='utf-8') as f_base:
            base_content = f_base.read()

        # 3. Read the generated patches
        print(f"Reading patches: {patch_file}...")
        with open(patch_file, 'r', encoding='utf-8') as f_patch:
            patch_content = f_patch.read()

        # 4. Write both to the final output file
        print(f"Writing merged content to: {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write(base_content)
            
            # Add a visual separator so you can track what was added
            f_out.write("\n\n")
            f_out.write("# " + "="*50 + "\n")
            f_out.write("# AUTOMATED RAG COMPLETION PATCHES BELOW\n")
            f_out.write("# " + "="*50 + "\n\n")
            
            f_out.write(patch_content)
            
        print("\nSuccess! Your final Knowledge Graph is ready.")

    except Exception as e:
        print(f"An error occurred during the merge process: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge a base Turtle file with a patch Turtle file.")
    
    # Set default filenames based on your previous terminal output
    parser.add_argument("--base", default="ontology/KNE_knowledge_graph_v034.ttl", help="Path to the original KG.")
    parser.add_argument("--patch", default="ontology/KNE_ke_v5.ttl", help="Path to the generated patches.")
    parser.add_argument("--output", default="ontology/final_knowledge_graph.ttl", help="Path for the final merged file.")
    
    args = parser.parse_args()
    
    merge_turtle_files(args.base, args.patch, args.output)