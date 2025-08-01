import os
import json
from PyPDF2 import PdfReader
from tqdm import tqdm

def process_pdf_to_json_pypdf2(pdf_path, output_dir="output"):
    """
    Extracts text from a PDF file using PyPDF2 and saves it as a JSON file
    with a _low_res tag in the filename. Each page's text is stored as an item in a list.

    Args:
        pdf_path (str): The path to the PDF file.
        output_dir (str): The directory to save the output JSON file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        reader = PdfReader(pdf_path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            pages_text.append({
                "page": i + 1,
                "text": text if text else ""
            })
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_json_filename = os.path.join(
        output_dir, f"{base_name}_low_res.json"
    )
    with open(output_json_filename, "w") as f:
        json.dump(pages_text, f, indent=2)
    print(f"Successfully processed and saved structured data to '{output_json_filename}'")

if __name__ == "__main__":
    source_directory = "./test_source_files"
    output_directory = "./JSON_files"

    if not os.path.exists(source_directory):
        print(f"Error: Source directory '{source_directory}' not found.")
        print(f"Creating directory '{source_directory}'. Please add your PDF files there and run again.")
        os.makedirs(source_directory)
    else:
        pdf_files = [f for f in os.listdir(source_directory) if f.lower().endswith(".pdf")]
        if len(pdf_files) == 0:
            print(f"No PDF files found in '{source_directory}'.")
        else:
            print(f"Found {len(pdf_files)} PDF file(s) to process...")
            for filename in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
                file_path = os.path.join(source_directory, filename)
                process_pdf_to_json_pypdf2(file_path, output_dir=output_directory)
            print(f"Batch processing complete! Successfully processed {len(pdf_files)} PDF file(s).")
