"""
tools/file_tools.py
File & directory operations (existing 17 tools migrated + 7 new tools).

NEW tools: zip_files, unzip_files, extract_archive, get_archive_contents,
           batch_rename_files, find_duplicate_files, diff_files
BUG FIX:  move_file now has @tool decorator
"""

import os
import re
import shutil
import hashlib
import difflib
import zipfile
import tarfile
import datetime
import time
from langchain_core.tools import tool


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING TOOLS (migrated from agent_tools.py)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def open_file(file_path: str) -> str:
    """Opens the specified file using the default application.

    Args:
        file_path: The path to the file to open.
    """
    try:
        os.startfile(file_path)
        return f"Opening {file_path} with the default application."
    except Exception as e:
        return f"An error occurred while trying to open the file: {e}"


@tool
def open_directory(directory_path: str) -> str:
    """Opens the specified directory in the default file explorer.

    Args:
        directory_path: The path to the directory to open.
    """
    try:
        os.startfile(directory_path)
        return f"Opening {directory_path} in the default file explorer."
    except Exception as e:
        return f"An error occurred while trying to open the directory: {e}"


@tool
def delete_file(file_path: str) -> str:
    """Deletes the specified file.

    Args:
        file_path: The path to the file to delete.
    """
    try:
        os.remove(file_path)
        return f"Deleted {file_path}."
    except Exception as e:
        return f"An error occurred while trying to delete the file: {e}"


@tool
def copy_file(source_path: str, destination_path: str) -> str:
    """Copies a file from the source path to the destination path.

    Args:
        source_path: The path to the source file.
        destination_path: The path to the destination file.
    """
    try:
        shutil.copy2(source_path, destination_path)
        return f"Copied {source_path} to {destination_path}."
    except Exception as e:
        return f"An error occurred while trying to copy the file: {e}"


@tool
def move_file(source_path: str, destination_path: str) -> str:
    """Moves a file from the source path to the destination path.

    Args:
        source_path: The path to the source file.
        destination_path: The path to the destination file or folder.
    """
    try:
        if not os.path.exists(source_path):
            return f"Move failed: source file does not exist at {source_path}"
        os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
        shutil.move(source_path, destination_path)
        return f"Moved {source_path} to {destination_path}."
    except Exception as e:
        return f"An error occurred while trying to move the file: {e}"


@tool
def rename_file(old_path: str, new_path: str) -> str:
    """Renames a file from the old path to the new path.

    Args:
        old_path: The current path of the file.
        new_path: The new path of the file.
    """
    try:
        os.rename(old_path, new_path)
        return f"Renamed {old_path} to {new_path}."
    except Exception as e:
        return f"An error occurred while trying to rename the file: {e}"


@tool
def create_directory(directory_path: str) -> str:
    """Creates a new directory at the specified path.

    Args:
        directory_path: The path where the new directory will be created.
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return f"Created directory {directory_path}."
    except Exception as e:
        return f"An error occurred while trying to create the directory: {e}"


@tool
def create_file(file_path: str, content: str = "") -> str:
    """Creates a new file with optional content. Returns the absolute path used."""
    try:
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created file at absolute path: {abs_path}"
    except Exception as e:
        return f"An error occurred while trying to create the file: {e}"


@tool
def write_to_file(file_path: str, content: str, mode: str = "w") -> str:
    """Writes text content to a file. Creates the file if it doesn't exist.

    Args:
        file_path: The path to the file.
        content: The text to write.
        mode: 'w' to overwrite, 'a' to append. Defaults to 'w'.
    """
    try:
        with open(file_path, "w" if mode == "w" else "a", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} characters to {file_path}."
    except Exception as e:
        return f"An error occurred while writing to the file: {e}"


@tool
def read_file_content(file_path: str, max_lines: int = 100) -> str:
    """Reads the content of a text file and returns it as a string.

    Args:
        file_path: The path to the file to read.
        max_lines: Maximum number of lines to read. Defaults to 100.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = []
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip("\n"))
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def search_files(root_path: str, query: str) -> str:
    """Searches for files inside a directory recursively by filename.

    Args:
        root_path: Starting directory path.
        query: Text to search for in file names.
    """
    try:
        results = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if query.lower() in file.lower():
                    results.append(os.path.join(root, file))
        return "\n".join(results[:50]) if results else "No matching files found."
    except Exception as e:
        return f"Search error: {e}"


@tool
def find_files_by_extension(root_path: str, extension: str) -> str:
    """Finds files with a specific extension recursively.

    Args:
        root_path: Starting directory path.
        extension: File extension (e.g., '.py', '.pdf').
    """
    try:
        results = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    results.append(os.path.join(root, file))
        return "\n".join(results[:100]) if results else "No files found."
    except Exception as e:
        return f"Error: {e}"


