# HLA元数据整理项目

## 项目简介

本项目用于从多个蛋白质组学数据库（ProteomeXchange、MassIVE、jPOST、PeptideAtlas）收集和整理147个HLA相关数据集的元数据。

## 环境安装

### 方法1：使用pip安装
```bash
pip install -r requirements.txt
```

### 方法2：使用conda安装（推荐）
```bash
conda create -n hla_metadata python=3.9
conda activate hla_metadata
pip install -r requirements.txt

# 可选：使用conda安装部分包
conda install -c conda-forge pandas openpyxl requests
conda install -c bioconda ppx pridepy
```

## 使用方法

### 1. 运行主收集脚本
```bash
python scripts/collect_metadata.py
```

这将：
- 从PRIDE API获取所有PXD数据集的元数据
- 下载并解析SDRF文件
- 处理MSV数据集（使用ppx）
- 生成中间结果文件

### 2. 生成Excel报告
```bash
python scripts/generate_excel.py
```

这将生成包含多个工作表的最终Excel报告。

### 3. 手动处理JPST和PASS数据
参考 `docs/manual_review_guide.txt` 中的说明。

## 输出文件

- `data/processed/proteomics_metadata_complete.xlsx` - 最终Excel报告
- `data/raw/pride_api_responses/` - 原始API响应
- `data/raw/sdrf_files/` - 下载的SDRF文件
- `data/validation/` - 质量检查报告

## 项目结构

```
HLA_metadata/
├── data/
│   ├── raw/                    # 原始数据
│   ├── processed/              # 处理后的数据
│   └── validation/             # 验证报告
├── scripts/                    # Python脚本
├── docs/                       # 文档
├── metadata_list               # 数据集ID列表
├── requirements.txt            # 依赖包
└── README.md                   # 本文件
```

## 预计运行时间

- 自动化收集（PXD+MSV）：3-5小时
- 手动处理（JPST+PASS）：1-2小时
- 人工审核：2-4小时
