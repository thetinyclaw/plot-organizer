import os
import argparse
import zipfile
import shutil
import pandas as pd
import re
from pathlib import Path

def setup_args():
    parser = argparse.ArgumentParser(description="Organize plots and extract CSV data.")
    parser.add_argument('--zip', required=True, help="Path to the input ZIP file")
    parser.add_argument('--output', default="report_output", help="Directory to save the report and organized files")
    return parser.parse_args()

def extract_zip(zip_path, extract_to):
    print(f"Extracting {zip_path} to {extract_to}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def parse_metadata(folder_name):
    # Format: 00_0E_15-N2D-260209-215048
    # ID-Descriptor-Date-Time
    parts = folder_name.split('-')
    if len(parts) >= 4:
        return {
            'part_id': parts[0].replace('_', ':'), # Restore colons for display
            'descriptor': parts[1],
            'date': parts[2],
            'time': parts[3]
        }
    return {'part_id': 'Unknown', 'descriptor': 'Unknown', 'date': 'Unknown', 'time': 'Unknown'}

def organize_files(source_dir, dest_dir):
    print("Organizing files...")
    
    # Define groups
    groups = {
        "psd_noise": [],
        "psd_signal": [],
        "thdn": [],
        "gain": [],
        "rms_nitara": [],
        "rms_electrode": [],
        "misc": []
    }
    
    metadata = {}
    csv_summary = []

    # Find the main data folder (it's usually the top-level folder inside the zip)
    # If source_dir has one folder, go into it.
    items = os.listdir(source_dir)
    if len(items) == 1 and os.path.isdir(os.path.join(source_dir, items[0])):
        data_root = os.path.join(source_dir, items[0])
        metadata = parse_metadata(items[0])
    else:
        data_root = source_dir

    print(f"Processing data root: {data_root}")

    # Walk through and categorize
    for root, _, files in os.walk(data_root):
        for file in files:
            file_path = os.path.join(root, file)
            lower_name = file.lower()
            
            if lower_name.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                # Categorization Logic
                if "_psd-" in lower_name and "noise" in lower_name:
                    groups["psd_noise"].append(file_path)
                elif "_psd-" in lower_name and "noise" not in lower_name:
                    groups["psd_signal"].append(file_path)
                elif "thdn" in lower_name:
                    groups["thdn"].append(file_path)
                elif "gain" in lower_name:
                    groups["gain"].append(file_path)
                elif "nitara" in lower_name and ("rms" in lower_name or "no-stim" in lower_name):
                    groups["rms_nitara"].append(file_path)
                elif "electrode" in lower_name and ("rms" in lower_name or "no-stim" in lower_name):
                    groups["rms_electrode"].append(file_path)
                else:
                    groups["misc"].append(file_path)
            
            elif lower_name.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)
                    summary = {
                        'filename': file,
                        'rows': len(df),
                        'columns': list(df.columns)
                    }
                    csv_summary.append(summary)
                except Exception as e:
                    print(f"Error reading CSV {file}: {e}")

    # Copy files to destination structured folders
    organized_paths = {} # store new relative paths for report
    
    plots_dir = os.path.join(dest_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    for group_name, file_list in groups.items():
        if not file_list:
            continue
            
        group_path = os.path.join(plots_dir, group_name)
        os.makedirs(group_path, exist_ok=True)
        
        organized_paths[group_name] = []
        
        for original_path in sorted(file_list): # Sort for consistency
            filename = os.path.basename(original_path)
            shutil.copy2(original_path, os.path.join(group_path, filename))
            organized_paths[group_name].append(os.path.join("plots", group_name, filename))

    return metadata, csv_summary, organized_paths

def generate_report(output_dir, metadata, csv_summary, organized_paths):
    print("Generating report...")
    report_path = os.path.join(output_dir, "report.md")
    
    with open(report_path, 'w') as f:
        f.write(f"# Data Analysis Report\n\n")
        
        # Metadata Section
        f.write("## Metadata\n")
        f.write(f"- **Part ID / Serial:** {metadata.get('part_id', 'N/A')}\n")
        f.write(f"- **Descriptor:** {metadata.get('descriptor', 'N/A')}\n")
        f.write(f"- **Date:** {metadata.get('date', 'N/A')}\n")
        f.write(f"- **Time:** {metadata.get('time', 'N/A')}\n\n")
        
        # CSV Summary
        f.write("## CSV Data Summary\n")
        if csv_summary:
            f.write("| Filename | Rows | Columns |\n")
            f.write("| :--- | :--- | :--- |\n")
            for item in csv_summary:
                cols = ", ".join(item['columns'])[:50] + "..." if len(str(item['columns'])) > 50 else ", ".join(item['columns'])
                f.write(f"| {item['filename']} | {item['rows']} | {cols} |\n")
        else:
            f.write("No CSV data found.\n")
        
        f.write("\n---\n")

        # Plots
        f.write("## Visualizations\n")
        
        # Order of presentation
        presentation_order = [
            ("PSD Noise Analysis", "psd_noise"),
            ("PSD Signal Analysis", "psd_signal"),
            ("THDN Maps", "thdn"),
            ("Gain", "gain"),
            ("Nitara RMS & No-Stim", "rms_nitara"),
            ("Electrode RMS & No-Stim", "rms_electrode"),
            ("Miscellaneous", "misc")
        ]
        
        for title, key in presentation_order:
            if key in organized_paths and organized_paths[key]:
                f.write(f"\n### {title}\n")
                # Create a grid or just list them
                for img_rel_path in organized_paths[key]:
                    img_name = os.path.basename(img_rel_path)
                    f.write(f"![{img_name}]({img_rel_path})\n")

if __name__ == "__main__":
    args = setup_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    temp_extract = os.path.join(args.output, "temp_extracted")
    
    try:
        extract_zip(args.zip, temp_extract)
        metadata, csv_summary, organized_paths = organize_files(temp_extract, args.output)
        generate_report(args.output, metadata, csv_summary, organized_paths)
        print(f"Done! Report saved to {args.output}/report.md")
    finally:
        # Cleanup temp extraction
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