@tool
def list_directory_tree(folder_path: str, depth: int = 2) -> str:
    """Creates a directory tree view.

    Args:
        folder_path: Root folder.
        depth: Maximum folder depth (default 2).
    """
    try:
        output = []
        base_depth = folder_path.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(folder_path):
            current_depth = root.count(os.sep) - base_depth
            if current_depth > depth:
                dirs.clear()
                continue
            indent = "    " * current_depth
            output.append(f"{indent}[{os.path.basename(root)}]")
            for file in files[:10]:
                output.append(f"{indent} └── {file}")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"


@tool
def find_large_files(root_path: str, size_mb: int = 100) -> str:
    """Finds files larger than the specified size.

    Args:
        root_path: Search location.
        size_mb: Minimum file size in MB (default 100).
    """
    try:
        results = []
        limit = size_mb * 1024 * 1024
        for root, _, files in os.walk(root_path):
            for file in files:
                path = os.path.join(root, file)
                try:
                    size = os.path.getsize(path)
                    if size > limit:
                        results.append(f"{path} ({size / 1024 / 1024:.2f} MB)")
                except Exception:
                    pass
        return "\n".join(results[:50]) if results else "No large files found."
    except Exception as e:
        return f"Error: {e}"


@tool
def find_recent_files(root_path: str, days: int = 7) -> str:
    """Finds files modified within the last N days.

    Args:
        root_path: Search location.
        days: Number of days to look back (default 7).
    """
    try:
        results = []
        now = time.time()
        limit = days * 24 * 60 * 60
        for root, _, files in os.walk(root_path):
            for file in files:
                path = os.path.join(root, file)
                try:
                    modified = os.path.getmtime(path)
                    if now - modified < limit:
                        date = datetime.datetime.fromtimestamp(modified)
                        results.append(f"{path} | {date}")
                except Exception:
                    pass
        return "\n".join(results[:50]) if results else "No recent files found."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_file_info(file_path: str) -> str:
    """Returns file metadata: size, created date, modified date.

    Args:
        file_path: The path to the file.
    """
    try:
        size = os.path.getsize(file_path)
        created = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
        modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        return (
            f"File: {file_path}\n"
            f"Size: {size / 1024:.2f} KB\n"
            f"Created: {created}\n"
            f"Modified: {modified}"
        )
    except Exception as e:
        return f"Error: {e}"


@tool
def analyze_folder(folder_path: str) -> str:
    """Calculates folder statistics: total files, folders, and size.

    Args:
        folder_path: Path to the folder to analyze.
    """
    try:
        files_count = 0
        folder_count = 0
        total_size = 0
        for root, dirs, files in os.walk(folder_path):
            folder_count += len(dirs)
            for file in files:
                files_count += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, file))
                except Exception:
                    pass
        return (
            f"Folder: {folder_path}\n"
            f"Files: {files_count}\n"
            f"Folders: {folder_count}\n"
            f"Total Size: {total_size / 1024 / 1024:.2f} MB"
        )
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# NEW TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def zip_files(source_paths: str, output_zip: str) -> str:
    """Compresses files or folders into a ZIP archive.

    Args:
        source_paths: Comma-separated list of file/folder paths to compress.
        output_zip: Path for the output .zip file (e.g., 'archive.zip').
    """
    try:
        paths = [p.strip() for p in source_paths.split(",")]
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for file in files:
                            full = os.path.join(root, file)
                            zf.write(full, os.path.relpath(full, os.path.dirname(path)))
                elif os.path.isfile(path):
                    zf.write(path, os.path.basename(path))
                else:
                    return f"❌ Path not found: {path}"
        size_mb = os.path.getsize(output_zip) / (1024 * 1024)
        return f"✅ Created ZIP: {output_zip} ({size_mb:.2f} MB)"
    except Exception as e:
        return f"❌ Error creating ZIP: {e}"


