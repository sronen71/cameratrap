import os
import subprocess

# Parameters
results_dir = "results"
md_results_dir = "results_md"
os.makedirs(md_results_dir, exist_ok=True)

# List all results files in results_dir
results_files = [f for f in os.listdir(results_dir) if f.endswith(".json")]

for results_file in results_files:
    input_path = os.path.join(results_dir, results_file)
    output_path = os.path.join(md_results_dir, f"md_{results_file}")
    cmd = [
        "python",
        "-m",
        "speciesnet.scripts.speciesnet_to_md",
        input_path,
        output_path,
    ]
    print(f'Running: {" ".join(cmd)}')
    subprocess.run(cmd, check=True)
