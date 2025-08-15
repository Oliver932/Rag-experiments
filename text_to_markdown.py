import os
import google.generativeai as genai
from pathlib import Path
import json
import time

def count_tokens_gemini(text, model_name="gemini-2.5-flash-lite"):
    """
    Counts the number of tokens in a given text using the Gemini API.
    
    Args:
        text (str): The text content to be tokenized.
        model_name (str): The specific Gemini model to use for tokenization.
        
    Returns:
        int: The total number of tokens, or 0 if an error occurs.
    """
    try:
        model = genai.GenerativeModel(model_name)
        result = model.count_tokens(contents=text)
        return result.total_tokens
    except Exception as e:
        print(f"Error counting tokens with {model_name}: {e}")
        return 0

def chunk_text_by_tokens(text, max_tokens=30000, model_name="gemini-2.5-flash-lite"):
    """
    Chunks text into segments with approximately max_tokens each.
    
    Args:
        text (str): The text to chunk
        max_tokens (int): Maximum tokens per chunk (default 30000 = 0.5x output limit)
        model_name (str): Model to use for token counting
        
    Returns:
        list: List of text chunks
    """
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        # Test adding this paragraph to current chunk
        test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
        token_count = count_tokens_gemini(test_chunk, model_name)
        
        if token_count <= max_tokens:
            current_chunk = test_chunk
        else:
            # If current chunk is not empty, save it and start new chunk
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                # Single paragraph is too large, split by sentences
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    test_chunk = current_chunk + ". " + sentence if current_chunk else sentence
                    token_count = count_tokens_gemini(test_chunk, model_name)
                    
                    if token_count <= max_tokens:
                        current_chunk = test_chunk
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            # Single sentence too large, add as is
                            chunks.append(sentence.strip())
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def convert_to_markdown(text_chunk, model_name="gemini-2.5-flash-lite"):
    """
    Converts a text chunk to markdown format with LaTeX equations using Gemini.
    
    Args:
        text_chunk (str): The text chunk to convert
        model_name (str): The Gemini model to use
        
    Returns:
        str: The converted markdown text
    """
    prompt = """Convert the following text to well-formatted markdown. Follow these guidelines:

1. Use proper markdown headings (# ## ### etc.) for sections and subsections
2. Convert any mathematical equations, formulas, or expressions to LaTeX format using $ for inline math and $$ for display math
3. Format lists, tables, and code appropriately using markdown syntax
4. Preserve the technical content and meaning exactly
5. Make the text more readable while maintaining all original information
6. Use bold and italic formatting where appropriate for emphasis
7. Ensure equations are properly formatted in LaTeX syntax

Text to convert:

"""
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt + text_chunk)
        return response.text
    except Exception as e:
        print(f"Error converting text to markdown: {e}")
        return f"Error converting chunk: {text_chunk[:100]}..."

def process_text_file(file_path, output_dir="./markdown_files", model_name="gemini-2.5-flash-lite"):
    """
    Processes a single text file: chunks it and converts each chunk to markdown.
    
    Args:
        file_path (Path): Path to the text file
        output_dir (str): Directory to save markdown files
        model_name (str): Gemini model to use
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\nProcessing: {file_path.name}")
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as file:
            text_content = file.read()
        
        # Count total tokens
        total_tokens = count_tokens_gemini(text_content, model_name)
        print(f"Total tokens: {total_tokens:,}")
        
        # Chunk the text
        print("Chunking text...")
        chunks = chunk_text_by_tokens(text_content, max_tokens=30000, model_name=model_name)
        print(f"Created {len(chunks)} chunks")
        
        # Convert each chunk to markdown
        markdown_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"Converting chunk {i+1}/{len(chunks)}...")
            markdown_chunk = convert_to_markdown(chunk, model_name)
            markdown_chunks.append(markdown_chunk)
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        # Combine all markdown chunks
        combined_markdown = "\n\n---\n\n".join(markdown_chunks)
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save the combined markdown file
        output_file = output_path / f"{file_path.stem}.md"
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(combined_markdown)
        
        print(f"Saved markdown to: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path.name}: {e}")
        return False

def process_all_text_files(text_dir="./text_files", output_dir="./markdown_files", model_name="gemini-2.5-flash-lite"):
    """
    Processes all text files in the specified directory.
    
    Args:
        text_dir (str): Directory containing text files
        output_dir (str): Directory to save markdown files
        model_name (str): Gemini model to use
    """
    text_dir_path = Path(text_dir)
    
    if not text_dir_path.exists():
        print(f"Directory '{text_dir}' does not exist.")
        return
    
    txt_files = list(text_dir_path.glob("*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in '{text_dir}'")
        return
    
    print(f"Found {len(txt_files)} text file(s) to process...")
    
    successful = 0
    for txt_file in txt_files:
        if process_text_file(txt_file, output_dir, model_name):
            successful += 1
    
    print(f"\n" + "=" * 60)
    print(f"Successfully processed {successful}/{len(txt_files)} files")
    print(f"Markdown files saved to: {output_dir}")

def main():
    """
    Main function to execute the text to markdown conversion script.
    """
    print("Text to Markdown Converter using Gemini 2.5 Flash Lite")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: The 'GEMINI_API_KEY' environment variable was not found.")
        print("Please set it before running the script.")
        return
    
    genai.configure(api_key=api_key)
    
    # Process all text files
    process_all_text_files()

if __name__ == "__main__":
    main()