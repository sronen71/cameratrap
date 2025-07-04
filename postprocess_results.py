import os
import subprocess

# Parameters
results_dir = "results"
preview_dir = "preview"
preview_batch_dir = "preview_batch"
images_dir = "/home/sronen/code/wildaware/cameratrap"

# List all results files in results_dir
results_files = [f for f in os.listdir(results_dir) if f.endswith("smoothed.json")]

for results_file in results_files:
    results_path = os.path.join(results_dir, results_file)
    # Use a unique html output file per results file
    html_output_file = f"preview/preview_{os.path.splitext(results_file)[0]}.html"
    # Create a unique preview subdirectory for each results file
    preview_subdir = os.path.join(preview_dir, os.path.splitext(results_file)[0])
    os.makedirs(preview_subdir, exist_ok=True)
    # Visualization command
    cmd_vis = [
        "python",
        "-m",
        "megadetector.visualization.visualize_detector_output",
        results_path,
        preview_subdir,
        "--images_dir",
        images_dir,
        "--html_output_file",
        html_output_file,
    ]
    #print(f'Running: {" ".join(cmd_vis)}')
    subprocess.run(cmd_vis, check=True)
    # Create a unique preview_batch subdirectory for each results file
    preview_batch_subdir = os.path.join(
        preview_batch_dir, os.path.splitext(results_file)[0]
    )
    os.makedirs(preview_batch_subdir, exist_ok=True)
    # Batch postprocess command
    print(results_path,preview_batch_subdir)
    cmd_batch = [
        "python",
        "-m",
        "megadetector.postprocessing.postprocess_batch_results",
        results_path,
        preview_batch_subdir,
        "--num_images_to_sample",
        "-1",
        "--image_base_dir",
        images_dir,
        "--separate_animals_by_classification"
    ]
    print(f'Running: {" ".join(cmd_batch)}')
    subprocess.run(cmd_batch, check=True)
