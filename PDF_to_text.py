import os
from PyPDF2 import PdfReader
from tqdm import tqdm

def process_pdf_to_text(pdf_path, output_dir="text_files"):
    """
    Extracts text from a PDF file using PyPDF2 and saves it as a plain text file.
    All pages' text is concatenated into a single continuous text block.

    Args:
        pdf_path (str): The path to the PDF file to process.
        output_dir (str): The directory to save the output text file.
                          Defaults to "text_files".
    
    Returns:
        None
    
    Raises:
        Exception: If there's an error reading the PDF file.
    """
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # Initialize PDF reader
        reader = PdfReader(pdf_path)
        extracted_pages = []
        
        # Extract text from each page
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text)
        
        # Combine all text into one continuous string
        combined_text = " ".join(extracted_pages)
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return

    # Generate output filename with .txt extension
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_text_filename = os.path.join(output_dir, f"{base_name}.txt")
    
    # Write text content directly to file
    with open(output_text_filename, "w", encoding="utf-8") as f:
        f.write(combined_text)
    
    print(f"✓ Successfully processed and saved text to '{output_text_filename}'")
    print(f"  Total characters extracted: {len(combined_text):,}")

if __name__ == "__main__":
    # Configuration: source and output directories
    source_directory = "./source_files"
    output_directory = "./text_files"

    # Check if source directory exists
    if not os.path.exists(source_directory):
        print(f"❌ Error: Source directory '{source_directory}' not found.")
        print(f"📁 Creating directory '{source_directory}'. Please add your PDF files there and run again.")
        os.makedirs(source_directory)
    else:
        # Find all PDF files in the source directory
        pdf_files = [f for f in os.listdir(source_directory) if f.lower().endswith(".pdf")]
        
        if len(pdf_files) == 0:
            print(f"📄 No PDF files found in '{source_directory}'.")
        else:
            print(f"🔍 Found {len(pdf_files)} PDF file(s) to process...")
            print(f"📝 Output will be saved to '{output_directory}' as text files")
            
            # Process each PDF file with progress tracking
            for filename in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
                file_path = os.path.join(source_directory, filename)
                process_pdf_to_text(file_path, output_dir=output_directory)
            
            print(f"🎉 Batch processing complete! Successfully processed {len(pdf_files)} PDF file(s).")
