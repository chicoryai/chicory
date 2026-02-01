import shutil
import os

from services.utils.logger import logger


def copy_folder_content(source_folder, destination_folder):
    # Ensure source folder exists
    if not os.path.exists(source_folder):
        raise FileNotFoundError(f"Source folder '{source_folder}' does not exist.")

    # Create destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Iterate over items in the source folder
    for item in os.listdir(source_folder):
        source_path = os.path.join(source_folder, item)
        destination_path = os.path.join(destination_folder, item)

        # Check if it's a file or directory and copy accordingly
        try:
            if os.path.isfile(source_path):
                shutil.copy2(source_path, destination_path)  # copy2 preserves metadata
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)  # Python 3.8+
            else:
                logger.debug(f"Skipping unknown item: {source_path}")
        except Exception as e:
            logger.error(f"Failed to copy folder '{source_path}' to '{destination_path}'.")


def copy_files_with_txt_extension(source_folder, dest_folder):
    if not os.path.exists(source_folder):
        return

    # Ensure destination folder exists
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    # Recursively iterate over all files in the source folder and subdirectories
    for root, dirs, files in os.walk(source_folder):
        for file_name in files:
            # Construct full file path
            source_path = os.path.join(root, file_name)

            # Process only files with specific extensions
            if file_name.lower().endswith('.json') or file_name.lower().endswith('.dtd') or file_name.lower().endswith('.jsonl'):
                # Add .txt extension to destination file name
                file_name_without_ext = os.path.splitext(file_name)[0]
                dest_file_name = f"{file_name_without_ext}.txt"
                dest_path = os.path.join(dest_folder, dest_file_name)

                # Copy file
                shutil.copy(source_path, dest_path)
                logger.debug(f"Copied: {source_path} -> {dest_path}")


def get_folder_size(folder_path):
    """Calculate the total size of a folder and its contents."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # Skip broken symlinks
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size


def get_folder_info(base_folder):
    """Get folder sizes for the base folder."""
    folder_info = []
    for item in os.listdir(base_folder):
        item_path = os.path.join(base_folder, item)
        if os.path.isdir(item_path):
            folder_size = get_folder_size(item_path)
        else:
            folder_size = os.path.getsize(item_path)
        folder_info.append({
            "Name": item,
            "Type": "Folder" if os.path.isdir(item_path) else "File",
            "Size": folder_size
        })
    return folder_info
