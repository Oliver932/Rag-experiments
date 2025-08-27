#!/usr/bin/env python3
"""
Markdown to JSON Converter

This script converts markdown files to JSON format, structured based on the markdown 
layout and headings. It creates entries for content under each lowest level heading,
with metadata including all parent headings up to the main title.

Features:
- Handles standard markdown headings (#, ##, ###, etc.)
- Filters out table of contents sections
- Preserves content hierarchy through metadata
- Processes multiple files and saves results to JSON_files directory
"""

import os
import re
import json
from pathlib import Path
import argparse
from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz


class MarkdownToJSONConverter:
    def __init__(self):
        # Only use standard markdown headings
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        
        # Keywords for sections to filter out using fuzzy matching
        self.filter_keywords = [
            "content", "contents", "table of contents", "index", "summary", 
            "preface", "foreword", "acknowledgement", "acknowledgment", 
            "acknowledgements", "acknowledgments", "references", "reference",
            "bibliography", "", "about", "about this",
            "revision history", "change log", "version history", "glossary", 
            "abbreviations", "disclaimer", "nomenclature", "notation",
            "list of figures", "list of tables", "list of symbols", "figure"
        ]
        
        # Fuzzy matching threshold (0-100, higher = more strict)
        self.fuzzy_threshold = 85  # Increased to be more conservative
        
        # Additional keywords that indicate technical content (should NOT be filtered)
        self.technical_keywords = [
            "analysis", "calculation", "model", "method", "theory", "equation",
            "performance", "flow", "physics", "aerodynamic", "dynamics", 
            "component", "system", "design", "optimization", "simulation"
        ]
    
    def is_toc_section(self, heading_text: str) -> bool:
        """Check if a heading represents a table of contents or similar section using fuzzy matching."""
        heading_lower = heading_text.lower().strip()
        
        # Remove common punctuation and extra whitespace for better matching
        cleaned_heading = re.sub(r'[^\w\s]', ' ', heading_lower)
        cleaned_heading = ' '.join(cleaned_heading.split())  # Normalize whitespace
        
        # First check if this appears to be technical content
        is_technical = any(tech_keyword in cleaned_heading for tech_keyword in self.technical_keywords)
        
        for keyword in self.filter_keywords:
            # Use partial_ratio for substring-like matching
            partial_score = fuzz.partial_ratio(cleaned_heading, keyword)
            
            # Use ratio for full string matching  
            full_score = fuzz.ratio(cleaned_heading, keyword)
            
            # Adjust threshold based on whether it's technical content
            if is_technical:
                # For technical content, require very high match to filter
                # Also check if the keyword appears as a standalone word (not part of compound term)
                words = cleaned_heading.split()
                keyword_words = keyword.split()
                
                # If the filter keyword appears as standalone words, be more lenient
                if all(kw in words for kw in keyword_words):
                    threshold = 90  # Still high, but not as strict
                else:
                    threshold = 97  # Very strict for compound terms
            else:
                # For non-technical content, use regular threshold
                threshold = self.fuzzy_threshold
            
            # Consider it a match if either score is above threshold
            if partial_score >= threshold or full_score >= threshold:
                return True
                
        return False
    
    def extract_headings_and_content(self, text: str) -> List[Dict[str, Any]]:
        """Extract headings and their content from markdown text."""
        # Find all headings with their positions
        headings = []
        
        # Only process standard markdown headings
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            start_pos = match.start()
            headings.append({
                'level': level,
                'title': title,
                'start_pos': start_pos,
                'type': 'standard'
            })
        
        # Sort headings by position
        headings.sort(key=lambda x: x['start_pos'])
        
        # Mark sections to skip (entire sections under filtered headings)
        skip_until_level = None
        sections_to_process = []
        filtered_positions = []  # Track positions of filtered headings
        
        for i, heading in enumerate(headings):
            current_level = heading['level']
            
            # Check if we're currently skipping a section
            if skip_until_level is not None:
                # Continue skipping until we reach a heading at the same level or higher
                if current_level <= skip_until_level:
                    skip_until_level = None  # Stop skipping
                else:
                    filtered_positions.append(heading['start_pos'])  # Track filtered position
                    continue  # Skip this heading and its content
            
            # Check if this heading should be filtered (start of section to skip)
            if self.is_toc_section(heading['title']):
                skip_until_level = current_level
                filtered_positions.append(heading['start_pos'])  # Track filtered position
                continue  # Skip this heading and start skipping its subsections
            
            # If we reach here, this heading should be processed
            sections_to_process.append(i)
        
        # Extract content for each heading that should be processed
        sections = []
        for idx, heading_index in enumerate(sections_to_process):
            heading = headings[heading_index]
            
            # Find the end position - need to consider both next processed heading AND any filtered headings
            possible_end_positions = []
            
            # Add next processed heading position
            if idx + 1 < len(sections_to_process):
                next_heading_index = sections_to_process[idx + 1]
                possible_end_positions.append(headings[next_heading_index]['start_pos'])
            
            # Add any filtered positions that come after this heading
            for filtered_pos in filtered_positions:
                if filtered_pos > heading['start_pos']:
                    possible_end_positions.append(filtered_pos)
            
            # Use the earliest position as the end, or end of text if no constraints
            if possible_end_positions:
                end_pos = min(possible_end_positions)
            else:
                end_pos = len(text)
            
            # Extract content
            content_start = text.find('\n', heading['start_pos']) + 1
            if content_start == 0:  # No newline found
                content_start = heading['start_pos'] + len(heading['title'])
            
            content = text[content_start:end_pos].strip()
            
            # Only include sections with meaningful content
            if content and len(content) > 20:  # Minimum content length
                sections.append({
                    'heading': heading,
                    'content': content
                })
        
        return sections
    
    def build_hierarchy(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build hierarchical structure and create final JSON entries."""
        json_entries = []
        heading_stack = []  # Stack to track current hierarchy
        
        for section in sections:
            heading = section['heading']
            content = section['content']
            current_level = heading['level']
            
            # Pop headings from stack that are at same or higher level
            while heading_stack and heading_stack[-1]['level'] >= current_level:
                heading_stack.pop()
            
            # Add current heading to stack
            heading_stack.append(heading)
            
            # Build metadata with full hierarchy
            hierarchy = [h['title'] for h in heading_stack[:-1]]  # All parent headings
            current_title = heading['title']
            
            # Create JSON entry
            entry = {
                'content': content,
                'metadata': {
                    'title': current_title,
                    'hierarchy': hierarchy,
                    'full_path': ' > '.join(hierarchy + [current_title]) if hierarchy else current_title,
                    'level': current_level,
                    'content_length': len(content),
                    'word_count': len(content.split())
                }
            }
            
            json_entries.append(entry)
        
        return json_entries
    
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a single markdown file and return JSON entries."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            print(f"Processing {os.path.basename(file_path)}...")
            
            # Extract sections
            sections = self.extract_headings_and_content(text)
            print(f"Found {len(sections)} sections with content")
            
            # Build hierarchy and create JSON entries
            json_entries = self.build_hierarchy(sections)
            print(f"Created {len(json_entries)} JSON entries")
            
            return json_entries
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return []
    
    def process_markdown_files(self, markdown_dir: str, output_dir: str):
        """Process all markdown files in the given directory."""
        markdown_path = Path(markdown_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(exist_ok=True)
        
        # Find all markdown files
        markdown_files = list(markdown_path.glob('*.md'))
        
        if not markdown_files:
            print(f"No markdown files found in {markdown_dir}")
            return
        
        print(f"Found {len(markdown_files)} markdown files to process")
        
        for md_file in markdown_files:
            print(f"\n{'='*60}")
            print(f"Processing: {md_file.name}")
            print(f"{'='*60}")
            
            # Process the file
            json_entries = self.process_file(str(md_file))
            
            if json_entries:
                # Create output filename
                output_filename = md_file.stem + '.json'
                output_file = output_path / output_filename
                
                # Save to JSON file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_entries, f, indent=2, ensure_ascii=False)
                
                print(f"Saved {len(json_entries)} entries to {output_file}")
                
                # Print summary statistics
                total_words = sum(entry['metadata']['word_count'] for entry in json_entries)
                total_chars = sum(entry['metadata']['content_length'] for entry in json_entries)
                
                print(f"Summary statistics:")
                print(f"  - Total entries: {len(json_entries)}")
                print(f"  - Total words: {total_words:,}")
                print(f"  - Total characters: {total_chars:,}")
                print(f"  - Average words per entry: {total_words/len(json_entries):.1f}")
            else:
                print(f"No content extracted from {md_file.name}")


def main():
    parser = argparse.ArgumentParser(description='Convert markdown files to structured JSON')
    parser.add_argument('--input-dir', '-i', 
                       default='markdown_files', 
                       help='Directory containing markdown files (default: markdown_files)')
    parser.add_argument('--output-dir', '-o', 
                       default='JSON_files', 
                       help='Directory to save JSON files (default: JSON_files)')
    
    args = parser.parse_args()
    
    # Get the script directory to ensure relative paths work correctly
    script_dir = Path(__file__).parent
    input_dir = script_dir / args.input_dir
    output_dir = script_dir / args.output_dir
    
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return
    
    # Create converter and process files
    converter = MarkdownToJSONConverter()
    converter.process_markdown_files(str(input_dir), str(output_dir))
    
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"Check the '{output_dir}' directory for output files.")


if __name__ == "__main__":
    main()
