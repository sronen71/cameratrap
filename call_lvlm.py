import os
import base64
import json
import re
import argparse
import io
from PIL import Image, ExifTags
from pathlib import Path
import csv
import logging

# -----------------------------
# Configurable Parameters
# -----------------------------

DEFAULT_ROOT = "Frames"
SAMPLES_PER_FOLDER = 5
MAX_IMAGE_HEIGHT = 720


# -----------------------------
# Utilities
# -----------------------------
def load_api_key():
    return os.getenv("openai_api_key")


def find_image_folders(root_dir):
    image_folders = []
    for dirpath, _, filenames in os.walk(root_dir):
        if any(f.lower().endswith(".jpg") for f in filenames):
            # Remove trailing slash
            image_folders.append(dirpath.rstrip(os.sep))
    return sorted(image_folders)


def get_csv_primary_image(folder_path):

    folder_path = Path(folder_path)
    path_parts = folder_path.parts

    month_folder = path_parts[1]

    csv_path = (
        Path("preview_batch")
        / f"predictions_{month_folder}_smoothed"
        / "sequence_max_detections.csv"
    )

    if not csv_path.exists():
        return None

    with open(csv_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            file_path = Path(row["file_name"])
            if file_path.parts[:-1] == folder_path.parts:
                return file_path
    return None


def sample_images(folder_path, n=SAMPLES_PER_FOLDER):
    all_jpgs = [
        Path(folder_path) / f
        for f in os.listdir(folder_path)
        if f.lower().endswith(".jpg")
    ]
    all_jpgs = sorted(all_jpgs)
    if n >= len(all_jpgs):
        return all_jpgs
    # Uniformly sample n images
    step = len(all_jpgs) / n
    sampled = [all_jpgs[int(i * step)] for i in range(n)]
    # Try to get primary image from CSV
    primary = get_csv_primary_image(folder_path)
    if primary and primary not in sampled:
        sampled.append(primary)
    sampled = sorted(sampled)
    return sampled


def resize_image_if_needed(image_path, max_height=MAX_IMAGE_HEIGHT):
    """
    Resize image to have a maximum height while maintaining aspect ratio.
    Returns the resized image as bytes.
    """
    with Image.open(image_path) as img:
        # Convert to RGB if needed (handles RGBA, grayscale, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Only resize if height exceeds max_height
        if img.height > max_height:
            # Calculate new width maintaining aspect ratio
            aspect_ratio = img.width / img.height
            new_height = max_height
            new_width = int(new_height * aspect_ratio)

            # Resize the image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(
                f"Resized {os.path.basename(image_path)} from original size to {new_width}x{new_height}"
            )
        else:
            print(
                f"No resize needed for {os.path.basename(image_path)} (size: {img.width}x{img.height})"
            )

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)
        return img_bytes.getvalue()


def get_image_datetime(image_path):
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if not exif:
                return None
            for tag, value in exif.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if decoded == "DateTimeOriginal":
                    return value
                if decoded == "DateTime":
                    return value
    except Exception:
        return None
    return None


# -----------------------------
# Prompt Construction
# -----------------------------


def build_prompt():
    return """
You are a wildlife ecologist analyzing a camera trap image sequence'.
The location is near Bailey or Evergreen, Colorado — use this to inform habitat, species, and behavior.

Your goals:
- Identify **each animal** seen across the sequence.
- Estimate: **species**, **age**, **health**, **primary activity**, and **interactions**.
- Use consistent labels (e.g., "elk_1", "elk_calf_1").
- If the same animal appears in multiple frames, label it once.
- Animals may pass through sequentially; avoid double-counting unless clearly distinct.
- Extract **date, time, and temperature from overlay** if visible.
- if weather or interaction etc is unknown, don't mention that in the summary.

Return one **JSON object** in this format (no extra explanation):

```json
{{
  "date": "YYYY-MM-DD",                // from image overlay if shown
  "time": "HH:MM:SS",                  // or "day"/"night"
  "habitat": "e.g., aspen meadow, riparian zone",
  "temperature": "e.g., 43F or unknown",
  "weather": "e.g., sunny, snowy, raining, cold, hot,unknown
  "count": total number of distinct animals seen,
  "individuals": [
    {{
      "id": "elk_1",
      "species": "Cervus canadensis (elk)",
      "sex":"female",                   // one of : male,female,unknown.
      "approx_age": "adult",          // one of: baby, young, adult, old
      "health": "healthy",            // or: thin, limping, wounded, etc.
      "activity": "grazing",          // one of: grazing, browsing, walking, running, resting, alert, drinking, social, following, chasing, sniffing, playing, fleeing, nursing, vocalizing, marking
      "interaction": "near elk_calf_1",  // or "none"
      "notes": "optional observations"
    }}
  ]
   "summary": "A short paragraph summarizing the scene in natural language, suitable for a field biologist.
   Mention key species, behaviors, habitat, group dynamics, and anything noteworthy like alertness, health, or time of day."
}}
}}
""".strip()


