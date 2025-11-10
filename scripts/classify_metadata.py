#!/usr/bin/env python3
"""
元数据分类脚本
自动分类HLA类型、样本类型、疾病类型等
"""

import sys
import pandas as pd
import re
from pathlib import Path
from typing import Tuple, Optional

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


class MetadataClassifier:
    """元数据分类器"""

    def __init__(self):
        # HLA关键词
        self.hla_i_keywords = [
            'HLA I', 'HLA-I', 'HLA class I', 'HLA-class I',
            'MHC I', 'MHC-I', 'MHC class I', 'MHC-class I',
            'HLA-A', 'HLA-B', 'HLA-C',
            'class I MHC', 'class I HLA'
        ]

        self.hla_ii_keywords = [
            'HLA II', 'HLA-II', 'HLA class II', 'HLA-class II',
            'MHC II', 'MHC-II', 'MHC class II', 'MHC-class II',
            'HLA-DR', 'HLA-DQ', 'HLA-DP',
            'class II MHC', 'class II HLA'
        ]

        self.hla_general_keywords = [
            'HLA', 'MHC', 'immunopeptid', 'immuno-peptid',
            'antigen presentation', 'antigen presenting',
            'peptide presentation', 'immunoaffinity',
            'immunoprecipitation'
        ]

        # 样本类型关键词
        self.blood_keywords = [
            'blood', 'serum', 'plasma', 'PBMC', 'peripheral blood',
            'leukocyte', 'lymphocyte', 'monocyte'
        ]

        self.tissue_keywords = [
            'tissue', 'biopsy', 'tumor', 'tumour', 'cancer',
            'carcinoma', 'adenocarcinoma', 'melanoma',
            'liver', 'kidney', 'lung', 'brain', 'heart',
            'breast', 'ovary', 'prostate', 'colon',
            'muscle', 'skin', 'bone', 'spleen'
        ]

        self.cell_line_keywords = [
            'cell line', 'cell-line', 'cellline',
            'HeLa', 'HEK293', 'Jurkat', 'K562',
            'cultured cell', 'culture', 'in vitro'
        ]

        # 疾病类型关键词
        self.cancer_keywords = [
            'cancer', 'tumor', 'tumour', 'carcinoma',
            'melanoma', 'leukemia', 'lymphoma', 'sarcoma',
            'adenocarcinoma', 'glioblastoma', 'neuroblastoma',
            'malignant', 'neoplasm', 'oncology'
        ]

        self.neurodegenerative_keywords = [
            'Alzheimer', 'Parkinson', 'dementia',
            'neurodegenerative', 'ALS', 'multiple sclerosis',
            'Huntington'
        ]

        self.infectious_keywords = [
            'COVID', 'SARS', 'influenza', 'HIV', 'virus',
            'bacterial', 'infection', 'pathogen',
            'tuberculosis', 'hepatitis'
        ]

        self.healthy_keywords = [
            'healthy', 'normal', 'control', 'disease-free',
            'non-disease', 'wild type', 'wild-type'
        ]

    def classify_hla_type(self, row: pd.Series) -> Tuple[str, bool]:
        """
        分类HLA类型

        Args:
            row: DataFrame的一行

        Returns:
            (HLA类型, 是否需要人工确认)
        """
        # 合并所有文本字段
        text_fields = [
            str(row.get('title', '')),
            str(row.get('description', '')),
            str(row.get('keywords', '')),
            str(row.get('project_tags', '')),
            str(row.get('sample_protocol', '')),
        ]
        combined_text = ' '.join(text_fields).upper()

        # 检查是否是HLA相关研究
        is_hla_related = any(
            keyword.upper() in combined_text
            for keyword in self.hla_general_keywords
        )

        if not is_hla_related:
            return 'Non-HLA', False

        # 检查HLA I类
        has_hla_i = any(
            keyword.upper() in combined_text
            for keyword in self.hla_i_keywords
        )

        # 检查HLA II类
        has_hla_ii = any(
            keyword.upper() in combined_text
            for keyword in self.hla_ii_keywords
        )

        # 分类逻辑
        if has_hla_i and has_hla_ii:
            return 'HLA I/II', False
        elif has_hla_i:
            return 'HLA I', False
        elif has_hla_ii:
            return 'HLA II', False
        else:
            # HLA相关但无法确定类型
            return 'HLA (需人工确认)', True

    def classify_sample_type(self, row: pd.Series) -> str:
        """
        分类样本类型

        Args:
            row: DataFrame的一行

        Returns:
            样本类型
        """
        # 合并相关字段
        text_fields = [
            str(row.get('tissues', '')),
            str(row.get('cell_types', '')),
            str(row.get('sdrf_organism part', '')),
            str(row.get('sdrf_cell type', '')),
            str(row.get('sdrf_cell line', '')),
            str(row.get('title', '')),
            str(row.get('description', '')),
        ]
        combined_text = ' '.join(text_fields).lower()

        # 优先检查细胞系（最具体）
        if any(keyword.lower() in combined_text for keyword in self.cell_line_keywords):
            # 尝试提取具体的细胞系名称
            cell_line_match = re.search(
                r'(HeLa|HEK293|Jurkat|K562|MCF-?7|A549|U2OS)',
                combined_text,
                re.IGNORECASE
            )
            if cell_line_match:
                return f'Cell line ({cell_line_match.group(1)})'
            return 'Cell line'

        # 检查血液
        if any(keyword in combined_text for keyword in self.blood_keywords):
            # 尝试提取具体类型
            if 'pbmc' in combined_text:
                return 'Blood (PBMC)'
            elif 'plasma' in combined_text:
                return 'Blood (Plasma)'
            elif 'serum' in combined_text:
                return 'Blood (Serum)'
            return 'Blood'

        # 检查组织
        if any(keyword in combined_text for keyword in self.tissue_keywords):
            # 尝试提取具体组织类型
            tissue_match = re.search(
                r'(liver|kidney|lung|brain|heart|breast|ovary|prostate|colon|'
                r'tumor|tumour|cancer|melanoma)',
                combined_text,
                re.IGNORECASE
            )
            if tissue_match:
                tissue_name = tissue_match.group(1).capitalize()
                return f'Tissue ({tissue_name})'
            return 'Tissue'

        # 如果有组织字段但上面没匹配到
        tissues = str(row.get('tissues', ''))
        if tissues and tissues != 'nan' and tissues.strip():
            return f'Tissue ({tissues[:50]})'  # 限制长度

        return 'Unknown'

    def classify_disease_type(self, row: pd.Series) -> Tuple[str, str, bool]:
        """
        分类疾病类型

        Args:
            row: DataFrame的一行

        Returns:
            (疾病类型, 疾病类别, 是否健康对照)
        """
        # 合并疾病相关字段
        text_fields = [
            str(row.get('diseases', '')),
            str(row.get('sdrf_disease', '')),
            str(row.get('title', '')),
            str(row.get('description', '')),
        ]
        combined_text = ' '.join(text_fields).lower()

        # 检查是否是健康对照
        is_healthy = any(
            keyword in combined_text
            for keyword in self.healthy_keywords
        )

        if is_healthy or 'not available' in combined_text or 'not applicable' in combined_text:
            return 'Healthy/Control', 'Healthy', True

        # 提取疾病类型（优先使用diseases字段）
        disease_type = str(row.get('diseases', ''))
        if not disease_type or disease_type == 'nan':
            disease_type = str(row.get('sdrf_disease', ''))

        if not disease_type or disease_type == 'nan':
            disease_type = 'Unknown'

        # 分类疾病类别
        disease_category = 'Other'

        if any(keyword in combined_text for keyword in self.cancer_keywords):
            disease_category = 'Cancer'
        elif any(keyword in combined_text for keyword in self.neurodegenerative_keywords):
            disease_category = 'Neurodegenerative'
        elif any(keyword in combined_text for keyword in self.infectious_keywords):
            disease_category = 'Infectious Disease'

        return disease_type, disease_category, False

    def classify_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对所有数据集进行分类

        Args:
            df: 输入DataFrame

        Returns:
            添加了分类列的DataFrame
        """
        print(f"\n{'='*60}")
        print(f"Classifying {len(df)} datasets")
        print(f"{'='*60}\n")

        # HLA类型分类
        print("Classifying HLA types...")
        hla_results = df.apply(self.classify_hla_type, axis=1)
        df['hla_type'] = hla_results.apply(lambda x: x[0])
        df['hla_needs_review'] = hla_results.apply(lambda x: x[1])

        # 样本类型分类
        print("Classifying sample types...")
        df['sample_type'] = df.apply(self.classify_sample_type, axis=1)

        # 疾病类型分类
        print("Classifying disease types...")
        disease_results = df.apply(self.classify_disease_type, axis=1)
        df['disease_type'] = disease_results.apply(lambda x: x[0])
        df['disease_category'] = disease_results.apply(lambda x: x[1])
        df['is_healthy'] = disease_results.apply(lambda x: x[2])

        # 数据质量评分
        print("Calculating data quality scores...")
        df['metadata_quality'] = df.apply(self._calculate_quality_score, axis=1)

        # 标记需要人工审核的数据集
        df['needs_manual_review'] = (
            df['hla_needs_review'] |
            (df['hla_type'] == 'HLA (需人工确认)') |
            (df['sample_type'] == 'Unknown') |
            (df['disease_type'] == 'Unknown') |
            df.get('manual_review', False).fillna(False)
        )

        print("\n✓ Classification complete!")

        # 输出统计信息
        self._print_statistics(df)

        return df

    def _calculate_quality_score(self, row: pd.Series) -> str:
        """
        计算元数据质量评分

        Args:
            row: DataFrame的一行

        Returns:
            质量评分 (High/Medium/Low)
        """
        score = 0

        # 检查关键字段是否存在且非空
        key_fields = [
            'title', 'description', 'diseases', 'tissues',
            'organisms', 'instruments', 'publication_date'
        ]

        for field in key_fields:
            value = str(row.get(field, ''))
            if value and value != 'nan' and value.strip():
                score += 1

        # 额外加分项
        if row.get('has_sdrf', False):
            score += 2

        if str(row.get('pubmed_ids', '')) and str(row.get('pubmed_ids', '')) != 'nan':
            score += 1

        # 分类
        if score >= 8:
            return 'High'
        elif score >= 5:
            return 'Medium'
        else:
            return 'Low'

    def _print_statistics(self, df: pd.DataFrame):
        """打印分类统计信息"""
        print("\n" + "="*60)
        print("Classification Statistics")
        print("="*60)

        # HLA类型分布
        print("\nHLA Type Distribution:")
        hla_counts = df['hla_type'].value_counts()
        for hla_type, count in hla_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {hla_type}: {count} ({percentage:.1f}%)")

        # 样本类型分布
        print("\nSample Type Distribution:")
        sample_counts = df['sample_type'].value_counts()
        for sample_type, count in sample_counts.head(10).items():
            percentage = (count / len(df)) * 100
            print(f"  {sample_type}: {count} ({percentage:.1f}%)")

        # 疾病类别分布
        print("\nDisease Category Distribution:")
        disease_counts = df['disease_category'].value_counts()
        for category, count in disease_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")

        # 数据质量分布
        print("\nMetadata Quality Distribution:")
        quality_counts = df['metadata_quality'].value_counts()
        for quality, count in quality_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {quality}: {count} ({percentage:.1f}%)")

        # 需要人工审核的数量
        review_count = df['needs_manual_review'].sum()
        print(f"\nDatasets needing manual review: {review_count} ({(review_count/len(df)*100):.1f}%)")

    def save_results(self, df: pd.DataFrame, filename: str):
        """保存结果"""
        csv_path = DATA_PROCESSED_DIR / f"{filename}.csv"
        json_path = DATA_PROCESSED_DIR / f"{filename}.json"

        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n✓ Saved CSV to: {csv_path}")

        df.to_json(json_path, orient='records', indent=2, force_ascii=False)
        print(f"✓ Saved JSON to: {json_path}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("Metadata Classification Tool")
    print("="*60 + "\n")

    # 查找输入文件（优先使用enriched版本）
    input_files = [
        DATA_PROCESSED_DIR / "all_metadata_enriched.csv",
        DATA_PROCESSED_DIR / "all_metadata_raw.csv",
    ]

    input_file = None
    for file_path in input_files:
        if file_path.exists():
            input_file = file_path
            break

    if not input_file:
        print("✗ Error: No metadata file found!")
        print("  Please run collect_metadata.py first")
        sys.exit(1)

    print(f"Loading metadata from: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df)} datasets")

    # 执行分类
    classifier = MetadataClassifier()
    classified_df = classifier.classify_all(df)

    # 保存结果
    classifier.save_results(classified_df, "all_metadata_classified")

    print("\n✓ Classification complete!")
    print(f"\nNext step:")
    print(f"  Run generate_excel.py to create the final Excel report")
    print("\n")


if __name__ == "__main__":
    main()
