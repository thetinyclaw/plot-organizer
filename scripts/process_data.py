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
    
    # Specific keys for new grouping logic (User request 2026-02-10)
    groups = {
        "psd_signal": [],      # Non-noise PSDs (3 images expected)
        "psd_noise": [],       # Noise PSDs (3 images expected)
        "thdn": [],            # THDN maps
        "gain": [],            # Gain plots (2 images expected)
        "nitara_group": [],    # RMS Nitara + No-Stim Nitara
        "electrode_group": [], # RMS Electrode + No-Stim Electrode
        "misc": []
    }
    
    metadata = {}
    csv_summary = []

    # Handle if the zip extracts to a single folder or loose files
    items = os.listdir(source_dir)
    if len(items) == 1 and os.path.isdir(os.path.join(source_dir, items[0])):
        data_root = os.path.join(source_dir, items[0])
        # Try to parse metadata from the folder name if it looks like the pattern
        # Pattern: PartID-Descriptor-Date-Time
        # Example: 00_0E_15-N2D-260209-215048
        metadata = parse_metadata(items[0])
    else:
        data_root = source_dir
        # If loose files, maybe the zip name had the metadata? 
        # (We don't have zip name easily here, assume folder structure usually)

    print(f"Processing data root: {data_root}")

    for root, _, files in os.walk(data_root):
        for file in files:
            file_path = os.path.join(root, file)
            lower_name = file.lower()
            
            if lower_name.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                
                # PSD Logic
                if "_psd-" in lower_name:
                    if "noise" in lower_name:
                        groups["psd_noise"].append(file_path)
                    else:
                        groups["psd_signal"].append(file_path)
                        
                # THDN
                elif "thdn" in lower_name:
                    groups["thdn"].append(file_path)
                    
                # Gain
                elif "gain" in lower_name:
                    groups["gain"].append(file_path)
                    
                # Nitara Group (RMS + No-Stim)
                elif "nitara" in lower_name and ("rms" in lower_name or "no-stim" in lower_name):
                    groups["nitara_group"].append(file_path)
                    
                # Electrode Group (RMS + No-Stim)
                elif "electrode" in lower_name and ("rms" in lower_name or "no-stim" in lower_name):
                    groups["electrode_group"].append(file_path)
                    
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
            organized_paths[group_name].append(dest_path)

    return metadata, csv_summary, organized_paths

class PDFReport(FPDF):
    def header(self):
        # Only show header on first page or meaningful sections?
        # Let's keep it simple for now, but smaller.
        self.set_font('Arial', 'B', 10)
        # self.cell(0, 5, 'Data Analysis Report', 0, 1, 'R')
        # self.ln(2)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

    def add_plot_image(self, img_path, title, x, y, w, h):
        # Place image at specific coordinates
        self.image(img_path, x=x, y=y, w=w, h=h)
        # Add caption below
        self.set_xy(x, y + h + 1)
        self.set_font('Arial', 'I', 8)
        self.cell(w, 5, title, 0, 0, 'C')

