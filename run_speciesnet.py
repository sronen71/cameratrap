import os
import subprocess
import argparse

# Parameters
country = "USA"
admin1_region = "CO"

# Helper: check if a folder contains images
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"}


def contains_images(path):
    return any(
        f.lower().endswith(tuple(IMAGE_EXTS))
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f))
    )

def main(base_dir):
    # If base_dir contains images, run on base_dir itself

    os.makedirs("results", exist_ok=True)
    if contains_images(base_dir):
        folders = [base_dir]
    else:
        # Otherwise, run on each subfolder
        folders = [
            os.path.join(base_dir, f)
            for f in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, f))
        ]

    for folder_path in folders:
        folder_name = os.path.basename(folder_path)
        output_json = f"results/predictions_{folder_name}.json"
        cmd = [
            "python",
            "-m",
            "speciesnet.scripts.run_model",
            "--folders",
            folder_path,
            "--predictions_json",
            output_json,
            "--country",
            country,
            "--admin1_region",
            admin1_region,
            # "--geo_distribute",
        ]
        print(f'Running: {" ".join(cmd)}')
        subprocess.run(cmd, check=True)

        cmd=[
                "python",
                "-m",
                "speciesnet.scripts.sequence_smoothing",
                "--predictions_json",
                output_json,
        ]
        print(f'Running: {" ".join(cmd)}')
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    default_base_dir="cameradata/DCIM"
    #default_base_dir="cameradata/DCIM/100MEDIA"
    #default_base_dir="cameradata/example"
    

    parser = argparse.ArgumentParser(description="Run SpeciesNet on a directory of images.")
    parser.add_argument("--base_dir", type=str, default=default_base_dir,
                        help="The base directory containing image folders.")
    args = parser.parse_args()
    main(args.base_dir)
