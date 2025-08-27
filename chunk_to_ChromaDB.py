"""
Script to load JSON chunk files and store them in ChromaDB using Gemini embeddings.
Only embeds new chunks that aren't already in the database.
"""

import json
import os
import logging
from typing import List, Dict, Any, Set
from pathlib import Path

import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from chromadb.utils import embedding_functions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Custom embedding function using Google's Gemini API."""
    
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        """
        Initialize the Gemini embedding function.
        
        Args:
            api_key: Google API key for Gemini
            model_name: Name of the embedding model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for the input texts.
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in input:
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            except Exception as e:
                logger.error(f"Error generating embedding for text: {e}")
                # Return a zero vector if embedding fails
                embeddings.append([0.0] * 768)  # Default embedding dimension
        
        return embeddings


class ChromaDBManager:
    """Manager class for ChromaDB operations."""
    
    def __init__(self, db_path: str = "./chroma_db", collection_name: str = "document_chunks"):
        """
        Initialize ChromaDB manager.
        
        Args:
            db_path: Path to store the ChromaDB database
            collection_name: Name of the collection to create/use
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
    def initialize_db(self, gemini_api_key: str):
        """
        Initialize the ChromaDB client and collection with Gemini embeddings.
        
        Args:
            gemini_api_key: Google API key for Gemini
        """
        # Create ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(allow_reset=True)
        )
        
        # Create embedding function
        embedding_function = GeminiEmbeddingFunction(gemini_api_key)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=embedding_function
            )
            logger.info(f"Retrieved existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={"description": "Document chunks with Gemini embeddings"}
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def get_existing_chunk_ids(self) -> Set[str]:
        """
        Get all existing chunk IDs in the collection.
        
        Returns:
            Set of existing chunk IDs
        """
        if not self.collection:
            raise ValueError("Collection not initialized. Call initialize_db() first.")
        
        try:
            # Get all documents to retrieve their IDs
            all_data = self.collection.get()
            existing_ids = set(all_data['ids'])
            logger.info(f"Found {len(existing_ids)} existing chunks in database")
            return existing_ids
        except Exception as e:
            logger.error(f"Error retrieving existing chunk IDs: {e}")
            return set()

    def filter_new_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter chunks to only include those not already in the database.
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
            
        Returns:
            List of new chunks that need to be added
        """
        existing_ids = self.get_existing_chunk_ids()
        new_chunks = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            chunk_id = metadata.get('chunk_id', f"chunk_{len(new_chunks)}")
            
            if chunk_id not in existing_ids:
                new_chunks.append(chunk)
        
        logger.info(f"Found {len(new_chunks)} new chunks to add (out of {len(chunks)} total)")
        return new_chunks
    
    def add_chunks(self, chunks: List[Dict[str, Any]], force_recompute: bool = False):
        """
        Add document chunks to the ChromaDB collection.
        Only adds chunks that don't already exist unless force_recompute is True.
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
            force_recompute: If True, skip duplicate checking and add all chunks
        """
        if not self.collection:
            raise ValueError("Collection not initialized. Call initialize_db() first.")
        
        # Filter to only new chunks unless forcing recompute
        if not force_recompute:
            chunks_to_add = self.filter_new_chunks(chunks)
        else:
            chunks_to_add = chunks
            logger.info("Force recompute enabled - adding all chunks")
        
        if not chunks_to_add:
            logger.info("No new chunks to add - database is up to date")
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks_to_add:
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            chunk_id = metadata.get('chunk_id', f"chunk_{len(documents)}")
            
            documents.append(content)
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        # Add to ChromaDB (this will trigger embedding generation)
        try:
            logger.info(f"Generating embeddings and adding {len(documents)} new chunks...")
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully added {len(documents)} chunks to collection")
        except Exception as e:
            logger.error(f"Error adding chunks to collection: {e}")
            raise

    def add_chunks_if_missing(self, chunks: List[Dict[str, Any]]):
        """
        Convenience method that only adds missing chunks (never recomputes existing ones).
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
        """
        self.add_chunks(chunks, force_recompute=False)
    
    def query_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Query for similar documents.
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
            
        Returns:
            Query results from ChromaDB
        """
        if not self.collection:
            raise ValueError("Collection not initialized. Call initialize_db() first.")
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        return results
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        if not self.collection:
            raise ValueError("Collection not initialized. Call initialize_db() first.")
        
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "database_path": self.db_path
        }


def load_json_chunks(chunk_files_dir: str) -> List[Dict[str, Any]]:
    """
    Load all JSON chunk files from the specified directory.
    
    Args:
        chunk_files_dir: Path to directory containing JSON chunk files
        
    Returns:
        List of all chunks from all JSON files
    """
    chunk_files_path = Path(chunk_files_dir)
    all_chunks = []
    
    for json_file in chunk_files_path.glob("*.json"):
        logger.info(f"Loading chunks from: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                
            if isinstance(chunks, list):
                all_chunks.extend(chunks)
                logger.info(f"Loaded {len(chunks)} chunks from {json_file.name}")
            else:
                logger.warning(f"Unexpected format in {json_file.name}, expected list")
                
        except Exception as e:
            logger.error(f"Error loading {json_file}: {e}")
    
    logger.info(f"Total chunks loaded: {len(all_chunks)}")
    return all_chunks


def main():
    """Main function to process chunk files and store in ChromaDB."""
    
    # Configuration
    CHUNK_FILES_DIR = "./chunk_files"
    DB_PATH = "./chroma_db"
    COLLECTION_NAME = "document_chunks"
    
    # Get Gemini API key from environment variable
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable not set!")
        logger.info("Please set your Gemini API key: export GEMINI_API_KEY='your_api_key'")
        return
    
    try:
        # Load chunks from JSON files
        logger.info("Loading chunks from JSON files...")
        chunks = load_json_chunks(CHUNK_FILES_DIR)
        
        if not chunks:
            logger.warning("No chunks found to process")
            return
        
        # Initialize ChromaDB manager
        logger.info("Initializing ChromaDB...")
        db_manager = ChromaDBManager(DB_PATH, COLLECTION_NAME)
        db_manager.initialize_db(gemini_api_key)
        
        # Add only missing chunks to database (no re-embedding)
        logger.info("Checking for missing chunks and adding them to ChromaDB...")
        db_manager.add_chunks_if_missing(chunks)
        
        # Display collection info
        info = db_manager.get_collection_info()
        logger.info(f"Collection info: {info}")
        
        # Example query
        logger.info("Testing with example query...")
        results = db_manager.query_similar("aerodynamics fluid properties", n_results=3)
        
        print("\n=== Example Query Results ===")
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        )):
            print(f"\nResult {i+1} (distance: {distance:.4f}):")
            print(f"Source: {metadata.get('source_file', 'Unknown')}")
            print(f"Path: {metadata.get('full_path', 'Unknown')}")
            print(f"Content: {doc[:200]}...")
        
        logger.info("ChromaDB processing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in main processing: {e}")
        raise


if __name__ == "__main__":
    main()
