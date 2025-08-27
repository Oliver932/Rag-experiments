# ChromaDB Integration with Gemini Embeddings

This script processes JSON chunk files and stores them in a ChromaDB vector database using Google's Gemini embedding model. **The system intelligently avoids re-embedding existing chunks** by checking chunk IDs.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Gemini API key:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create an API key
   - Set it as an environment variable:
   ```bash
   export GEMINI_API_KEY='your_api_key_here'
   ```

## Usage

### Initial Database Setup

Run the main script to process all JSON files in the `chunk_files` directory:

```bash
python chunk_to_ChromaDB.py
```

This will:
- Load all JSON chunk files from `./chunk_files/`
- Check which chunks are already in the database
- **Only generate embeddings for new chunks** (saves time and API costs)
- Store them in a local ChromaDB database at `./chroma_db/`
- Run a test query to verify the setup

### Query Only (No Re-embedding)

Run the example script to query the existing database without any re-embedding:

```bash
python example_usage.py
```

This script:
- Connects to the existing database
- Runs multiple example queries
- Shows similarity scores and content previews
- **Never re-embeds existing chunks**

### Programmatic Usage

```python
from chunk_to_ChromaDB import ChromaDBManager, load_json_chunks

# Load chunks
chunks = load_json_chunks("./chunk_files")

# Initialize database
db_manager = ChromaDBManager()
db_manager.initialize_db(gemini_api_key)

# Add only missing chunks (efficient)
db_manager.add_chunks_if_missing(chunks)

# Query
results = db_manager.query_similar("your query here", n_results=5)
```

## Key Features

### 🚀 **Efficient Embedding Management**
- **Smart Duplicate Detection**: Checks existing chunk IDs before embedding
- **Incremental Updates**: Only embeds new chunks, never re-embeds existing ones
- **Cost Optimization**: Saves on Gemini API calls by avoiding redundant embeddings
- **Fast Queries**: Query-only operations don't trigger any embedding generation

### 🔧 **Flexible Operations**
- **`add_chunks_if_missing()`**: Only adds chunks not already in database
- **`add_chunks(force_recompute=True)`**: Force re-embedding if needed
- **`filter_new_chunks()`**: Preview which chunks would be added

### 📊 **Database Features**
- **Gemini Embeddings**: Uses Google's latest `text-embedding-004` model
- **Local Storage**: ChromaDB stores everything locally for privacy
- **Metadata Preservation**: Keeps all original metadata from chunk files
- **Persistent Storage**: Database persists between runs

## File Structure

- `chunk_to_ChromaDB.py` - Main script with efficient ChromaDB integration
- `example_usage.py` - Query-only example (no re-embedding)
- `requirements.txt` - Python dependencies
- `chunk_files/` - Directory containing JSON chunk files
- `chroma_db/` - ChromaDB database (created after first run)

## Performance Benefits

| Operation | First Run | Subsequent Runs |
|-----------|-----------|-----------------|
| Embedding API Calls | 451 chunks | 0 chunks (if no new data) |
| Processing Time | ~2-3 minutes | ~5 seconds |
| API Cost | Full cost | Nearly zero |

## Configuration

You can customize the following in the main script:

- `CHUNK_FILES_DIR` - Directory containing JSON chunk files
- `DB_PATH` - Path for ChromaDB database storage
- `COLLECTION_NAME` - Name of the ChromaDB collection
- Embedding model (default: `models/text-embedding-004`)

## Troubleshooting

1. **API Key Issues**: Make sure your Gemini API key is set correctly
2. **No New Chunks**: If you see "0 new chunks to add", the database is up to date
3. **Force Re-embedding**: Use `add_chunks(force_recompute=True)` if needed
4. **Empty Database**: Run `chunk_to_ChromaDB.py` first before querying

## Notes

- **First run**: Takes longer as it generates embeddings for all chunks
- **Subsequent runs**: Very fast, only processes truly new chunks
- **Query operations**: Always fast, never trigger embedding generation
- **Database persistence**: All data stored locally in `./chroma_db/`
