#!/usr/bin/env python3
"""
测试脚本设置和基本功能
"""

import sys
from pathlib import Path

print("="*60)
print("Testing HLA Metadata Collection Setup")
print("="*60 + "\n")

# 检查Python版本
print(f"Python version: {sys.version}")
print()

# 检查项目结构
PROJECT_ROOT = Path(__file__).parent.parent
print(f"Project root: {PROJECT_ROOT}")
print()

# 检查必要文件
required_files = [
    "metadata_list",
    "requirements.txt",
    "README.md",
    "CLAUDE.md",
]

print("Checking required files:")
for filename in required_files:
    file_path = PROJECT_ROOT / filename
    exists = "✓" if file_path.exists() else "✗"
    print(f"  {exists} {filename}")
print()

# 检查脚本文件
scripts = [
    "collect_metadata.py",
    "parse_sdrf.py",
    "classify_metadata.py",
    "generate_excel.py",
]

print("Checking scripts:")
for script in scripts:
    script_path = PROJECT_ROOT / "scripts" / script
    exists = "✓" if script_path.exists() else "✗"
    print(f"  {exists} {script}")
print()

# 检查目录结构
required_dirs = [
    "data/raw/pride_api_responses",
    "data/raw/sdrf_files",
    "data/raw/manual_extracts",
    "data/processed",
    "data/validation",
    "scripts",
    "docs",
]

print("Checking directory structure:")
for dir_path in required_dirs:
    full_path = PROJECT_ROOT / dir_path
    exists = "✓" if full_path.exists() else "✗"
    print(f"  {exists} {dir_path}/")
print()

# 读取数据集列表
metadata_list_file = PROJECT_ROOT / "metadata_list"
if metadata_list_file.exists():
    with open(metadata_list_file, 'r') as f:
        dataset_ids = [line.strip() for line in f if line.strip() and len(line.strip()) > 3]

    print(f"Dataset list statistics:")
    print(f"  Total datasets: {len(dataset_ids)}")

    pxd_count = sum(1 for d in dataset_ids if d.startswith('PXD'))
    msv_count = sum(1 for d in dataset_ids if d.startswith('MSV'))
    jpst_count = sum(1 for d in dataset_ids if d.startswith('JPST'))
    pass_count = sum(1 for d in dataset_ids if d.startswith('PASS'))

    print(f"  PXD: {pxd_count}")
    print(f"  MSV: {msv_count}")
    print(f"  JPST: {jpst_count}")
    print(f"  PASS: {pass_count}")
    print()

# 检查Python包
print("Checking Python packages:")
packages = {
    'requests': False,
    'pandas': False,
    'openpyxl': False,
    'pridepy': False,
    'ppx': False,
}

for package in packages.keys():
    try:
        __import__(package)
        packages[package] = True
        print(f"  ✓ {package}")
    except ImportError:
        print(f"  ✗ {package} (not installed)")

print()
print("="*60)

# 总结
all_files_exist = all((PROJECT_ROOT / f).exists() for f in required_files)
all_scripts_exist = all((PROJECT_ROOT / "scripts" / s).exists() for s in scripts)
all_dirs_exist = all((PROJECT_ROOT / d).exists() for d in required_dirs)
core_packages = packages['requests'] and packages['pandas']

if all_files_exist and all_scripts_exist and all_dirs_exist:
    print("✓ Project structure is complete!")
else:
    print("✗ Some files or directories are missing")

if core_packages:
    print("✓ Core packages are installed")
    print("\nYou can now run:")
    print("  python scripts/collect_metadata.py")
else:
    print("✗ Core packages need to be installed")
    print("\nPlease run:")
    print("  pip install -r requirements.txt")

print("="*60)