# -----------------------------
# Vision Model Integration (OpenAI GPT-4o)
# -----------------------------
def extract_json(text):
    """
    Extract and parse a JSON object from a language model response.
    Handles Markdown-wrapped code blocks and extra formatting.
    """
    # Try to find a JSON object inside triple backticks (Markdown-style)
    match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Fallback: try to find any JSON object in the text
        match = re.search(r"({.*})", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            raise ValueError("No valid JSON found in the response.")

    # Parse the cleaned JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        print("Extracted string:", json_str)
        raise


def ask_openai(prompt_text, image_paths, client):
    # Upload image files or serve from local web server
    # For now, encode directly as base64 with MIME type
    def image_payload(path):
        resized_image_bytes = resize_image_if_needed(path)
        base64_image = base64.b64encode(resized_image_bytes).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        }

    # Create message content list: prompt text first
    content = [{"type": "text", "text": prompt_text}]
    # Add each image with an explicit order marker (always) and EXIF time if available
    for i, img_path in enumerate(image_paths):
        exif_time = get_image_datetime(img_path)
        label = f"Image {i+1}"
        if exif_time:
            label + f" EXIF datetime: {exif_time}):"
        print(label)
        content.append({"type": "text", "text": label})
        content.append(image_payload(img_path))

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        temperature=0.0,
        max_tokens=2048,
    )

    return response


# -----------------------------
# Main Processing Pipeline
# -----------------------------


def setup_logger(log_path):
    logger = logging.getLogger("wildlife_lvlm")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, mode="w")
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.handlers = []  # Remove any existing handlers
    logger.addHandler(handler)
    logger.info("folder\tinput_tokens\toutput_tokens")
    return logger


def process_folder(folder, api_key, dry_run=False, logger=None, client=None):
    images = sample_images(folder)
    if not images:
        print(f"No images sampled for {folder}, skipping output.")
        return None, None
    prompt = build_prompt()
    print(f"Sampled {len(images)} images from {folder}.")
    image_frames = [Path(img_path).name for img_path in images]
    if dry_run:
        print("[DRY RUN] Skipping OpenAI API call.")
        analysis_results = {
            "date": "unknown",
            "time": "unknown",
            "habitat": "unknown",
            "temperature": "unknown",
            "weather": "unknown",
            "count": 0,
            "individuals": [],
            "summary": "[DRY RUN] No analysis performed",
        }
        log_entry = {
            "folder": folder,
            "input_tokens": None,
            "output_tokens": None,
        }
    else:
        try:
            response = ask_openai(prompt, images, client)
            response_content = response.choices[0].message.content
            print(f"Response content: {response_content}")
            analysis_results = extract_json(response_content)
            log_entry = {
                "folder": folder,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        except Exception as e:
            import sys
            import traceback

            print(f"\n❌ Error processing folder {folder}: {e}")
            if (
                "AuthenticationError" in str(type(e))
                or "401" in str(e)
                or "API key" in str(e)
            ):
                print(
                    "\nAuthentication error: Please check your OpenAI API key and try again."
                )
                sys.exit(1)
            else:
                traceback.print_exc()
                sys.exit(1)
    result = {
        "folder": folder,
        "image_frames": image_frames,
        "analysis": analysis_results,
        "metadata": {
            "total_images_in_folder": len(
                [f for f in os.listdir(folder) if f.lower().endswith(".jpg")]
            ),
            "sampled_images": len(images),
        },
    }
    # Log immediately if logger is provided
    if logger is not None:
        logger.info(
            f"{folder}\t{log_entry['input_tokens']}\t{log_entry['output_tokens']}"
        )
    return result, log_entry


def process_month(month, month_folders, api_key, dry_run=False, logger=None):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    results = []
    log_entries = []
    for folder in month_folders:
        print(f"\nProcessing: {folder}")
        result, log_entry = process_folder(folder, api_key, dry_run, logger, client)
        if result is not None:
            results.append(result)
            log_entries.append(log_entry)
    return results, log_entries


def process_all_folders(root_dir, api_key, dry_run=False):
    folders = find_image_folders(root_dir)
    print(f"Found {len(folders)} folders with images.")
    from collections import defaultdict

    month_to_folders = defaultdict(list)
    for folder in folders:
        path_parts = Path(folder).parts
        month = path_parts[1]
        month_to_folders[month].append(folder)
    all_log_entries = []
    log_path = Path("lvlm") / "wildlife_lvlm_log.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(log_path)
    for month, month_folders in month_to_folders.items():
        results, log_entries = process_month(
            month, month_folders, api_key, dry_run, logger
        )
        output_folder = Path("lvlm")
        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / f"{month}.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Metadata for {month} saved to: {output_path}")
        all_log_entries.extend(log_entries)
    # Calculate total tokens
    total_input_tokens = sum(e["input_tokens"] or 0 for e in all_log_entries)
    total_output_tokens = sum(e["output_tokens"] or 0 for e in all_log_entries)
    print(f"\n🔢 Total input tokens: {total_input_tokens}")
    print(f"🔢 Total output tokens: {total_output_tokens}")
    # Append totals to log file
    logger.info(f"TOTAL\t{total_input_tokens}\t{total_output_tokens}")
    print(f"\n📝 Log saved to: {log_path}")


# -----------------------------
# CLI Entry Point
# -----------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate wildlife metadata using vision-language model."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=DEFAULT_ROOT,
        help="Root folder containing image subfolders",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, do not call the OpenAI API, just print sampled images and prompt.",
    )
    api_key = load_api_key()
    args = parser.parse_args()
    process_all_folders(args.root, api_key, dry_run=args.dry_run)
