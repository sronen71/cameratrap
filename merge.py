import pandas as pd
import json
import os
import glob


def merge_json_and_csv(
    json_month: str,
    lvlm_dir="lvlm",
    preview_batch_dir="preview_batch",
    output_path=None,
):
    """
    Merge a month JSON from lvlm/ with the corresponding CSV from preview_batch/.
    json_month: e.g. '202506.json'
    Output is written to the same folder as the CSV.
    """
    # Find JSON path
    json_path = os.path.join(lvlm_dir, json_month)
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    # Find corresponding CSV path
    month = os.path.splitext(json_month)[0].replace("predictions_", "")
    csv_glob = os.path.join(
        preview_batch_dir,
        f"predictions_{month}_smoothed",
        "sequence_max_detections.csv",
    )
    csv_candidates = glob.glob(csv_glob)
    if not csv_candidates:
        raise FileNotFoundError(f"CSV file not found for month {month} in {csv_glob}")
    csv_path = csv_candidates[0]
    csv_folder = os.path.dirname(csv_path)
    if output_path is None:
        output_path = os.path.join(
            csv_folder, f"merged_{os.path.splitext(json_month)[0]}.csv"
        )
    # Load CSV
    csv_df = pd.read_csv(csv_path)
    # Load JSON
    with open(json_path, "r") as f:
        json_data = json.load(f)
    # Normalize JSON into a DataFrame for comparison
    records = []
    for entry in json_data:
        folder = entry["folder"]
        count = entry["analysis"]["count"]
        species = ", ".join(
            set([ind["species"] for ind in entry["analysis"]["individuals"]])
        )
        summary = entry["analysis"]["summary"]
        individuals = entry["analysis"]["individuals"]
        sample_image = (
            os.path.join(folder, entry["image_frames"][0])
            if entry["image_frames"]
            else None
        )
        records.append(
            {
                "folder": folder,
                "gpt_species": species,
                "gpt_count": count,
                "gpt_summary": summary,
                "gpt_individuals": individuals,
                "sample_image": sample_image,
            }
        )
    json_df = pd.DataFrame(records)
    # Merge CSV and JSON on folder
    csv_df["folder"] = csv_df["file_name"].apply(lambda x: os.path.dirname(x))
    merged_df = pd.merge(csv_df, json_df, on="folder", how="outer")
    merged_df.to_csv(output_path, index=False)
    print(f"Merged data written to {output_path}")


def merge_all_json_and_csv(
    lvlm_dir="lvlm", preview_batch_dir="preview_batch", output_dir=None
):
    """
    Merge all month JSONs from lvlm/ with their corresponding CSVs from preview_batch/.
    Writes one merged CSV per month in the same folder as the CSV.
    """
    json_files = [
        f for f in os.listdir(lvlm_dir) if f.endswith(".json") and not f.startswith(".")
    ]
    if not json_files:
        print(f"No JSON files found in {lvlm_dir}")
        return
    for json_month in sorted(json_files):
        # Find corresponding CSV path
        month = os.path.splitext(json_month)[0].replace("predictions_", "")
        csv_glob = os.path.join(
            preview_batch_dir,
            f"predictions_{month}_smoothed",
            "sequence_max_detections.csv",
        )
        csv_candidates = glob.glob(csv_glob)
        if not csv_candidates:
            print(
                f"Skipping {json_month}: CSV file not found for month {month} in {csv_glob}"
            )
            continue
        csv_path = csv_candidates[0]
        csv_folder = os.path.dirname(csv_path)
        output_path = os.path.join(
            csv_folder, f"merged_{os.path.splitext(json_month)[0]}.csv"
        )
        try:
            merge_json_and_csv(
                json_month,
                lvlm_dir=lvlm_dir,
                preview_batch_dir=preview_batch_dir,
                output_path=output_path,
            )
        except Exception as e:
            print(f"Skipping {json_month}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Merge JSON and CSV for all months or a given month."
    )
    parser.add_argument(
        "--json_month",
        type=str,
        default=None,
        help="Month JSON file, e.g. 202506.json. If not set, merge all months.",
    )
    parser.add_argument(
        "--lvlm_dir",
        type=str,
        default="lvlm",
        help="Directory containing JSON files",
    )
    parser.add_argument(
        "--preview_batch_dir",
        type=str,
        default="preview_batch",
        help="Directory containing preview_batch folders",
    )
    args = parser.parse_args()
    if args.json_month:
        merge_json_and_csv(
            args.json_month,
            lvlm_dir=args.lvlm_dir,
            preview_batch_dir=args.preview_batch_dir,
        )
    else:
        merge_all_json_and_csv(
            lvlm_dir=args.lvlm_dir,
            preview_batch_dir=args.preview_batch_dir,
        )
