import os
import json
import argparse
import requests
from bs4 import BeautifulSoup

EMAIL = "stallon.fernandes@kcl.ac.uk"
HEADERS = {
    'User-Agent': f"LondonTransportKnowledgeGraph/1.0 ({EMAIL})", 
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

def parse_html_table_matrix(table_tag):
    """
    Converts an HTML table into a matrix (list of lists).
    The first row usually contains the field names (headers) if <th> tags or standard headers are used.
    """
    rows = table_tag.find_all('tr')
    matrix = []
    
    for row in rows:
        # Extract both table headers (th) and table data (td)
        cols = row.find_all(['th', 'td'])
        # Clean the text and remove excessive whitespace, joining nested paragraphs with a space
        cols_text = [ele.get_text(separator=" ", strip=True) for ele in cols]
        
        # If the row has text data, append it as a list to our matrix
        if any(cols_text): 
            matrix.append(cols_text)
            
    return matrix

def download_and_extract_webpage(urls, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    all_documents = []

    for url in urls:
        try:
            print(f"Requesting: {url}...")
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()

            if "<html" not in response.text.lower():
                print("WARNING: The downloaded content does not look like HTML!")

            soup = BeautifulSoup(response.text, 'html.parser')

            # Clean up junk (leaves useful tables intact)
            for junk in soup.find_all(['table', 'span', 'div'], class_=['reflist', 'toc', 'navbox', 'mw-editsection']):
                junk.decompose()

            # Find important tags sequentially
            tags = soup.find_all(['h1', 'h2', 'h3', 'p', 'table'])

            document_content = {}
            current_title = "Introduction"

            for tag in tags:
                # Skip parsing paragraphs or headings if they are nested inside a table.
                # The table parsing function will extract their text automatically into the matrix.
                if tag.name != 'table' and tag.find_parent('table'):
                    continue

                # 1. Handle Headings
                if tag.name in ['h1', 'h2', 'h3']:
                    current_title = tag.get_text(strip=True)
                    if current_title not in document_content:
                        document_content[current_title] = []

                # 2. Handle Paragraphs
                elif tag.name == 'p':
                    text = tag.get_text(strip=True)
                    if not text:
                        continue
                    
                    if current_title not in document_content:
                        document_content[current_title] = []
                    document_content[current_title].append(text)

                # 3. Handle Tables
                elif tag.name == 'table':
                    table_matrix = parse_html_table_matrix(tag)
                    
                    # Only append if the table actually contained rows/data
                    if table_matrix:
                        if current_title not in document_content:
                            document_content[current_title] = []
                            
                        # Deduplicate: responsive sites often have multiple identical tables hidden in the DOM
                        is_duplicate = False
                        for item in document_content[current_title]:
                            if isinstance(item, dict) and item.get("table_matrix") == table_matrix:
                                is_duplicate = True
                                break
                                
                        if not is_duplicate:
                            # Append as a structured dictionary so it exports to JSON natively and beautifully
                            document_content[current_title].append({
                                "type": "table",
                                "table_matrix": table_matrix
                            })

            doc_object = {
                "__id": url, 
                "content": document_content
            }
            
            all_documents.append(doc_object)
            print(f"SUCCESS: Extracted grouped content (with tables) from {url}")

        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Save to JSON
    output_file_path = os.path.join("data/json", args.output)
    with open(output_file_path, "w", encoding="utf-8") as file:
        json.dump(all_documents, file, indent=4, ensure_ascii=False)
        
    print(f"\nSaved all data to {output_file_path}")

    return all_documents


def read_urls_from_file(file_path):
    with open(file_path, 'r') as file:
        urls = []
        for line in file.readlines():
            url = line.strip()
            if not url or url.startswith('#'):
                continue
            else:
                urls.append(url)

    return urls

def main(args):
    urls = read_urls_from_file(args.urls)
    download_and_extract_webpage(urls, args.output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Content from webpages"
    )
    parser.add_argument(
        "--urls",
        type=str,
        default="webscrapper/urls.txt",
        help="File path to text file containing urls"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scraped_data.json",
        help="File path to save scraped data"
    )
    args = parser.parse_args()
    main(args)