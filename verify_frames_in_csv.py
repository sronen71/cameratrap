import os
import csv

FRAMES_DIR = "Frames"
PREVIEW_BATCH_DIR = "preview_batch"


def get_all_frame_folders():
    # Return all subfolders (recursively) under FRAMES_DIR, relative to FRAMES_DIR
    frame_folders = []
    for root, dirs, _ in os.walk(FRAMES_DIR):
        for d in dirs:
            rel_path = os.path.relpath(os.path.join(root, d), FRAMES_DIR)
            frame_folders.append(rel_path)
    return frame_folders


def get_all_csv_files():
    csv_files = []
    for root, _, files in os.walk(PREVIEW_BATCH_DIR):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))
    return csv_files


def get_all_file_names_from_csvs(csv_files):
    file_names = set()
    for csv_path in csv_files:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                file_name = row.get("file_name", "")
                if file_name:
                    file_names.add(file_name)
    return file_names


def main():
    frame_folders = get_all_frame_folders()
    csv_files = get_all_csv_files()
    file_names = get_all_file_names_from_csvs(csv_files)

    missing = []
    for folder in frame_folders:
        found = any(folder in file_name for file_name in file_names)
        if not found:
            missing.append(folder)

    if missing:
        print("Folders under Frames missing from any file_name in preview_batch CSVs:")
        for folder in missing:
            print(f"  {folder}")
    else:
        print("All frame folders are referenced in the preview_batch CSVs.")


if __name__ == "__main__":
    main()
