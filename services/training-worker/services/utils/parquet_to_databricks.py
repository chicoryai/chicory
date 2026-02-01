import os
import shutil

def find_and_copy_parquet_files(root_folder, destination_folder):
    # Ensure the destination directory exists
    os.makedirs(destination_folder, exist_ok=True)

    # Traverse through root_folder and its subfolders
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith(".parquet"):
                source_path = os.path.join(root, file)
                destination_path = os.path.join(destination_folder, file)
                try:
                    shutil.copy2(source_path, destination_path)
                    print(f"Copied: {source_path} -> {destination_path}")
                except Exception as e:
                    print (f"Failed: {source_path} -> {destination_path}")

# Set the root folder and destination folder
root_folder = '/Users/sarkarsaurabh.27/Documents/Projects/brewsearch/data/thredup/raw/data'
destination_folder = os.path.join(root_folder, 'all_parquets')

# Execute the function
find_and_copy_parquet_files(root_folder, destination_folder)