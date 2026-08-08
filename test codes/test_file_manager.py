import os 

def open_file(file_path):
    """
    Opens the specified file using the default application.

    Args:
        file_path (str): The path to the file to open.
    """
    try:
        os.startfile(file_path)
        print(f"Opening {file_path} with the default application.")
    except Exception as e:
        print(f"An error occurred while trying to open the file: {e}")

def open_directory(directory_path):
    """
    Opens the specified directory in the default file explorer.

    Args:
        directory_path (str): The path to the directory to open.
    """
    try:
        os.startfile(directory_path)
        print(f"Opening {directory_path} in the default file explorer.")
    except Exception as e:
        print(f"An error occurred while trying to open the directory: {e}")

def delete_file(file_path):
    """
    Deletes the specified file.

    Args:
        file_path (str): The path to the file to delete.
    """
    try:
        os.remove(file_path)
        print(f"Deleted {file_path}.")
    except Exception as e:
        print(f"An error occurred while trying to delete the file: {e}")

def copy_file(source_path, destination_path):
    """
    Copies a file from the source path to the destination path.

    Args:
        source_path (str): The path to the source file.
        destination_path (str): The path to the destination file.
    """
    try:
        with open(source_path, 'rb') as source_file:
            with open(destination_path, 'wb') as destination_file:
                destination_file.write(source_file.read())
        print(f"Copied {source_path} to {destination_path}.")
    except Exception as e:
        print(f"An error occurred while trying to copy the file: {e}")

def move_file(source_path, destination_path):
    """
    Moves a file from the source path to the destination path.

    Args:
        source_path (str): The path to the source file.
        destination_path (str): The path to the destination file.
    """
    try:
        os.rename(source_path, destination_path)
        print(f"Moved {source_path} to {destination_path}.")
    except Exception as e:
        print(f"An error occurred while trying to move the file: {e}")

def rename_file(old_path, new_path):
    """
    Renames a file from the old path to the new path.

    Args:
        old_path (str): The current path of the file.
        new_path (str): The new path of the file.
    """
    try:
        os.rename(old_path, new_path)
        print(f"Renamed {old_path} to {new_path}.")
    except Exception as e:
        print(f"An error occurred while trying to rename the file: {e}")

def create_directory(directory_path):
    """
    Creates a new directory at the specified path.

    Args:
        directory_path (str): The path where the new directory will be created.
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        print(f"Created directory {directory_path}.")
    except Exception as e:
        print(f"An error occurred while trying to create the directory: {e}")

def create_file(file_path):
    """
    Creates a new file at the specified path.

    Args:
        file_path (str): The path where the new file will be created.
    """
    try:
        with open(file_path, 'w') as new_file:
            new_file.write("")  # Create an empty file
        print(f"Created file {file_path}.")
    except Exception as e:
        print(f"An error occurred while trying to create the file: {e}")