import py7zr
import os
import sys

# Path to the 7z archive
archive_path = '/Users/tinyclaw/.openclaw/media/inbound/file_22---4081274c-381a-4653-9be4-092b5309efb4.7z'
output_dir = 'skills/plot-organizer/output/new_structure_test'

print(f"Extracting {archive_path} to {output_dir}...")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

try:
    with py7zr.SevenZipFile(archive_path, 'r') as archive:
        archive.extractall(path=output_dir)
    print("Extraction complete.")
except Exception as e:
    print(f"Error extracting archive: {e}")