def generate_pdf_report(output_dir, metadata, csv_summary, organized_paths):
    print("Generating PDF report...")
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- Page 1: Metadata, CSV, and Signal PSD ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Data Analysis Report', 0, 1, 'C')
    pdf.ln(5)
    
    # Metadata
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 6, 'Metadata', 0, 1)
    pdf.set_font('Arial', '', 10)
    meta_text = (
        f"Part ID: {metadata.get('part_id', 'N/A')} | "
        f"Descriptor: {metadata.get('descriptor', 'N/A')} | "
        f"Date: {metadata.get('date', 'N/A')} | "
        f"Time: {metadata.get('time', 'N/A')}"
    )
    pdf.multi_cell(0, 5, meta_text)
    pdf.ln(5)

    # PSD Signal (Non-Noise) - Page 1
    if "psd_signal" in organized_paths:
        pdf.chapter_title("PSD Analysis (Signal)")
        
        imgs = organized_paths["psd_signal"]
        
        y_start = pdf.get_y()
        w_img = 94
        h_img = 70
        x_start = 10
        margin_x = 2
        margin_y = 5
        
        # Simple 2-col flow
        for i, img_path in enumerate(imgs):
            col = i % 2
            row = i // 2
            
            x = x_start + (col * (w_img + margin_x))
            y = y_start + (row * (h_img + margin_y))
            
            pdf.add_plot_image(img_path, os.path.basename(img_path), x, y, w_img, h_img)
        
        # Advance cursor past the last row
        rows_used = (len(imgs) + 1) // 2
        pdf.set_y(y_start + (rows_used * (h_img + margin_y)) + 5)

    # PSD Noise - Page 2 (Force new page?)
    if "psd_noise" in organized_paths:
        pdf.add_page()
        pdf.chapter_title("PSD Analysis (Noise)")
        
        imgs = organized_paths["psd_noise"]
        y_start = pdf.get_y()
        w_img = 94
        h_img = 70
        x_start = 10
        margin_x = 2
        margin_y = 5
        
        for i, img_path in enumerate(imgs):
            col = i % 2
            row = i // 2
            
            x = x_start + (col * (w_img + margin_x))
            y = y_start + (row * (h_img + margin_y))
            
            pdf.add_plot_image(img_path, os.path.basename(img_path), x, y, w_img, h_img)
            
        rows_used = (len(imgs) + 1) // 2
        pdf.set_y(y_start + (rows_used * (h_img + margin_y)) + 5)

    # --- Remaining Groups ---
    remaining_order = [
        ("THDN Maps", "thdn"),
        ("Gain Plots", "gain"),
        ("Nitara RMS & No-Stim", "nitara_group"),
        ("Electrode RMS & No-Stim", "electrode_group"),
        ("Miscellaneous", "misc")
    ]
    
    # Constants for grid (Dynamic approach below)
    # Default fallback
    w_img = 62
    h_img = 48
    margin_x = 2
    margin_y = 5

    for title, key in remaining_order:
        if key in organized_paths and organized_paths[key]:
            pdf.add_page()
            pdf.chapter_title(title)
            
            imgs = organized_paths[key]
            num_imgs = len(imgs)
            
            # --- Dynamic Sizing Logic ---
            # Goal: Maximize size while keeping on one page if possible (or split if too many)
            # Usable area: W ~190mm, H ~250mm (minus header)
            
            if num_imgs <= 2:
                # 1x2 Layout (HUGE)
                # Stack vertically, full width
                w_img = 150 
                h_img = 110
                cols_per_row = 1
                x_center_offset = (190 - w_img) / 2 # Center it
            elif num_imgs <= 4:
                # 2x2 Layout (LARGE)
                # 2 columns, 2 rows
                w_img = 94
                h_img = 70
                cols_per_row = 2
                x_center_offset = 0
            elif num_imgs <= 6:
                # 2x3 Layout (MEDIUM-LARGE)
                w_img = 94
                h_img = 70
                cols_per_row = 2
                x_center_offset = 0
            else:
                # 3x4 Layout (DENSE - Fallback for many plots)
                w_img = 62
                h_img = 48
                cols_per_row = 3
                x_center_offset = 0

            x_start = 10 + x_center_offset
            y_start = pdf.get_y()
            
            page_row = 0
            page_col = 0
            current_page_start_y = y_start
            
            # Recalculate max rows based on new height
            max_rows = int(240 // (h_img + margin_y))
            if max_rows < 1: max_rows = 1

            for i, img_path in enumerate(imgs):
                if i > 0:
                    if i % cols_per_row == 0:
                        page_col = 0
                        page_row += 1
                        
                        if page_row >= max_rows:
                            pdf.add_page()
                            pdf.chapter_title(f"{title} (cont.)")
                            current_page_start_y = pdf.get_y()
                            page_row = 0
                            page_col = 0
                    else:
                        page_col += 1
                
                x = x_start + (page_col * (w_img + margin_x))
                y = current_page_start_y + (page_row * (h_img + margin_y))
                
                pdf.add_plot_image(img_path, os.path.basename(img_path), x, y, w_img, h_img)

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
