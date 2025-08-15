import os
import json
import sys

def clean_json(input_path, output_path):
    with open(input_path, 'r') as f:
        data = json.load(f)

    cleaned = []
    current_title = None
    for el in data:
        el_type = el.get("type", "")
        # if el_type == "Formula":
        #     continue  # Remove formulas
        if el_type == "Title":
            current_title = el.get("text", None)
            continue  # Don't include title as a separate element
        # Remove unnecessary metadata, keep element_id and filename
        text = el.get("text", "")
        new_el = {
            "text": text,
            "type": el_type,
            "element_id": el.get("element_id", None),
            "filename": None
        }
        # Try to get filename from metadata if present
        meta = el.get("metadata", {})
        if isinstance(meta, dict):
            new_el["filename"] = meta.get("filename", None)
        cleaned.append(new_el)

    # Calculate mean and stddev of text lengths
    import numpy as np
    import matplotlib.pyplot as plt
    text_lengths = [len(e["text"]) for e in cleaned if e["text"]]
    mean_len = np.mean(text_lengths) if text_lengths else 0
    std_len = np.std(text_lengths) if text_lengths else 0

    with open(output_path, 'w') as f:
        json.dump(cleaned, f, indent=2)
    print(f"Cleaned JSON saved to {output_path}")
    print(f"Mean text length: {mean_len:.2f}")
    print(f"Stddev text length: {std_len:.2f}")

    # Plot histogram of text lengths
    if text_lengths:
        plt.figure(figsize=(8, 4))
        plt.hist(text_lengths, bins=40, color='skyblue', edgecolor='black')
        plt.title('Distribution of Text Lengths')
        plt.xlabel('Text Length (characters)')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    # Define paths here
    input_file = "./JSON_files/TASOPT_reduced.json"  # Change this as needed
    output_dir = "./cleaned_JSON_files"  # Change this as needed
    base = os.path.basename(input_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir, base)
    clean_json(input_file, output_file)
