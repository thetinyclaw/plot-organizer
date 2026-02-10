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
    
    # Specific keys for new grouping logic
    groups = {
        "psd_signal_lfp_sbp": [], # LFP + SBP signal
        "psd_noise_lfp_sbp": [],  # LFP + SBP noise
        "psd_full_combined": [],  # Full PSD (signal + noise)
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
                
                # PSD Logic
                if "_psd-" in lower_name:
                    is_noise = "noise" in lower_name
                    is_full = "full" in lower_name
                    is_lfp_sbp = "lfp" in lower_name or "sbp" in lower_name
                    
                    if is_full:
                        groups["psd_full_combined"].append(file_path)
                    elif is_lfp_sbp:
                        if is_noise:
                            groups["psd_noise_lfp_sbp"].append(file_path)
                        else:
                            groups["psd_signal_lfp_sbp"].append(file_path)
                    else:
                        groups["misc"].append(file_path)
                        
                # Other Groups
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
    
    # --- Page 1: Metadata, CSV, and Signal PSD (LFP+SBP) ---
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

    # Signal PSD (LFP & SBP) - Side by Side
    if "psd_signal_lfp_sbp" in organized_paths:
        pdf.chapter_title("Signal PSD Analysis (LFP & SBP)")
        # 2 plots side-by-side
        # Page width ~210mm. Margins 10mm. Usable ~190mm.
        # Image width ~90mm each.
        y_start = pdf.get_y()
        x_start = 10
        w_img = 90
        h_img = 60 # Aspect ratio guess
        
        imgs = organized_paths["psd_signal_lfp_sbp"]
        # Assuming exactly 2 images usually (LFP and SBP)
        for i, img_path in enumerate(imgs):
            if i < 2:
                x = x_start + (i * (w_img + 5))
                pdf.add_plot_image(img_path, os.path.basename(img_path), x, y_start, w_img, h_img)
        
        pdf.set_y(y_start + h_img + 10)

    # Noise PSD (LFP & SBP) - Side by Side
    if "psd_noise_lfp_sbp" in organized_paths:
        pdf.chapter_title("Noise PSD Analysis (LFP & SBP)")
        y_start = pdf.get_y()
        x_start = 10
        w_img = 90
        h_img = 60
        
        imgs = organized_paths["psd_noise_lfp_sbp"]
        for i, img_path in enumerate(imgs):
            if i < 2:
                x = x_start + (i * (w_img + 5))
                pdf.add_plot_image(img_path, os.path.basename(img_path), x, y_start, w_img, h_img)
        
        pdf.set_y(y_start + h_img + 10)

    # --- Page 2: Full PSD (Signal & Noise) ---
    if "psd_full_combined" in organized_paths:
        pdf.add_page()
        pdf.chapter_title("Full PSD Analysis (Signal & Noise)")
        # Expecting 2 images (signal full, noise full).
        # Stack vertically or side-by-side depending on aspect ratio.
        # Let's do side-by-side to save space if possible, or vertical if large.
        # Given "Full", usually implies wide freq range. Let's stack 2 vertically but smaller.
        
        y_start = pdf.get_y()
        w_img = 150
        h_img = 80
        x_center = (210 - w_img) / 2
        
        imgs = organized_paths["psd_full_combined"]
        for i, img_path in enumerate(imgs):
            if pdf.get_y() + h_img > 270:
                pdf.add_page()
                y_start = 20
            
            pdf.add_plot_image(img_path, os.path.basename(img_path), x_center, pdf.get_y(), w_img, h_img)
            pdf.set_y(pdf.get_y() + h_img + 10)

    # --- Remaining Plots (2x2 Grid per page) ---
    remaining_order = [
        ("THDN Maps", "thdn"),
        ("Gain", "gain"),
        ("Nitara RMS & No-Stim", "rms_nitara"),
        ("Electrode RMS & No-Stim", "rms_electrode"),
        ("Miscellaneous", "misc")
    ]

    for title, key in remaining_order:
        if key in organized_paths and organized_paths[key]:
            pdf.add_page()
            pdf.chapter_title(title)
            
            # Grid Layout: 2 columns, rows as needed
            imgs = organized_paths[key]
            x_start = 10
            y_start = pdf.get_y()
            w_img = 90
            h_img = 65
            
            col = 0
            row = 0
            
            for i, img_path in enumerate(imgs):
                if i > 0 and i % 2 == 0:
                    row += 1
                    col = 0
                else:
                    col = i % 2
                
                # Check page overflow
                cur_y = y_start + (row * (h_img + 15))
                if cur_y + h_img > 270:
                    pdf.add_page()
                    pdf.chapter_title(f"{title} (cont.)")
                    y_start = pdf.get_y()
                    row = 0
                    cur_y = y_start
                
                x = x_start + (col * (w_img + 5))
                pdf.add_plot_image(img_path, os.path.basename(img_path), x, cur_y, w_img, h_img)

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
