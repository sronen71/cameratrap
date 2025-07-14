import os
import csv
import re
from bs4 import BeautifulSoup

PREVIEW_BATCH_DIR = "preview_batch"


# Helper to split words (alphanumeric, ignore punctuation, remove digits)
def split_words(text):
    # Remove digits, lowercase, split into words
    text = re.sub(r"\d+", "", text.lower())
    words = set(re.findall(r"\w+", text))
    # If 'gbh' in words, add 'great', 'blue', 'heron' as well
    if "gbh" in words:
        words.update(["great", "blue", "heron"])
    return words


def is_match(file_words, species_words):
    # Systematic species-to-filepath matching
    species_file_keywords = {
        "puma": {"lion"},
        "bird": {
            "crossbill",
            "jay",
            "goose",
            "gho",
            "gbh",
            "owl",
            "magpie",
            "crows",
            "heron",
            "mallard",
            "mallards",
            "goshawk",
            "crossbills",
            "kingfisher",
            "goshawk",
            "grosbeaks",
            "hawk",
            "raven",
            "woodpecker",
            "nutcracker",
            "chickadee",
            "dipper",
        },
        "passeriformes": {"raven"},
        "heron": {"gbh"},
        "turkey": {"turkeys"},
        "corvidae": {"crow", "crows", "raven", "ravens", "magpie", "nutcracker"},
        "corvus": {"crow", "crows", "raven", "ravens"},
        "coyote": {"coyotes"},
        "mule": {"md"},
        "human": {"me", "trespasser", "trespassers"},
        "blank": {"shoulder"},
        # Add more species and their matching file keywords here as needed
    }

    # If a keyword from species_file_keywords is in species_words, add all its value words to species_words
    for key, value_words in species_file_keywords.items():
        if key in species_words:
            species_words = species_words.union(value_words)

    # Standard match
    return bool(file_words & species_words)


def process_csv_file(csv_path):
    rows = []
    mismatches = []
    positives = 0
    negatives = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        if not reader:
            return 0, 0, []  # skip empty files
        fieldnames = list(reader[0].keys())
        has_match_col = "match" in fieldnames
        if not has_match_col:
            fieldnames = fieldnames + ["match"]
        for row in reader:
            file_name = row.get("file_name", "")
            species = row.get("species", "")
            file_words = split_words(file_name.lower())
            species_words = split_words(species.lower())
            match_val = is_match(file_words, species_words)
            # Only debug print if 'puma' is in file_words or species_words
            row["match"] = "true" if match_val else "false"
            if match_val:
                positives += 1
            else:
                negatives += 1
                mismatches.append(
                    {
                        "file_name": file_name,
                        "species": species,
                        "time": row.get("time", ""),
                    }
                )
            rows.append(row)
    # Always write back with updated match column
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return positives, negatives, mismatches


def highlight_mismatches_in_html_from_csv():
    # For each preview_batch subdir, read sequence_max_detections.csv and index.html
    for subdir in os.listdir(PREVIEW_BATCH_DIR):
        subdir_path = os.path.join(PREVIEW_BATCH_DIR, subdir)
        if not os.path.isdir(subdir_path):
            continue
        csv_path = os.path.join(subdir_path, "sequence_max_detections.csv")
        index_path = os.path.join(subdir_path, "index.html")
        if not (os.path.exists(csv_path) and os.path.exists(index_path)):
            continue
        # Collect all file_names with match == false
        mismatched_files = set()
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("match", "true").lower() == "false":
                    mismatched_files.add(row["file_name"])
        if not mismatched_files:
            continue
        # Update index.html
        with open(index_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            a = tds[0].find("a")
            if a and a.get("href"):
                # The href may be absolute or relative, but the file_name in csv is relative
                # So check if the file_name is a substring of the href
                for file_name in mismatched_files:
                    if file_name in a["href"]:
                        tr["style"] = tr.get("style", "") + ";background-color:#ffcccc;"
                        break
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(str(soup))


def main():
    total_positives = 0
    total_negatives = 0
    all_mismatches = []
    for root, _, files in os.walk(PREVIEW_BATCH_DIR):
        for file in files:
            if file.endswith(".csv"):
                csv_path = os.path.join(root, file)
                print(f"Processing {csv_path}")
                positives, negatives, mismatches = process_csv_file(csv_path)
                total_positives += positives
                total_negatives += negatives
                all_mismatches.extend(mismatches)
    # Write mismatches.csv
    if all_mismatches:
        with open("mismatches.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["file_name", "species", "time"])
            writer.writeheader()
            writer.writerows(all_mismatches)
        print(f"Wrote {len(all_mismatches)} mismatches to mismatches.csv")
        highlight_mismatches_in_html_from_csv()
    else:
        print("No mismatches found.")
    print(f"Total positives (true match): {total_positives}")
    print(f"Total negatives (false match): {total_negatives}")


if __name__ == "__main__":
    main()
