#!/usr/bin/env python3
"""
智能填充SysteMHC数据
基于标题、描述和HLA免疫肽组学领域知识进行推断
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"


class IntelligentSystemHCFiller:
    """智能填充器 - 基于标题和领域知识"""

    def __init__(self):
        # HLA等位基因模式库
        self.hla_patterns = {
            'B*57:01': ['B*57:01', 'B57:01', 'B5701'],
            'B*57:03': ['B*57:03', 'B57:03', 'B5703'],
            'B*58:01': ['B*58:01', 'B58:01', 'B5801'],
            'B*27': ['B*27', 'HLA-B27', 'B27'],
            'B*51': ['B*51', 'B51', 'Behçet'],
            'DRB1*15:01': ['DRB1*15:01', 'DRB1*1501', 'DR15'],
            'DRB5*01:01': ['DRB5*01:01', 'DRB5*0101'],
            'A*02:01': ['A*02:01', 'A*0201', 'A02'],
            'A*24:02': ['A*24:02', 'A*2402', 'A24'],
        }

        # 疾病推断规则
        self.disease_rules = {
            'Behçet': ['Behçet', 'Behcet'],
            'Ankylosing spondylitis': ['ankylosing spondylitis', 'AS'],
            'Melanoma': ['melanoma'],
            'Lymphoma': ['lymphoma', 'B-cell lymph', 'B cell lymph'],
            'Influenza': ['influenza', 'flu'],
            'Tuberculosis': ['BCG', 'Bacillus Calmette', 'tuberculosis'],
            'Theileria': ['Theileria parva'],
            'Marek disease': ['Marek'],
            'Infectious bursal disease': ['IBDV', 'infectious bursal'],
            'Cancer': ['tumor', 'cancer', 'carcinoma', 'malignancy'],
            'Multiple sclerosis': ['multiple sclerosis', 'MS'],
            'Diabetes': ['diabetes', 'NOD mouse', 'insulin'],
        }

        # 组织类型推断
        self.tissue_rules = {
            'BAL': ['BAL', 'bronchoalveolar'],
            'Blood': ['blood', 'plasma', 'serum', 'PBMC'],
            'Spleen': ['spleen'],
            'Liver': ['liver', 'hepat'],
            'Tumor': ['tumor', 'cancer'],
            'Benign tissue': ['benign tissue'],
            'Pancreas': ['insulin granule', 'pancrea'],
        }

        # 细胞系识别
        self.cell_line_rules = {
            'C1R': ['C1R'],
            'EBV-transformed B cells': ['EBV', 'B-lymphoblast'],
            'THP-1': ['THP-1', 'Thp-1'],
            'Jurkat': ['Jurkat'],
            'LCL': ['lymphoblastoid', 'LCL'],
        }

    def extract_hla_from_title(self, title: str, dataset_id: str) -> Tuple[List[str], str]:
        """从标题提取HLA信息"""
        if not title or pd.isna(title):
            return [], None

        alleles = []
        hla_type = None

        # 从标题提取HLA等位基因
        # Class I alleles
        class_i_patterns = [
            r'HLA-[ABC]\*\d+:\d+',
            r'[ABC]\*\d+:\d+',
            r'HLA-[ABC]\d+',
        ]

        # Class II alleles
        class_ii_patterns = [
            r'HLA-DR[AB]\d+\*\d+:\d+',
            r'HLA-DQ[AB]\d*\*\d+:\d+',
            r'HLA-DP[AB]\d*\*\d+:\d+',
            r'DRB\d+\*\d+:\d+',
            r'DQA?\d*\*\d+:\d+',
        ]

        title_upper = title.upper()

        # Extract Class I
        has_class_i = False
        for pattern in class_i_patterns:
            matches = re.findall(pattern, title_upper)
            for match in matches:
                normalized = self._normalize_allele(match)
                if normalized and normalized not in alleles:
                    alleles.append(normalized)
                    has_class_i = True

        # Extract Class II
        has_class_ii = False
        for pattern in class_ii_patterns:
            matches = re.findall(pattern, title_upper)
            for match in matches:
                normalized = self._normalize_allele(match)
                if normalized and normalized not in alleles:
                    alleles.append(normalized)
                    has_class_ii = True

        # Check for general mentions
        if 'MHC CLASS I' in title_upper or 'MHC I' in title_upper or 'HLA-I' in title_upper:
            has_class_i = True
        if 'MHC CLASS II' in title_upper or 'MHC II' in title_upper or 'HLA-II' in title_upper:
            has_class_ii = True

        # Determine HLA type
        if has_class_i and has_class_ii:
            hla_type = 'HLA I/II'
        elif has_class_i:
            hla_type = 'HLA I'
        elif has_class_ii:
            hla_type = 'HLA II'

        # Special dataset-specific knowledge
        if 'C1R.B*57:01' in title:
            alleles.append('HLA-B*57:01')
            hla_type = 'HLA I'
        elif 'C1R.B*57:03' in title:
            alleles.append('HLA-B*57:03')
            hla_type = 'HLA I'
        elif 'C1R.B*58:01' in title:
            alleles.append('HLA-B*58:01')
            hla_type = 'HLA I'

        return alleles, hla_type

    def _normalize_allele(self, allele: str) -> str:
        """规范化HLA等位基因命名"""
        allele = allele.strip().upper()

        # Add HLA- prefix if missing
        if not allele.startswith('HLA-'):
            allele = 'HLA-' + allele

        # Ensure proper format: HLA-X*##:##
        if '*' not in allele:
            # Try to add * for formats like HLA-A0201
            match = re.match(r'HLA-([A-Z]+)(\d+)', allele)
            if match:
                gene = match.group(1)
                digits = match.group(2)
                if len(digits) == 4:
                    allele = f"HLA-{gene}*{digits[:2]}:{digits[2:]}"

        return allele

    def infer_disease(self, title: str, description: str = '') -> str:
        """推断疾病类型"""
        text = f"{title} {description}".lower()

        diseases = []
        for disease, keywords in self.disease_rules.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if disease not in diseases:
                        diseases.append(disease)
                    break

        # Special cases
        if 'healthy' in text or 'benign' in text or 'normal' in text:
            return 'Healthy'

        if not diseases:
            # Check for general HLA study
            if 'immunopeptidome' in text or 'peptidomics' in text:
                if 'method' in text or 'prediction' in text or 'motif' in text:
                    return 'Method development'
                return 'Unknown'

        return '; '.join(diseases) if diseases else 'Unknown'

    def infer_tissue(self, title: str, description: str = '') -> str:
        """推断组织类型"""
        text = f"{title} {description}".lower()

        tissues = []
        for tissue, keywords in self.tissue_rules.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if tissue not in tissues:
                        tissues.append(tissue)
                    break

        return ', '.join(tissues) if tissues else ''

    def infer_cell_type(self, title: str, description: str = '') -> str:
        """推断细胞类型"""
        text = f"{title} {description}".lower()

        cell_types = []
        for cell_type, keywords in self.cell_line_rules.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if cell_type not in cell_types:
                        cell_types.append(cell_type)
                    break

        return ', '.join(cell_types) if cell_types else ''

    def fill_dataset(self, row: pd.Series, main_data: pd.DataFrame) -> Dict:
        """填充单个数据集的信息"""
        dataset_id = row['dataset_id']
        title = row['title']

        # 获取主数据中的信息（可能从PRIDE API获取）
        main_row = main_data[main_data['dataset_id'] == dataset_id]
        description = ''
        if len(main_row) > 0:
            description = main_row.iloc[0].get('description', '')
            if pd.isna(description):
                description = ''

        # 提取HLA信息
        alleles, hla_type = self.extract_hla_from_title(title, dataset_id)

        # 推断疾病、组织、细胞类型
        disease = self.infer_disease(title, description)
        tissue = self.infer_tissue(title, description)
        cell_type = self.infer_cell_type(title, description)

        result = {
            'hla_alleles_found': '; '.join(alleles) if alleles else '',
            'tissues_found': tissue,
            'cell_types_found': cell_type,
            'diseases_found': disease,
            'notes': 'Auto-filled based on title and knowledge base'
        }

        return result


def main():
    """主函数"""
    print("\n" + "="*70)
    print("Intelligent SystemHC Data Filler")
    print("="*70 + "\n")

    # 读取模板
    template_file = DATA_VALIDATION_DIR / "systemhc_manual_template.csv"
    template_df = pd.read_csv(template_file)
    print(f"✓ Loaded template: {len(template_df)} datasets\n")

    # 读取主数据（用于获取description等额外信息）
    main_file = DATA_PROCESSED_DIR / "all_metadata_crosschecked.csv"
    main_df = pd.read_csv(main_file)
    print(f"✓ Loaded main data: {len(main_df)} datasets\n")

    # 初始化填充器
    filler = IntelligentSystemHCFiller()

    # 填充每个数据集
    filled_count = 0
    for idx, row in template_df.iterrows():
        dataset_id = row['dataset_id']
        print(f"[{idx+1}/{len(template_df)}] Processing {dataset_id}...")

        # 智能填充
        filled_data = filler.fill_dataset(row, main_df)

        # 更新模板
        for key, value in filled_data.items():
            template_df.at[idx, key] = value

        # 显示填充结果
        if filled_data['hla_alleles_found'] or filled_data['diseases_found'] != 'Unknown':
            filled_count += 1
            print(f"  ✓ HLA: {filled_data['hla_alleles_found'] or 'N/A'}")
            print(f"  ✓ Disease: {filled_data['diseases_found']}")
            if filled_data['tissues_found']:
                print(f"  ✓ Tissue: {filled_data['tissues_found']}")
            if filled_data['cell_types_found']:
                print(f"  ✓ Cell: {filled_data['cell_types_found']}")
        else:
            print(f"  ⚠ Limited information extracted")
        print()

    # 保存填充后的模板
    output_file = DATA_VALIDATION_DIR / "systemhc_manual_template_filled.csv"
    template_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ Saved filled template to: {output_file}\n")

    # 统计
    print("="*70)
    print("Filling Summary")
    print("="*70)
    print(f"Total datasets: {len(template_df)}")
    print(f"Successfully filled: {filled_count}")
    print(f"Success rate: {filled_count/len(template_df)*100:.1f}%")

    # 统计各字段填充情况
    has_hla = len(template_df[template_df['hla_alleles_found'] != ''])
    has_disease = len(template_df[template_df['diseases_found'] != 'Unknown'])
    has_tissue = len(template_df[template_df['tissues_found'] != ''])
    has_cell = len(template_df[template_df['cell_types_found'] != ''])

    print(f"\nField statistics:")
    print(f"  HLA alleles filled: {has_hla}")
    print(f"  Disease filled: {has_disease}")
    print(f"  Tissue filled: {has_tissue}")
    print(f"  Cell type filled: {has_cell}")

    print("\nNext step: Review and run merge_manual_systemhc.py")
    print()


if __name__ == "__main__":
    main()
