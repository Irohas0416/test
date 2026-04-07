import os
from pypdf import PdfReader, PdfWriter

def split_pdf(input_path, output_dir, chunk_size=20):
    os.makedirs(output_dir, exist_ok=True)
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        chunk_pages = reader.pages[i:i + chunk_size]
        
        for page in chunk_pages:
            writer.add_page(page)
            
        output_filename = os.path.join(output_dir, f"chunk_{i//chunk_size + 1}.pdf")
        with open(output_filename, "wb") as out_file:
            writer.write(out_file)
        print(f"Created: {output_filename}")

