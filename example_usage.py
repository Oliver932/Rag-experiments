#!/usr/bin/env python3
"""
Example script showing how to use the ChromaDB integration.
This script now only queries the existing database without re-embedding chunks.
"""

import os
from chunk_to_ChromaDB import ChromaDBManager

def main():
    """Example usage of the ChromaDB integration - query only mode."""
    
    # Set your Gemini API key
    # You can get it from: https://makersuite.google.com/app/apikey
    # Then set it as an environment variable: export GEMINI_API_KEY='your_api_key'
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your_api_key'")
        return
    
    # Initialize database manager (connects to existing database)
    print("Connecting to existing ChromaDB database...")
    db_manager = ChromaDBManager()
    db_manager.initialize_db(gemini_api_key)
    
    # Check database info
    info = db_manager.get_collection_info()
    print(f"Database contains {info['document_count']} chunks")
    
    if info['document_count'] == 0:
        print("Database is empty! Run 'python chunk_to_ChromaDB.py' first to populate it.")
        return
    
    # Query examples - no re-embedding needed!
    queries = [
        "aerodynamics and fluid flow",
        "atmospheric properties", 
        "ideal gas law",
        "conservation of mass and momentum",
        "wing design and lift generation",
        "boundary layer theory"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print('='*50)
        
        results = db_manager.query_similar(query, n_results=3)
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"\nResult {i+1} (similarity: {1-distance:.3f}):")
            print(f"Source: {metadata.get('source_file', 'Unknown')}")
            print(f"Path: {metadata.get('full_path', 'Unknown')}")
            print(f"Content: {doc[:200]}...")
            if len(doc) > 200:
                print("...")

def add_new_chunks_example():
    """Example of how to add new chunks without re-embedding existing ones."""
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your_api_key'")
        return
    
    # Load all chunks from files
    from chunk_to_ChromaDB import load_json_chunks
    chunks = load_json_chunks("./chunk_files")
    
    # Initialize database
    db_manager = ChromaDBManager()
    db_manager.initialize_db(gemini_api_key)
    
    # This will only add chunks that don't already exist
    print("Adding any missing chunks (no re-embedding of existing chunks)...")
    db_manager.add_chunks_if_missing(chunks)
    
    # Show final count
    info = db_manager.get_collection_info()
    print(f"Database now contains {info['document_count']} chunks")

if __name__ == "__main__":
    print("=== ChromaDB Query Example ===")
    print("This script queries the existing database without re-embedding.")
    print("Run 'python chunk_to_ChromaDB.py' first if the database is empty.\n")
    
    main()
    
    print("\n" + "="*60)
    print("To add new chunks without re-embedding existing ones:")
    print("Run the add_new_chunks_example() function or use:")
    print("db_manager.add_chunks_if_missing(chunks)")
