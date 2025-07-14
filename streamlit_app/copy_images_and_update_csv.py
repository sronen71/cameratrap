import os
import pandas as pd
import shutil

# --- CONFIG ---
CSV_PATH = "../preview_batch/predictions_202506_smoothed/merged_202506.csv"  # Update this to your actual CSV path
SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DST_IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
UPDATED_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "updated_" + os.path.basename(CSV_PATH)
)

os.makedirs(DST_IMG_DIR, exist_ok=True)

# Read CSV
df = pd.read_csv(CSV_PATH)

# Track mapping for updating CSV
new_paths = []

for img_path in df["sample_image"]:
    if not isinstance(img_path, str) or not img_path.startswith("Frames/"):
        new_paths.append(img_path)
        continue
    src = os.path.join(SRC_ROOT, img_path)
    dst = os.path.join(DST_IMG_DIR, img_path)  # preserve subfolders
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        new_paths.append(os.path.relpath(dst, os.path.dirname(__file__)))
    else:
        print(f"Warning: {src} not found.")
        new_paths.append("")

# Update CSV and save

df["sample_image"] = new_paths
df.to_csv(UPDATED_CSV_PATH, index=False)
print(
    f"Done. Images copied to {DST_IMG_DIR} and updated CSV saved as {UPDATED_CSV_PATH}"
)
