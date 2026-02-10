import os
import argparse
import zipfile
import shutil
import pandas as pd
import re
from pathlib import Path
from fpdf import FPDF

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
            'part_id': parts[0].replace('_', ':'),
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

    items = os.listdir(source_dir)
    if len(items) == 1 and os.path.isdir(os.path.join(source_dir, items[0])):
        data_root = os.path.join(source_dir, items[0])
        metadata = parse_metadata(items[0])
    else:
        data_root = source_dir

    print(f"Processing data root: {data_root}")

    for root, _, files in os.walk(data_root):
        for file in files:
            file_path = os.path.join(root, file)
            lower_name = file.lower()
            
            if lower_name.endswith(('.png', '.jpg', '.jpeg', '.svg')):
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

    organized_paths = {}
    plots_dir = os.path.join(dest_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    for group_name, file_list in groups.items():
        if not file_list:
            continue
            
        group_path = os.path.join(plots_dir, group_name)
        os.makedirs(group_path, exist_ok=True)
        
        organized_paths[group_name] = []
        
        for original_path in sorted(file_list):
            filename = os.path.basename(original_path)
            dest_path = os.path.join(group_path, filename)
            shutil.copy2(original_path, dest_path)
            # Store absolute path for PDF generation to be safe, or relative to script execution
            organized_paths[group_name].append(dest_path)

    return metadata, csv_summary, organized_paths

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Data Analysis Report', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

    def add_plot_image(self, img_path, title):
        self.set_font('Arial', 'I', 9)
        self.cell(0, 5, title, 0, 1)
        # Calculate width to fit page (A4 width is 210mm, margins ~20mm)
        # Using 170mm width for image
        try:
            self.image(img_path, w=170)
        except Exception as e:
            self.cell(0, 5, f"Error loading image: {str(e)}", 0, 1)
        self.ln(5)

def generate_pdf_report(output_dir, metadata, csv_summary, organized_paths):
    print("Generating PDF report...")
    pdf = PDFReport()
    pdf.add_page()
    
    # Metadata
    pdf.chapter_title('Metadata')
    meta_text = (
        f"Part ID / Serial: {metadata.get('part_id', 'N/A')}\n"
        f"Descriptor: {metadata.get('descriptor', 'N/A')}\n"
        f"Date: {metadata.get('date', 'N/A')}\n"
        f"Time: {metadata.get('time', 'N/A')}"
    )
    pdf.chapter_body(meta_text)
    
    # CSV Summary
    pdf.chapter_title('CSV Data Summary')
    if csv_summary:
        for item in csv_summary:
            cols = ", ".join(item['columns'])
            # Truncate long column lists
            if len(cols) > 100:
                cols = cols[:100] + "..."
            
            summary_text = (
                f"File: {item['filename']}\n"
                f"Rows: {item['rows']}\n"
                f"Columns: {cols}\n"
            )
            pdf.chapter_body(summary_text)
            pdf.ln(2)
    else:
        pdf.chapter_body("No CSV data found.")
    
    pdf.add_page()
    
    # Visualizations
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
            pdf.chapter_title(title)
            for img_path in organized_paths[key]:
                img_name = os.path.basename(img_path)
                # Check if we need a new page for the image
                if pdf.get_y() > 220: # A4 height is ~297mm
                    pdf.add_page()
                    pdf.chapter_title(f"{title} (cont.)")
                
                pdf.add_plot_image(img_path, img_name)
            
            pdf.ln(5)

    pdf_output_path = os.path.join(output_dir, "report.pdf")
    pdf.output(pdf_output_path)
    return pdf_output_path

if __name__ == "__main__":
    args = setup_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    temp_extract = os.path.join(args.output, "temp_extracted")
    
    try:
        extract_zip(args.zip, temp_extract)
        metadata, csv_summary, organized_paths = organize_files(temp_extract, args.output)
        pdf_path = generate_pdf_report(args.output, metadata, csv_summary, organized_paths)
        print(f"Done! Report saved to {pdf_path}")
    finally:
        # Cleanup temp extraction
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
