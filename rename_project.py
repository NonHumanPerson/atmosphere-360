#!/usr/bin/env python3
"""
Comprehensive rename script: Atmosphere360 -> Atmosphere360
Handles all case variations and file renames.
"""
import os
import re
import shutil
from pathlib import Path

# Configuration
OLD_DIR = Path("C:/NAVEED/Projects/9to5 Buildathon/atmosphere360-2.0")
NEW_DIR = Path("C:/NAVEED/Projects/9to5 Buildathon/atmosphere360")

# Replacement patterns (ordered by specificity)
REPLACEMENTS = [
    # Exact brand names with versions
    ("Atmosphere360", "Atmosphere360"),
    ("Atmosphere360:", "Atmosphere360"),
    ("Atmosphere360: Mumbai", "Atmosphere360: Mumbai"),
    ("Atmosphere360: Mumbai —", "Atmosphere360: Mumbai —"),
    ("Atmosphere360: Predict. Explain. Act.", "Atmosphere360: Predict. Explain. Act."),
    ("Atmosphere360: Mumbai — Air Quality Prioritisation", "Atmosphere360: Mumbai — Air Quality Prioritisation"),
    ("Atmosphere360: Mumbai — Air Quality & Health Action Platform", "Atmosphere360: Mumbai — Air Quality & Health Action Platform"),
    
    # Brand name variations
    ("Atmosphere360", "Atmosphere360"),
    ("atmosphere360", "atmosphere360"),
    ("ATMOSPHERE360", "ATMOSPHERE360"),
    
    # Directory/repo names
    ("atmosphere360-2.0", "atmosphere360"),
    ("atmosphere3602026", "atmosphere360"),
    ("atmosphere3602026", "atmosphere360"),
    
    # GitHub/repo references
    ("RatneshPathak/atmosphere360-2.0", "RatneshPathak/atmosphere360"),
    ("RishiBuilds/Atmosphere360", "RishiBuilds/Atmosphere360"),
    ("atmosphere360-mumbai", "atmosphere360-mumbai"),
    ("atmosphere360aweb", "atmosphere360aweb"),
    
    # File names
    ("atmosphere360_cleaned_data", "atmosphere360_cleaned_data"),
    ("atmosphere360_station_summary", "atmosphere360_station_summary"),
    ("Atmosphere360_AQI_Cleaning_EDA", "Atmosphere360_AQI_Cleaning_EDA"),
    
    # Theme/template names
    ("atmosphere360_dark", "atmosphere360_dark"),
    ("atmosphere360-theme", "atmosphere360-theme"),
    
    # Passwords/keys
    ("atmosphere3602026", "atmosphere360"),
    
    # UI text
    ("Atmosphere360 Admin", "Atmosphere360 Admin"),
    ("Atmosphere360 command center", "Atmosphere360 command center"),
    ("Atmosphere360 design system", "Atmosphere360 design system"),
]

# Files to skip (binary, large, or generated)
SKIP_PATTERNS = [
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    'venv',
    '.venv',
    'env',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.so',
    '*.dll',
    '*.exe',
    '*.bin',
    '*.dat',
    '*.db',
    '*.sqlite',
    '*.sqlite3',
    '*.parquet',
    '*.csv',
    '*.ipynb',  # Notebooks handled separately
    '*.png',
    '*.jpg',
    '*.jpeg',
    '*.gif',
    '*.svg',
    '*.ico',
    '*.woff',
    '*.woff2',
    '*.ttf',
    '*.eot',
    '*.pdf',
    '*.pptx',
    '*.xlsx',
    '*.zip',
    '*.tar',
    '*.gz',
]

def should_skip(filepath: Path) -> bool:
    """Check if file should be skipped."""
    for pattern in SKIP_PATTERNS:
        if pattern.startswith('*'):
            if filepath.suffix == pattern[1:]:
                return True
        elif pattern in str(filepath):
            return True
    return False

def replace_in_file(filepath: Path) -> tuple:
    """Replace text in a single file. Returns (changed, error)."""
    if should_skip(filepath):
        return (False, "skipped")
    
    try:
        content = filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = filepath.read_text(encoding='latin-1')
        except Exception as e:
            return (False, f"read error: {e}")
    except Exception as e:
        return (False, f"read error: {e}")
    
    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    
    # Also handle regex patterns for remaining cases
    # Case-insensitive replacements for any remaining
    content = re.sub(r'(?i)atmosphere360', lambda m: 'Atmosphere360' if m.group().istitle() else 'atmosphere360', content)
    content = re.sub(r'(?i)atmosphere360', 'atmosphere360', content)
    
    if content != original:
        try:
            filepath.write_text(content, encoding='utf-8')
            return (True, None)
        except Exception as e:
            return (False, f"write error: {e}")
    
    return (False, None)

def rename_files_and_dirs(root: Path):
    """Rename files and directories containing atmosphere360."""
    renamed = []
    
    # Collect all paths first (bottom-up for dirs)
    all_paths = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for f in filenames:
            all_paths.append(Path(dirpath) / f)
        for d in dirnames:
            all_paths.append(Path(dirpath) / d)
    
    for path in all_paths:
        name = path.name
        new_name = name
        for old, new in REPLACEMENTS:
            new_name = new_name.replace(old, new)
        
        # Also case-insensitive
        new_name = re.sub(r'(?i)atmosphere360', 'atmosphere360', new_name)
        
        if new_name != name:
            new_path = path.parent / new_name
            try:
                path.rename(new_path)
                renamed.append((str(path), str(new_path)))
            except Exception as e:
                print(f"Error renaming {path}: {e}")
    
    return renamed

def main():
    print("=" * 60)
    print("Atmosphere360 -> Atmosphere360 Rename Script")
    print("=" * 60)
    
    # First, copy the directory
    if NEW_DIR.exists():
        print(f"Destination {NEW_DIR} already exists. Removing...")
        shutil.rmtree(NEW_DIR)
    
    print(f"Copying {OLD_DIR} -> {NEW_DIR}...")
    shutil.copytree(OLD_DIR, NEW_DIR, ignore=shutil.ignore_patterns(
        '.git', '__pycache__', '*.pyc', '__pycache__', '.pytest_cache', 
        '*.parquet', '*.csv', '*.ipynb', '*.png', '*.jpg', '*.svg'
    ))
    
    print("\nRenaming files and directories...")
    renamed = rename_files_and_dirs(NEW_DIR)
    for old, new in renamed:
        print(f"  {old} -> {new}")
    
    print("\nReplacing content in files...")
    changed_count = 0
    error_count = 0
    
    for filepath in NEW_DIR.rglob('*'):
        if filepath.is_file():
            changed, error = replace_in_file(filepath)
            if error:
                if error != "skipped":
                    print(f"  Error in {filepath}: {error}")
                    error_count += 1
            elif changed:
                changed_count += 1
    
    print(f"\nDone! Files changed: {changed_count}, Errors: {error_count}")
    print(f"New project at: {NEW_DIR}")
    
    # Show summary of key files changed
    print("\nKey files to verify:")
    key_files = [
        "app.py", "config.py", "README.md", "requirements.txt", 
        ".env.example", "serpapi_client.py", "theme.py", "components.py",
        "src/admin/admin_panel.py", "src/llm/gemini_client.py"
    ]
    for kf in key_files:
        fpath = NEW_DIR / kf
        if fpath.exists():
            print(f"  ✓ {kf}")
        else:
            print(f"  ✗ {kf} (missing!)")

if __name__ == "__main__":
    main()