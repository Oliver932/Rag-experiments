import os
import json
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import elements_to_json
from tqdm import tqdm

def process_pdf_to_structured_json(pdf_path, output_dir="output"):
    """
    Processes a PDF file using unstructured.io to extract structured elements
    and saves the result as a JSON file.

    Args:
        pdf_path (str): The path to the PDF file.
        output_dir (str): The directory to save the output JSON file.
    """

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- Step 1: Partition the PDF ---
    # Use the "hi_res" strategy for high-quality layout analysis, which is
    # excellent for RAG because it understands headings, tables, and more.
    # If you have scanned documents, you might consider "ocr_only".
    try:
        elements = partition_pdf(
            filename=pdf_path,
            strategy="fast",
            infer_table_structure=False,
        )
        if not elements:  # If fast returns nothing, try hi_res
            print(f"No elements found with 'fast' strategy, retrying with 'hi_res'...")
            elements = partition_pdf(
                filename=pdf_path,
                strategy="hi_res",
                infer_table_structure=False,
            )
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return

    # --- Step 2: Inspect the Elements (Optional) ---
    # This is useful for understanding what unstructured has extracted.
    print("\n--- Found Elements ---")
    element_counts = {}
    for element in elements:
        category = element.category
        element_counts[category] = element_counts.get(category, 0) + 1
    
    for category, count in element_counts.items():
        print(f"- {category}: {count} elements")
    print("----------------------\n")


    # --- Step 3: Save the Structured Output as JSON ---
    # The elements_to_json function is a helper from unstructured
    # that serializes the list of Element objects into a JSON file.
    output_json_filename = os.path.join(
        output_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}.json"
    )
    
    elements_to_json(elements, filename=output_json_filename)

    print(f"Successfully processed and saved structured data to '{output_json_filename}'")
    
    # You can also get the elements as a list of dictionaries directly
    # elements_as_dicts = [el.to_dict() for el in elements]
    # print("\nFirst element as dictionary:\n", json.dumps(elements_as_dicts[0], indent=2))


# --- Batch Processing Usage ---
if __name__ == "__main__":
    source_directory = "./test_source_files"
    output_directory = "./JSON_files"

    # Check if the source directory exists
    if not os.path.exists(source_directory):
        print(f"Error: Source directory '{source_directory}' not found.")
        # Create the directory for the user to place files in.
        print(f"Creating directory '{source_directory}'. Please add your PDF files there and run again.")
        os.makedirs(source_directory)
    else:
        # Get list of PDF files first to track progress
        pdf_files = [f for f in os.listdir(source_directory) if f.lower().endswith(".pdf")]
        
        if len(pdf_files) == 0:
            print(f"No PDF files found in '{source_directory}'.")
        else:
            print(f"Found {len(pdf_files)} PDF file(s) to process...")
            
            # Process all PDF files with tqdm progress bar
            for filename in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
                file_path = os.path.join(source_directory, filename)
                process_pdf_to_structured_json(file_path, output_dir=output_directory)
            
            print(f"Batch processing complete! Successfully processed {len(pdf_files)} PDF file(s).")