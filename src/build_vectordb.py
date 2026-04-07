import json
import chromadb
import os

def load_data(json_file_path):
    """Loads the scraped JSON data."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_vector_database(data, db_folder="cache/chroma_db"):
    """
    Takes the nested JSON data, flattens it into text chunks, 
    and embeds it into a local vector database.
    """
    # 1. Initialize a persistent database on your hard drive
    os.makedirs(db_folder, exist_ok=True)
    client = chromadb.PersistentClient(path=db_folder)
    
    # 2. Create or load a "collection" (like a table in SQL)
    collection = client.get_or_create_collection(name="london_transport_kb")
    
    # If the database already has data, we can skip embedding
    if collection.count() > 0:
        print(f"Database already exists with {collection.count()} chunks. Ready to query!")
        return collection

    documents = []
    metadatas = []
    ids = []
    
    chunk_id = 0
    
    print("Flattening JSON into chunks...")
    for doc in data:
        url = doc.get("__id", "Unknown URL")
        content_dict = doc.get("content", {})
        
        for title, paragraphs in content_dict.items():
            # Skip empty sections (e.g., "References": [])
            if not paragraphs:
                continue
                
            # Combine all paragraphs under a single title to give the Vector DB good context
            combined_text = "\n".join(paragraphs)
            
            documents.append(combined_text)
            
            # Save metadata so we can cite sources later!
            metadatas.append({
                "url": url, 
                "section_title": title
            }) 
            
            # ChromaDB requires a unique ID for every chunk
            ids.append(f"chunk_{chunk_id}")
            chunk_id += 1
            
    print(f"Embedding and inserting {len(documents)} chunks...")
    print("This may take a minute the first time you run it...")
    
    # ChromaDB automatically downloads a lightweight embedding model 
    # and converts your text into vectors right here!
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print("Database built successfully!")
    return collection

def query_database(collection, query, top_k=2):
    """
    Searches the database for the closest semantic matches to your query.
    """
    print(f"\n" + "="*50)
    print(f"🔍 SEARCHING FOR: '{query}'")
    print("="*50)
    
    # Execute semantic search
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    # Print the results nicely
    if not results['documents'][0]:
        print("No matches found.")
        return

    for i in range(len(results['documents'][0])):
        text = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        distance = results['distances'][0][i] 
        
        # In Chroma's default distance metric, a LOWER number means MORE similar
        print(f"\n--- MATCH {i+1} (Similarity Distance: {distance:.4f}) ---")
        print(f"📌 Section Title: {meta['section_title']}")
        print(f"📄 Source URL:    {meta['url']}")
        print(f"📝 Content Snippet: \n{text[:400]}...\n") 


if __name__ == "__main__":
    # Path to the JSON file you just uploaded
    json_path = "cache/scraped_data.json" 
    
    if not os.path.exists(json_path):
        print(f"Error: Could not find {json_path}. Check your file paths.")
    else:
        # 1. Load the raw scraped data
        raw_data = load_data(json_path)
        
        # 2. Build (or load) the Vector Database
        vector_db = build_vector_database(raw_data)
        
        # 3. Test Queries based on your Ontology!
        # Notice how these queries don't rely on exact keyword matches, but on semantic meaning.
        
        query_database(vector_db, "Step-free street to train access for wheelchairs", top_k=2)
        
        query_database(vector_db, "Fares, ticketing zones, and Oyster cards", top_k=1)
        
        query_database(vector_db, "Severe delays, train collisions, and fires underground", top_k=2)