import os
import argparse
import shutil
import pandas as pd
from fpdf import FPDF

def setup_args():
    parser = argparse.ArgumentParser(description="Organize plots and extract CSV data.")
    parser.add_argument('--dir', required=True, help="Path to the input directory")
    parser.add_argument('--output', default="report_output", help="Directory to save the report and organized files")
    return parser.parse_args()

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

def organize_files(data_root, dest_dir):
    print(f"Organizing files from {data_root}...")
    
    # Structure for grouping
    organized_data = {
        "saline_ec0": {
            "psd_signal": [],
            "psd_noise": [],
            "others": []
        },
        "saline_ec1": {
            "psd_signal": [],
            "psd_noise": [],
            "others": []
        },
        "impedance": {
            "electrodes": [],
            "nitara": [],
            "yield": []
        }
    }
    
    csv_summary = []
    metadata = {}

    # Extract metadata
    for sub in ['saline-results', 'impedance-results']:
        sub_path = os.path.join(data_root, sub)
        if os.path.exists(sub_path):
            folders = [f for f in os.listdir(sub_path) if os.path.isdir(os.path.join(sub_path, f))]
            if folders:
                metadata = parse_metadata(folders[0])
                break

    # Walk through the directory structure
    for root, _, files in os.walk(data_root):
        if "png" in root or ("/png" in root) or ("\\png" in root):
            for file in files:
                file_path = os.path.join(root, file)
                lower_name = file.lower()
                
                if not lower_name.endswith(('.png', '.jpg', '.jpeg')):
                    continue

                # Saline Processing
                if "saline-results" in root:
                    ec_key = None
                    if "ec0" in lower_name:
                        ec_key = "saline_ec0"
                    elif "ec1" in lower_name:
                        ec_key = "saline_ec1"
                    
                    if ec_key:
                        if "psd" in lower_name:
                            if "noise" in lower_name:
                                organized_data[ec_key]["psd_noise"].append(file_path)
                            else:
                                organized_data[ec_key]["psd_signal"].append(file_path)
                        else:
                            organized_data[ec_key]["others"].append(file_path)

                # Impedance Processing
                elif "impedance-results" in root:
                    if "impedance-electrodes" in lower_name:
                        organized_data["impedance"]["electrodes"].append(file_path)
                    elif "impedance-nitara" in lower_name:
                        organized_data["impedance"]["nitara"].append(file_path)
                    elif "yield-response" in lower_name:
                        organized_data["impedance"]["yield"].append(file_path)

    # Copy files
    organized_paths = {
        "saline_ec0": {},
        "saline_ec1": {},
        "impedance": {}
    }
    
    plots_dir = os.path.join(dest_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # Process Saline
    for ec in ["saline_ec0", "saline_ec1"]:
        ec_dir = os.path.join(plots_dir, ec)
        os.makedirs(ec_dir, exist_ok=True)
        for group in ["psd_signal", "psd_noise", "others"]:
            if organized_data[ec][group]:
                group_dir = os.path.join(ec_dir, group)
                os.makedirs(group_dir, exist_ok=True)
                organized_paths[ec][group] = []
                for original_path in sorted(organized_data[ec][group]):
                    filename = os.path.basename(original_path)
                    dest_path = os.path.join(group_dir, filename)
                    shutil.copy2(original_path, dest_path)
                    organized_paths[ec][group].append(dest_path)

    # Process Impedance
    imp_dir = os.path.join(plots_dir, "impedance")
    os.makedirs(imp_dir, exist_ok=True)
    for group in ["electrodes", "nitara", "yield"]:
        if organized_data["impedance"][group]:
            group_dir = os.path.join(imp_dir, group)
            os.makedirs(group_dir, exist_ok=True)
            organized_paths["impedance"][group] = []
            for original_path in sorted(organized_data["impedance"][group]):
                filename = os.path.basename(original_path)
                dest_path = os.path.join(group_dir, filename)
                shutil.copy2(original_path, dest_path)
                organized_paths["impedance"][group].append(dest_path)

    return metadata, csv_summary, organized_paths

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(2)

    def add_plot_image(self, img_path, x, y, w, h=0):
        self.image(img_path, x=x, y=y, w=w, h=h)

def generate_pdf_report(output_dir, metadata, csv_summary, organized_paths):
    print("Generating PDF report...")
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Metadata Page
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Data Analysis Report', 0, 1, 'C')
    pdf.ln(5)
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

    def add_plot_group_dynamic(title, imgs):
        if not imgs: return
        pdf.add_page()
        pdf.chapter_title(title)
        
        # Grid settings
        num_imgs = len(imgs)
        if num_imgs <= 2:
            w_img, h_img, cols_per_row = 150, 0, 1
            x_center_offset = (190 - w_img) / 2
        elif num_imgs <= 6:
            w_img, h_img, cols_per_row = 94, 0, 2
            x_center_offset = 0
        else:
            w_img, h_img, cols_per_row = 62, 0, 3
            x_center_offset = 0

        x_start = 10 + x_center_offset
        margin_x, margin_y = 2, 5
        
        y_curr = pdf.get_y()
        col = 0
        max_y_in_row = 0
        
        for i, img_path in enumerate(imgs):
            if i > 0 and i % cols_per_row == 0:
                col = 0
                y_curr += max_y_in_row + margin_y # Removed +5 caption space
                max_y_in_row = 0
                
                # Check page break
                if y_curr > 250:
                    pdf.add_page()
                    pdf.chapter_title(f"{title} (cont.)")
                    y_curr = pdf.get_y()

            x = x_start + (col * (w_img + margin_x))
            
            # Place image
            pdf.image(img_path, x=x, y=y_curr, w=w_img)
            
            # Caption - Removed per user request 2026-02-10
            # pdf.set_xy(x, pdf.get_y() + 1)
            # pdf.set_font('Arial', 'I', 6)
            # pdf.cell(w_img, 3, os.path.basename(img_path), 0, 0, 'C')
            
            # Track height for row
            est_h = w_img * 0.75 
            if est_h > max_y_in_row: max_y_in_row = est_h
            
            col += 1
            
        pdf.ln(max_y_in_row + 10)

    # --- Saline EC0 ---
    if organized_paths.get("saline_ec0"):
        ec0 = organized_paths["saline_ec0"]
        add_plot_group_dynamic("Saline EC0 - PSD Signal", ec0.get("psd_signal"))
        add_plot_group_dynamic("Saline EC0 - PSD Noise", ec0.get("psd_noise"))
        add_plot_group_dynamic("Saline EC0 - Other Plots", ec0.get("others"))

    # --- Saline EC1 ---
    if organized_paths.get("saline_ec1"):
        ec1 = organized_paths["saline_ec1"]
        add_plot_group_dynamic("Saline EC1 - PSD Signal", ec1.get("psd_signal"))
        add_plot_group_dynamic("Saline EC1 - PSD Noise", ec1.get("psd_noise"))
        add_plot_group_dynamic("Saline EC1 - Other Plots", ec1.get("others"))

    # --- Impedance ---
    if organized_paths.get("impedance"):
        imp = organized_paths["impedance"]
        add_plot_group_dynamic("Impedance - Electrodes", imp.get("electrodes"))
        add_plot_group_dynamic("Impedance - Nitara", imp.get("nitara"))
        add_plot_group_dynamic("Impedance - Yield Response", imp.get("yield"))

    pdf_output_path = os.path.join(output_dir, "report.pdf")
    pdf.output(pdf_output_path)
    return pdf_output_path

if __name__ == "__main__":
    args = setup_args()
    os.makedirs(args.output, exist_ok=True)
    try:
        metadata, csv_summary, organized_paths = organize_files(args.dir, args.output)
        pdf_path = generate_pdf_report(args.output, metadata, csv_summary, organized_paths)
        print(f"Done! Report saved to {pdf_path}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
