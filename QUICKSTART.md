# 快速入门指南

本指南帮助您快速开始HLA元数据收集项目。

## 项目概述

自动从多个蛋白质组学数据库收集147个数据集的元数据，包括：
- **疾病类型**：癌症、神经退行性疾病、感染性疾病等
- **HLA类型**：HLA I类、II类或混合
- **样本类型**：组织、血液、细胞系

## 5分钟快速开始

### 1. 安装依赖（首次运行）

```bash
# 推荐：使用conda创建独立环境
conda create -n hla_metadata python=3.9
conda activate hla_metadata

# 安装必要的包
pip install -r requirements.txt

# 可选：安装增强功能包
pip install pridepy ppx
```

### 2. 验证设置

```bash
# 运行测试脚本确认一切正常
python scripts/test_setup.py
```

如果看到 "✓ Project structure is complete!" 表示设置成功。

### 3. 运行完整流程

**方式A：一步执行（推荐用于首次运行）**

```bash
# 运行主收集脚本
python scripts/collect_metadata.py

# 解析SDRF文件
python scripts/parse_sdrf.py

# 分类元数据
python scripts/classify_metadata.py

# 生成Excel报告
python scripts/generate_excel.py
```

**方式B：后台运行（适合长时间运行）**

```bash
# 使用nohup在后台运行
nohup python scripts/collect_metadata.py > collection.log 2>&1 &

# 查看进度
tail -f collection.log
```

### 4. 查看结果

最终Excel文件位于：
```
data/processed/proteomics_metadata_complete.xlsx
```

打开此文件，您将看到6个工作表：
- **主元数据表**：所有数据集的完整信息
- **疾病类型汇总**：按疾病分类的统计
- **HLA分类汇总**：HLA I/II类型分布
- **样本类型汇总**：组织/血液/细胞系统计
- **技术信息汇总**：仪器、PTM统计
- **数据质量报告**：需要人工审核的列表

## 预计时间

| 步骤 | 自动运行时间 | 说明 |
|------|------------|------|
| collect_metadata.py | 3-5小时 | 从API获取数据并下载SDRF |
| parse_sdrf.py | 10-30分钟 | 解析SDRF文件 |
| classify_metadata.py | 1-2分钟 | 分类HLA和样本类型 |
| generate_excel.py | 1-2分钟 | 生成Excel报告 |
| **自动化总计** | **4-6小时** | 可在后台运行 |
| 手动审核 | 3-6小时 | 需要您的参与 |

## 数据集分布

根据`metadata_list`文件：
- **PXD** (ProteomeXchange): 129个数据集 ✓ 全自动
- **MSV** (MassIVE): 10个数据集 ✓ 自动（需要ppx包）
- **JPST** (jPOST): 7个数据集 ⚠ 需要手动提取
- **PASS** (PeptideAtlas): 1个数据集 ⚠ 需要手动提取

## 手动处理步骤

对于JPST和PASS数据集，请参考：
```
docs/manual_review_guide.md
```

主要步骤：
1. 访问数据集URL（脚本会生成URL列表）
2. 从网页提取元数据
3. 填入`data/raw/manual_extracts/`目录的CSV文件
4. 重新运行分类和Excel生成脚本

## 常见问题

### Q: 脚本运行很慢怎么办？
**A:** 这是正常的。脚本需要：
- 访问129+个数据集的API
- 下载大量SDRF文件
- 包含速率限制（1-2秒延迟）以遵守API使用规则

建议在后台运行或过夜执行。

### Q: 出现网络错误怎么办？
**A:** 脚本包含自动重试机制（3次）。如果持续失败：
1. 检查网络连接
2. 查看`data/raw/pride_api_responses/`已保存的文件
3. 重新运行脚本（会跳过已下载的文件）

### Q: 某些包安装失败？
**A:** 核心包（requests, pandas, openpyxl）是必须的：
```bash
pip install requests pandas openpyxl
```

可选包（pridepy, ppx）提供增强功能但不是必需的。

### Q: 如何只更新部分数据集？
**A:** 编辑`metadata_list`文件，只保留需要更新的数据集ID。

### Q: Excel文件中有很多"需人工审核"的条目？
**A:** 这是正常的。自动分类器保守标记不确定的案例。按照以下优先级审核：
1. HLA类型不明确的数据集
2. 疾病类型为"Unknown"的数据集
3. 样本类型为"Unknown"的数据集

参考`docs/manual_review_guide.md`获取详细说明。

## 输出文件说明

```
data/
├── raw/
│   ├── pride_api_responses/      # 每个PXD数据集的JSON响应
│   ├── sdrf_files/                # 下载的SDRF文件
│   └── manual_extracts/           # 手动提取的数据
├── processed/
│   ├── pxd_metadata.csv          # PXD数据集元数据
│   ├── msv_metadata.csv          # MSV数据集元数据
│   ├── all_metadata_raw.csv      # 合并的原始元数据
│   ├── sdrf_parsed.csv           # SDRF解析结果
│   ├── all_metadata_enriched.csv # 增强后的元数据
│   ├── all_metadata_classified.csv # 分类后的元数据
│   └── proteomics_metadata_complete.xlsx # 最终Excel报告
└── validation/
    └── quality_report.txt         # 质量报告文本
```

## 下一步

1. ✓ 运行自动化脚本（4-6小时）
2. ⚠ 手动提取JPST/PASS数据（1-2小时）
3. 👁 人工审核标记的数据集（2-4小时）
4. ✓ 生成最终报告
5. 📊 分析和使用数据

## 需要帮助？

- 查看详细文档：`README.md`
- 手动审核指南：`docs/manual_review_guide.md`
- 代码指引：`CLAUDE.md`
- 测试设置：`python scripts/test_setup.py`

祝您使用顺利！