@tool
def unzip_files(zip_path: str, output_folder: str = "") -> str:
    """Extracts a ZIP archive to a folder.

    Args:
        zip_path: Path to the .zip file.
        output_folder: Destination folder (defaults to same directory as zip).
    """
    try:
        if not output_folder:
            output_folder = os.path.splitext(zip_path)[0]
        os.makedirs(output_folder, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(output_folder)
            names = zf.namelist()
        return f"✅ Extracted {len(names)} files to: {output_folder}"
    except Exception as e:
        return f"❌ Error extracting ZIP: {e}"


@tool
def extract_archive(archive_path: str, output_folder: str = "") -> str:
    """Extracts ZIP, TAR, TAR.GZ, or TAR.BZ2 archives.

    Args:
        archive_path: Path to the archive file.
        output_folder: Destination folder (defaults to archive name without extension).
    """
    try:
        if not output_folder:
            # Strip common double extensions like .tar.gz
            base = archive_path
            for ext in (".tar.gz", ".tar.bz2", ".tar.xz", ".zip", ".tar"):
                if base.lower().endswith(ext):
                    base = base[: -len(ext)]
                    break
            output_folder = base
        os.makedirs(output_folder, exist_ok=True)

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(output_folder)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(output_folder)
        else:
            return f"❌ Unsupported archive format: {archive_path}"

        return f"✅ Extracted to: {output_folder}"
    except Exception as e:
        return f"❌ Error extracting archive: {e}"


@tool
def get_archive_contents(archive_path: str) -> str:
    """Lists files inside a ZIP or TAR archive without extracting.

    Args:
        archive_path: Path to the archive file.
    """
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                names = zf.namelist()
            header = f"📦 ZIP Archive: {os.path.basename(archive_path)} ({len(names)} files)\n"
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tf:
                names = tf.getnames()
            header = f"📦 TAR Archive: {os.path.basename(archive_path)} ({len(names)} files)\n"
        else:
            return "❌ Unsupported archive format."
        return header + "\n".join(names[:100])
    except Exception as e:
        return f"❌ Error reading archive: {e}"


@tool
def batch_rename_files(
    folder_path: str,
    prefix: str = "",
    suffix: str = "",
    start_number: int = 1,
    extension_filter: str = "",
) -> str:
    """Bulk renames files in a folder with optional prefix, suffix, and counter.

    Args:
        folder_path: Path to the folder containing files to rename.
        prefix: Text to add before the filename (optional).
        suffix: Text to add after the filename, before extension (optional).
        start_number: Starting counter number for sequential naming (default 1, use 0 to disable).
        extension_filter: Only rename files with this extension e.g. '.jpg' (optional, renames all if empty).
    """
    try:
        if not os.path.isdir(folder_path):
            return f"❌ Folder not found: {folder_path}"

        files = sorted([
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
            and (not extension_filter or f.lower().endswith(extension_filter.lower()))
        ])

        if not files:
            return "No matching files found in the folder."

        renamed = []
        for i, filename in enumerate(files):
            name, ext = os.path.splitext(filename)
            counter = f"_{start_number + i:03d}" if start_number > 0 else ""
            new_name = f"{prefix}{name}{suffix}{counter}{ext}"
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_name)
            os.rename(old_path, new_path)
            renamed.append(f"  {filename}  →  {new_name}")

        return f"✅ Renamed {len(renamed)} files:\n" + "\n".join(renamed[:30])
    except Exception as e:
        return f"❌ Error batch renaming: {e}"


@tool
def find_duplicate_files(root_path: str) -> str:
    """Finds duplicate files by content hash within a directory.

    Args:
        root_path: Directory to search for duplicates.
    """
    try:
        hash_map: dict[str, list[str]] = {}

        for root, _, files in os.walk(root_path):
            for file in files:
                path = os.path.join(root, file)
                try:
                    h = hashlib.md5()
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            h.update(chunk)
                    digest = h.hexdigest()
                    hash_map.setdefault(digest, []).append(path)
                except Exception:
                    pass

        duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}

        if not duplicates:
            return "✅ No duplicate files found."

        lines = [f"🔍 Found {len(duplicates)} groups of duplicates:\n"]
        for digest, paths in list(duplicates.items())[:20]:
            lines.append(f"  Hash: {digest[:12]}...")
            for p in paths:
                lines.append(f"    📄 {p}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def diff_files(file_path_1: str, file_path_2: str) -> str:
    """Compares two text files and shows the differences line-by-line.

    Args:
        file_path_1: Path to the first file.
        file_path_2: Path to the second file.
    """
    try:
        with open(file_path_1, "r", encoding="utf-8") as f1:
            lines1 = f1.readlines()
        with open(file_path_2, "r", encoding="utf-8") as f2:
            lines2 = f2.readlines()

        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=os.path.basename(file_path_1),
            tofile=os.path.basename(file_path_2),
            lineterm="",
        ))

        if not diff:
            return "✅ Files are identical."

        return f"📝 Differences ({len(diff)} lines):\n" + "\n".join(diff[:100])
    except Exception as e:
        return f"❌ Error comparing files: {e}"
