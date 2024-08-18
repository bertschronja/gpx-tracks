import os
from datetime import datetime

def cleanup_old_backups(directory, max_files_to_keep=10):
    files_with_times = []

    # Scan the directory and get files with their last modification times
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            # Get the last modification time of the file
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            files_with_times.append((mod_time, filename))
    
    # Sort files by modification time (oldest first)
    files_with_times.sort(key=lambda x: x[0])
    
    # Determine files to delete (all but the latest 'max_files_to_keep')
    files_to_delete = files_with_times[:-max_files_to_keep]

    # Print the number of files that will be deleted
    print(f"{len(files_to_delete)} files will be deleted")

    # Delete the old files
    for _, file in files_to_delete:
        file_path = os.path.join(directory, file)
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")