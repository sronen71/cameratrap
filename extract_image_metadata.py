import os
from tqdm import tqdm
import pandas as pd
from PIL import Image
import re


def find_images(root_dir, exts={".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"}):
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if any(fname.lower().endswith(ext) for ext in exts):
                yield os.path.join(dirpath, fname)


def extract_datetime_and_temp(image_path):
    date_time = None
    temperature = None
    with Image.open(image_path) as img:
        exif = img._getexif()
        from PIL.ExifTags import TAGS

        meta = {TAGS.get(k, k): v for k, v in exif.items()}
        print(meta)
        exit()
        # DateTimeOriginal
        date_time = meta.get("DateTimeOriginal")
        # Print MakerNote type and length if present
        if "MakerNote" in meta:
            maker = meta["MakerNote"]
            if isinstance(maker, (bytes, bytearray)):
                decoded = maker.decode("ascii", errors="ignore")
            else:
                decoded = str(maker)
            m = re.search(r"temp[^:]*:?\s*([\-0-9.]+[CF])", decoded, re.IGNORECASE)
            if m:
                temperature = m.group(1)

    return date_time, temperature


def main():
    image_dir = "cameradata"
    output_csv = "image_metadata.csv"
    images = list(find_images(image_dir))
    metadata_list = []

    for img_path in tqdm(images):
        dt, temp = extract_datetime_and_temp(img_path)
        metadata_list.append(
            {"file_path": img_path, "DateTimeOriginal": dt, "Temperature": temp}
        )

    df = pd.DataFrame(metadata_list)
    df = df.sort_values("file_path")
    df.to_csv(output_csv, index=False)
    print(
        f"Extracted DateTimeOriginal and Temperature for {len(images)} images to {output_csv}"
    )


if __name__ == "__main__":
    main()
