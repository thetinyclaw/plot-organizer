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

def organize_files(source_dir, dest_dir):
    print("Organizing files...")
    images_dir = os.path.join(dest_dir, "plots")
    os.makedirs(images_dir, exist_ok=True)
    
    data_summary = []
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
                # Simple heuristic: group by part of filename before the first underscore or hyphen
                # Adjust regex based on specific user needs later
                match = re.match(r"([a-zA-Z0-9]+)[_-]", file)
                group_name = match.group(1) if match else "misc"
                
                group_dir = os.path.join(images_dir, group_name)
                os.makedirs(group_dir, exist_ok=True)
                shutil.copy2(file_path, os.path.join(group_dir, file))
                
            elif file.lower().endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)
                    # Basic extraction example - can be customized
                    summary = {
                        'filename': file,
                        'rows': len(df),
                        'columns': list(df.columns)
                    }
                    data_summary.append(summary)
                except Exception as e:
                    print(f"Error reading {file}: {e}")

    return data_summary

def generate_report(output_dir, data_summary):
    print("Generating report...")
    report_path = os.path.join(output_dir, "report.md")
    
    with open(report_path, 'w') as f:
        f.write("# Data Analysis Report\n\n")
        
        f.write("## CSV Data Summary\n")
        if data_summary:
            f.write("| Filename | Rows | Columns |\n")
            f.write("| :--- | :--- | :--- |\n")
            for item in data_summary:
                cols = ", ".join(item['columns'])[:50] + "..." if len(str(item['columns'])) > 50 else ", ".join(item['columns'])
                f.write(f"| {item['filename']} | {item['rows']} | {cols} |\n")
        else:
            f.write("No CSV data found.\n")
            
        f.write("\n## Organized Plots\n")
        plots_dir = os.path.join(output_dir, "plots")
        if os.path.exists(plots_dir):
            for group in sorted(os.listdir(plots_dir)):
                group_path = os.path.join(plots_dir, group)
                if os.path.isdir(group_path):
                    f.write(f"\n### Group: {group}\n")
                    for image in sorted(os.listdir(group_path)):
                        # Use relative path for markdown
                        rel_path = os.path.join("plots", group, image)
                        f.write(f"![{image}]({rel_path})\n")

if __name__ == "__main__":
    args = setup_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    temp_extract = os.path.join(args.output, "temp_extracted")
    
    try:
        extract_zip(args.zip, temp_extract)
        summary = organize_files(temp_extract, args.output)
        generate_report(args.output, summary)
        print(f"Done! Report saved to {args.output}/report.md")
    finally:
        # Cleanup temp extraction
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
