import os
import google.generativeai as genai
from pathlib import Path
import json

def count_tokens_gemini(text, model_name="gemini-2.5-flash-lite"):
    """
    Counts the number of tokens in a given text using the Gemini API.
    
    Args:
        text (str): The text content to be tokenized.
        model_name (str): The specific Gemini model to use for tokenization.
                          Defaults to "gemini-2.5-flash-lite".
        
    Returns:
        int: The total number of tokens, or 0 if an error occurs.
    """
    try:
        # First, create an instance of the generative model.
        model = genai.GenerativeModel(model_name)
        # Then, call the count_tokens method on the model instance.
        result = model.count_tokens(contents=text)
        return result.total_tokens
    except Exception as e:
        print(f"Error counting tokens with {model_name}: {e}")
        return 0

def load_and_count_text_files(text_dir="./text_files"):
    """
    Loads all .txt files from a directory, counts their tokens, and returns the results.
    
    Args:
        text_dir (str): The path to the directory containing the text files.
        
    Returns:
        dict: A dictionary mapping filenames to their respective token counts.
    """
    text_dir_path = Path(text_dir)
    token_counts = {}
    
    if not text_dir_path.exists():
        print(f"Directory '{text_dir}' does not exist. Please create it and add your .txt files.")
        return token_counts
    
    # Find all files ending with .txt in the specified directory.
    txt_files = list(text_dir_path.glob("*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in '{text_dir}'")
        return token_counts
    
    print(f"Found {len(txt_files)} text file(s) to process...")
    
    for txt_file in txt_files:
        print(f"\nProcessing: {txt_file.name}")
        try:
            # Read the entire content of the file.
            with open(txt_file, 'r', encoding='utf-8') as file:
                text_content = file.read()
            
            # Call the function to count tokens using the Gemini API.
            token_count = count_tokens_gemini(text_content)
            token_counts[txt_file.name] = token_count
            
            print(f"  {len(text_content):,} characters → {token_count:,} tokens")
            
        except Exception as e:
            print(f"  Error processing {txt_file.name}: {e}")
            token_counts[txt_file.name] = 0
    
    return token_counts

def main():
    """
    Main function to execute the token counting script.
    """
    # Corrected the model name in the title for clarity.
    print("Text File Token Counter using Gemini 2.5 Flash Lite Tokenizer")
    print("=" * 60)
    
    # The API key must be set as an environment variable for security.
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: The 'GEMINI_API_KEY' environment variable was not found.")
        print("Please set it before running the script.")
        return
    
    genai.configure(api_key=api_key)
    
    # Process the text files in the target directory.
    token_counts = load_and_count_text_files()
    
    if token_counts:
        print("\n" + "=" * 60)
        print("SUMMARY OF TOKEN COUNTS:")
        print("=" * 60)
        
        total_tokens = 0
        # Display a formatted summary of the results.
        for filename, count in token_counts.items():
            print(f"{filename:<30} {count:>10,} tokens")
            total_tokens += count
        
        print("-" * 60)
        print(f"{'TOTAL':<30} {total_tokens:>10,} tokens")
    
    else:
        print("\nNo files were processed successfully.")

if __name__ == "__main__":
    main()