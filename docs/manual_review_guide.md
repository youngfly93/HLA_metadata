# 手动审核指南

本文档提供手动提取和审核元数据的详细指南。

## 目录

1. [JPST数据集手动提取](#jpst数据集手动提取)
2. [PASS数据集手动提取](#pass数据集手动提取)
3. [HLA类型人工确认](#hla类型人工确认)
4. [疾病类型审核](#疾病类型审核)
5. [样本类型验证](#样本类型验证)

---

## JPST数据集手动提取

### 访问方式

jPOST (Japan ProteomeStandard Repository) 数据集需要通过Web界面手动访问。

### 步骤

1. **访问jPOSTrepo**
   - URL模板: `https://repository.jpostdb.org/entry/{JPST_ID}`
   - 例如: `https://repository.jpostdb.org/entry/JPST001066`

2. **提取信息**
   在页面上找到以下字段：

   | 字段 | 页面位置 | 备注 |
   |------|---------|------|
   | Title | 页面顶部 | 数据集标题 |
   | Description | Summary部分 | 详细描述 |
   | Organism | Sample Information | 物种信息 |
   | Disease | Sample Information | 疾病类型 |
   | Tissue/Cell Type | Sample Information | 组织或细胞类型 |
   | Instrument | Instrument Information | 质谱仪器 |
   | Publication | Reference部分 | PubMed ID或DOI |

3. **HLA相关判断**
   - 检查Title和Description中是否包含HLA、MHC、immunopeptid等关键词
   - 查看Publication的摘要确认HLA类型（I类或II类）

4. **记录数据**
   将提取的信息填入 `data/raw/manual_extracts/jpst_manual.csv`

   CSV格式：
   ```csv
   dataset_id,title,description,organism,disease,tissue,cell_type,instrument,hla_type,sample_type,pubmed_id
   ```

---

## PASS数据集手动提取

### 访问方式

PeptideAtlas PASS (PeptideAtlas SRM/MRM Experiment Library) 数据集访问。

### 步骤

1. **访问PeptideAtlas**
   - URL模板: `http://www.peptideatlas.org/PASS/{PASS_ID}`
   - 例如: `http://www.peptideatlas.org/PASS/PASS00211`

2. **提取信息**

   | 字段 | 页面位置 | 备注 |
   |------|---------|------|
   | Dataset Title | 页面顶部 | 数据集名称 |
   | Description | Dataset Summary | 详细说明 |
   | Organism | Sample Details | 通常在样本描述中 |
   | Sample Type | Sample Details | 血液/组织/细胞系 |
   | Instrument | Methods | 质谱平台 |
   | Publication | Publications | 相关文献 |

3. **交叉引用ProteomeXchange**
   - 许多PASS数据集在ProteomeXchange中有对应条目
   - 如果有PXD编号，可以从PRIDE获取更详细的元数据

4. **记录数据**
   填入 `data/raw/manual_extracts/pass_manual.csv`

---

## HLA类型人工确认

### 需要确认的情况

自动分类器标记为 "HLA (需人工确认)" 的数据集需要人工验证。

### 确认步骤

1. **查看原始文献**
   - 使用Excel报告中的PubMed ID
   - 访问: `https://pubmed.ncbi.nlm.nih.gov/{PMID}`
   - 阅读摘要和方法部分

2. **关键判断依据**

   **HLA I类指标：**
   - 提及 HLA-A, HLA-B, HLA-C
   - 描述 8-11氨基酸肽段
   - 使用抗体：W6/32（泛HLA I类抗体）
   - 关键词：CD8+ T cell epitopes

   **HLA II类指标：**
   - 提及 HLA-DR, HLA-DQ, HLA-DP
   - 描述 13-25氨基酸肽段
   - 使用抗体：L243, TÜ39（HLA-DR抗体）
   - 关键词：CD4+ T cell epitopes

   **同时包含I和II类：**
   - 明确说明同时研究两类
   - 使用多种抗体
   - 比较不同类别的表位

3. **更新Excel文件**
   - 在 "主元数据表" 中找到对应行
   - 将 "HLA类型" 列更新为正确分类
   - 将 "需人工审核" 列改为FALSE
   - 在 "备注" 列添加确认依据

---

## 疾病类型审核

### 审核重点

确保疾病类型正确分类并使用标准术语。

### 标准化指南

1. **癌症类型标准化**
   ```
   原始术语 → 标准术语
   lung cancer → Lung carcinoma
   breast cancer → Breast carcinoma
   melanoma → Melanoma
   CML → Chronic myeloid leukemia
   ```

2. **使用本体论术语**
   - 优先使用 MONDO (Monarch Disease Ontology)
   - 备选使用 Disease Ontology (DO)
   - 记录本体论ID（如果可获得）

3. **特殊情况处理**
   - **健康对照**: 标记为 "Healthy" 或 "Normal"
   - **多种疾病**: 用分号分隔，例如 "Type 2 diabetes; Obesity"
   - **疾病模型**: 注明是动物模型还是细胞模型

### 审核步骤

1. 检查 "疾病类型汇总" sheet
2. 识别不标准或模糊的术语
3. 查阅原始论文或PRIDE页面确认
4. 更新主表中的疾病类型字段

---

## 样本类型验证

### 分类标准

**组织 (Tissue)**
- 来自器官或组织的样本
- 包括肿瘤组织、正常组织
- 示例：liver tissue, tumor biopsy

**血液 (Blood)**
- 全血、血浆、血清、PBMC
- 示例：plasma, serum, PBMC, whole blood

**细胞系 (Cell Line)**
- 体外培养的永生化细胞
- 示例：HeLa, Jurkat, K562

**原代细胞 (Primary Cells)**
- 直接分离的细胞，未永生化
- 示例：primary hepatocytes, isolated monocytes

### 验证检查清单

- [ ] 样本类型与组织字段一致
- [ ] 细胞系名称标准化（大小写正确）
- [ ] 血液样本具体类型明确（血浆/血清/全血）
- [ ] 组织来源明确（哪个器官）
- [ ] 肿瘤样本注明癌症类型

### 常见问题修正

| 问题 | 修正方法 |
|------|---------|
| "Unknown" | 查看description和SDRF文件 |
| 组织字段为空但有详细描述 | 从描述中提取组织信息 |
| 细胞系命名不一致 | 统一为标准名称（如HEK-293 → HEK293）|
| 混合样本 | 使用主要样本类型，在备注中说明 |

---

## 质量检查清单

完成手动审核后，检查以下项目：

### 数据完整性
- [ ] 所有JPST数据集已手动提取
- [ ] 所有PASS数据集已手动提取
- [ ] 标记为"需人工确认"的HLA类型已审核
- [ ] Unknown疾病类型少于5%
- [ ] Unknown样本类型少于5%

### 数据一致性
- [ ] 疾病术语已标准化
- [ ] 样本类型分类一致
- [ ] HLA类型与项目描述匹配
- [ ] 没有明显的分类错误

### 文档记录
- [ ] 手动提取的数据已保存到CSV
- [ ] 审核变更已记录在Excel备注中
- [ ] 不确定的案例已在validation目录中记录

---

## 输出文件

手动审核完成后，应该生成以下文件：

```
data/
├── raw/
│   └── manual_extracts/
│       ├── jpst_manual.csv          # JPST手动提取数据
│       ├── pass_manual.csv          # PASS手动提取数据
│       └── hla_corrections.csv      # HLA类型人工修正记录
└── validation/
    ├── review_notes.txt             # 审核笔记
    └── uncertain_cases.csv          # 不确定的案例
```

---

## 需要帮助？

如果遇到以下情况：

1. **无法访问数据集页面**
   - 检查网络连接
   - 尝试使用VPN
   - 联系数据库管理员

2. **信息不完整**
   - 查找关联的论文
   - 搜索数据集在其他数据库的镜像
   - 联系数据集提交者

3. **分类不确定**
   - 在Excel中标记为"待定"
   - 记录在uncertain_cases.csv中
   - 咨询领域专家

---

## 审核时间估算

| 任务 | 每个数据集耗时 | 总时间（基于数量）|
|------|--------------|-----------------|
| JPST手动提取 | 5-10分钟 | ~1小时（7个）|
| PASS手动提取 | 5-10分钟 | ~15分钟（1个）|
| HLA类型确认 | 10-15分钟 | 视标记数量而定 |
| 疾病类型审核 | 2-5分钟 | ~1-2小时 |
| 样本类型验证 | 2-3分钟 | ~30-60分钟 |

**预计总时间：3-6小时**（取决于需要审核的数量）
