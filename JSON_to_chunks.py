#!/usr/bin/env python3
"""
JSON to Chunks Processor

This script processes JSON files from the JSON_files directory and creates chunked versions
with hierarchical background context. For each entry in the original JSON:
1. Builds background context from all higher-level hierarchy entries
2. Calculates remaining character budget after background
3. Splits the content into chunks of the specified size with overlap
4. Prepends background to each chunk
5. Creates metadata with unique chunk IDs and hierarchy paths
"""

import json
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse


class JSONChunkProcessor:
    def __init__(self, chunk_size: int = 5000, overlap_size: int = 200, max_background_size: int = None):
        """
        Initialize the chunk processor.
        
        Args:
            chunk_size: Target size for each chunk in characters
            overlap_size: Number of characters to overlap between chunks
            max_background_size: Maximum size for background context (default: 40% of chunk_size)
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.max_background_size = max_background_size or int(chunk_size * 0.4)
        self.hierarchy_cache = {}  # Cache for building hierarchical context
        self.global_chunk_counter = 0  # Global counter for unique chunk IDs
        
    def generate_chunk_id(self, source_filename: str, entry_title: str, chunk_index: int) -> str:
        """
        Generate a globally unique chunk ID.
        
        Args:
            source_filename: Name of the source file
            entry_title: Title of the original entry
            chunk_index: Index of this chunk within the entry
            
        Returns:
            Unique chunk identifier
        """
        self.global_chunk_counter += 1
        # Create a clean filename without extension
        clean_filename = Path(source_filename).stem
        # Create a clean title (remove special characters, limit length)
        clean_title = ''.join(c for c in entry_title if c.isalnum() or c in ' -_').strip()
        clean_title = clean_title.replace(' ', '_')[:30]  # Limit to 30 chars
        
        return f"chunk_{self.global_chunk_counter:06d}_{clean_filename}_{clean_title}_{chunk_index}"
        
    def build_hierarchical_background(self, entry: Dict[str, Any], all_entries: List[Dict[str, Any]]) -> Tuple[str, bool]:
        """
        Build background context from higher levels in the hierarchy.
        
        Args:
            entry: Current entry to build background for
            all_entries: All entries in the document to search for hierarchy
            
        Returns:
            Tuple of (background context string, was_truncated boolean)
        """
        hierarchy = entry['metadata'].get('hierarchy', [])
        level = entry['metadata'].get('level', 1)
        
        background_parts = []
        
        # For each level in the hierarchy, find the corresponding entry content
        for hierarchy_title in hierarchy:
            # Check cache first
            if hierarchy_title in self.hierarchy_cache:
                background_parts.append(self.hierarchy_cache[hierarchy_title])
                continue
                
            # Find the entry that matches this hierarchy level
            for other_entry in all_entries:
                if other_entry['metadata'].get('title') == hierarchy_title:
                    content = other_entry['content'].strip()
                    self.hierarchy_cache[hierarchy_title] = content
                    background_parts.append(content)
                    break
        
        # Join all background parts with double newlines
        raw_background = '\n\n'.join(background_parts)
        
        # If no background, return empty
        if not raw_background:
            return "", False
        
        # Check if truncation is needed
        was_truncated = False
        if len(raw_background) > self.max_background_size:
            # Truncate from the beginning to keep the most recent/relevant context
            truncation_point = len(raw_background) - self.max_background_size + len('[TRUNCATED] ')
            raw_background = '[TRUNCATED] ' + raw_background[truncation_point:]
            was_truncated = True
        
        # Add clear background label
        background = f"[BACKGROUND]\n{raw_background}\n[/BACKGROUND]"
        
        return background, was_truncated
    
    def split_content_with_overlap(self, content: str, available_chars: int) -> List[str]:
        """
        Split content into chunks of available_chars size with overlap.
        
        Args:
            content: Content to split
            available_chars: Available character count after background
            
        Returns:
            List of content chunks
        """
        if len(content) <= available_chars:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            # Calculate end position for this chunk
            end = start + available_chars
            
            # If this is not the last chunk and we're not at the end of content
            if end < len(content):
                # Try to find a good break point (sentence, paragraph, or word boundary)
                # Look backwards from the end position for a good break
                break_point = end
                
                # Try to break at sentence end first
                for i in range(end - 1, max(start, end - 200), -1):
                    if content[i] in '.!?':
                        # Check if it's followed by whitespace or end of string
                        if i + 1 >= len(content) or content[i + 1].isspace():
                            break_point = i + 1
                            break
                
                # If no sentence break found, try paragraph break
                if break_point == end:
                    for i in range(end - 1, max(start, end - 200), -1):
                        if content[i:i+2] == '\n\n':
                            break_point = i + 2
                            break
                
                # If no paragraph break, try single newline
                if break_point == end:
                    for i in range(end - 1, max(start, end - 100), -1):
                        if content[i] == '\n':
                            break_point = i + 1
                            break
                
                # If no newline break, try word boundary
                if break_point == end:
                    for i in range(end - 1, max(start, end - 50), -1):
                        if content[i].isspace():
                            break_point = i + 1
                            break
                
                # Use the break point
                end = break_point
            
            # Extract the chunk
            chunk = content[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Move start position for next chunk with overlap
            if end >= len(content):
                break
                
            # Calculate next start with overlap, but ensure we don't go backwards
            next_start = max(start + 1, end - self.overlap_size)
            start = next_start
        
        return chunks
    
    def create_chunks_from_entry(self, entry: Dict[str, Any], all_entries: List[Dict[str, Any]], 
                                source_filename: str) -> List[Dict[str, Any]]:
        """
        Create chunks from a single JSON entry.
        
        Args:
            entry: The entry to process
            all_entries: All entries for building hierarchy
            source_filename: Name of source file for metadata
            
        Returns:
            List of chunk dictionaries
        """
        background, was_truncated = self.build_hierarchical_background(entry, all_entries)
        background_length = len(background)
        
        # Calculate available characters for content after background
        available_chars = self.chunk_size - background_length
        
        # Ensure minimum content size
        min_content_size = 100
        if available_chars < min_content_size:
            if background_length > 0:
                print(f"Warning: Background too large ({background_length} chars) for entry '{entry['metadata'].get('title', 'Unknown')}'. "
                      f"Reducing background size to fit minimum content size.")
                # Reduce background to fit minimum content
                max_allowed_background = self.chunk_size - min_content_size
                if max_allowed_background > 0:
                    # Truncate the background content (keeping the labels)
                    if background.startswith('[BACKGROUND]\n') and background.endswith('\n[/BACKGROUND]'):
                        inner_content = background[13:-14]  # Remove labels
                        if '[TRUNCATED] ' in inner_content:
                            # Already truncated, just reduce further
                            truncated_inner = inner_content[12:]  # Remove [TRUNCATED] 
                            new_size = max_allowed_background - 30  # Account for labels and [TRUNCATED]
                            if new_size > 0:
                                truncated_inner = truncated_inner[-new_size:]
                                background = f"[BACKGROUND]\n[TRUNCATED] {truncated_inner}\n[/BACKGROUND]"
                        else:
                            # Truncate from beginning
                            new_size = max_allowed_background - 28  # Account for labels
                            if new_size > 0:
                                truncated_inner = inner_content[-new_size:]
                                background = f"[BACKGROUND]\n[TRUNCATED] {truncated_inner}\n[/BACKGROUND]"
                            else:
                                background = ""
                    background_length = len(background)
                    was_truncated = True
                else:
                    background = ""
                    background_length = 0
            available_chars = self.chunk_size - background_length
            available_chars = max(available_chars, min_content_size)
        
        # Split the content into chunks
        content = entry['content']
        content_chunks = self.split_content_with_overlap(content, available_chars)
        
        # Create chunk objects
        chunks = []
        hierarchy_path = entry['metadata'].get('hierarchy', [])
        current_title = entry['metadata'].get('title', 'Unknown')
        full_path = entry['metadata'].get('full_path', current_title)
        
        for i, content_chunk in enumerate(content_chunks):
            # Combine background and content
            if background:
                full_content = background + '\n\n' + content_chunk
            else:
                full_content = content_chunk
            
            # Create globally unique chunk ID
            chunk_id = self.generate_chunk_id(source_filename, current_title, i)
            
            # Create streamlined chunk metadata
            chunk_metadata = {
                'chunk_id': chunk_id,
                'source_file': source_filename,
                'full_path': full_path,
                'chunk_size': len(full_content),
                'background_size': background_length,
                'content_size': len(content_chunk)
            }
            
            chunk = {
                'content': full_content,
                'metadata': chunk_metadata
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def process_json_file(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """
        Process a single JSON file and create chunks.
        
        Args:
            input_file: Path to input JSON file
            output_file: Path to output chunked JSON file
            
        Returns:
            Processing statistics
        """
        print(f"Processing {input_file}...")
        
        # Load the JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        
        # Reset hierarchy cache for each file (but keep global chunk counter)
        self.hierarchy_cache = {}
        
        # Process each entry to create chunks
        all_chunks = []
        source_filename = os.path.basename(input_file)
        
        total_entries = len(entries)
        total_original_chars = 0
        total_chunks = 0
        
        for i, entry in enumerate(entries):
            if i % 10 == 0:  # Progress indicator
                print(f"  Processing entry {i+1}/{total_entries}")
            
            original_content_length = len(entry['content'])
            total_original_chars += original_content_length
            
            chunks = self.create_chunks_from_entry(entry, entries, source_filename)
            all_chunks.extend(chunks)
            total_chunks += len(chunks)
        
        # Save the chunks
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
        # Calculate statistics
        total_chunk_chars = sum(len(chunk['content']) for chunk in all_chunks)
        avg_chunk_size = total_chunk_chars / len(all_chunks) if all_chunks else 0
        
        stats = {
            'input_file': input_file,
            'output_file': output_file,
            'original_entries': total_entries,
            'total_chunks': total_chunks,
            'original_total_chars': total_original_chars,
            'chunked_total_chars': total_chunk_chars,
            'average_chunk_size': avg_chunk_size,
            'target_chunk_size': self.chunk_size,
            'overlap_size': self.overlap_size
        }
        
        print(f"  Created {total_chunks} chunks from {total_entries} entries")
        print(f"  Average chunk size: {avg_chunk_size:.1f} characters")
        print(f"  Output saved to: {output_file}")
        
        return stats
    
    def process_all_json_files(self, json_dir: str, output_dir: str) -> List[Dict[str, Any]]:
        """
        Process all JSON files in the input directory.
        
        Args:
            json_dir: Directory containing JSON files
            output_dir: Directory to save chunked files
            
        Returns:
            List of processing statistics for each file
        """
        json_path = Path(json_dir)
        output_path = Path(output_dir)
        
        # Ensure output directory exists
        output_path.mkdir(exist_ok=True)
        
        # Find all JSON files
        json_files = list(json_path.glob('*.json'))
        
        if not json_files:
            print(f"No JSON files found in {json_dir}")
            return []
        
        print(f"Found {len(json_files)} JSON files to process")
        
        all_stats = []
        
        for json_file in json_files:
            # Create output filename
            output_filename = f"chunks_{json_file.stem}.json"
            output_file = output_path / output_filename
            
            try:
                stats = self.process_json_file(str(json_file), str(output_file))
                all_stats.append(stats)
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        
        return all_stats


def main():
    parser = argparse.ArgumentParser(description='Process JSON files into chunks with hierarchical context')
    parser.add_argument('--chunk-size', type=int, default=5000,
                       help='Target chunk size in characters (default: 5000)')
    parser.add_argument('--overlap', type=int, default=200,
                       help='Overlap size between chunks in characters (default: 200)')
    parser.add_argument('--max-background-size', type=int, default=None,
                       help='Maximum background size in characters (default: 40%% of chunk-size)')
    parser.add_argument('--input-dir', type=str, default='JSON_files',
                       help='Input directory containing JSON files (default: JSON_files)')
    parser.add_argument('--output-dir', type=str, default='chunk_files',
                       help='Output directory for chunked files (default: chunk_files)')
    parser.add_argument('--file', type=str, help='Process a specific file instead of all files')
    
    args = parser.parse_args()
    
    # Initialize the processor
    processor = JSONChunkProcessor(
        chunk_size=args.chunk_size, 
        overlap_size=args.overlap,
        max_background_size=args.max_background_size
    )
    
    if args.file:
        # Process a specific file
        input_file = args.file
        output_file = os.path.join(args.output_dir, f"chunks_{Path(input_file).stem}.json")
        
        # Ensure output directory exists
        Path(args.output_dir).mkdir(exist_ok=True)
        
        stats = processor.process_json_file(input_file, output_file)
        
        print("\nProcessing complete!")
        print(f"Statistics: {stats}")
        
    else:
        # Process all files in the directory
        all_stats = processor.process_all_json_files(args.input_dir, args.output_dir)
        
        if all_stats:
            print("\nProcessing complete!")
            print("\nSummary Statistics:")
            total_entries = sum(s['original_entries'] for s in all_stats)
            total_chunks = sum(s['total_chunks'] for s in all_stats)
            total_original_chars = sum(s['original_total_chars'] for s in all_stats)
            total_chunked_chars = sum(s['chunked_total_chars'] for s in all_stats)
            avg_chunk_size = total_chunked_chars / total_chunks if total_chunks else 0
            
            print(f"  Files processed: {len(all_stats)}")
            print(f"  Total original entries: {total_entries}")
            print(f"  Total chunks created: {total_chunks}")
            print(f"  Original total characters: {total_original_chars:,}")
            print(f"  Chunked total characters: {total_chunked_chars:,}")
            print(f"  Average chunk size: {avg_chunk_size:.1f} characters")
            print(f"  Target chunk size: {args.chunk_size} characters")
            print(f"  Maximum background size: {processor.max_background_size} characters")


if __name__ == "__main__":
    main()
