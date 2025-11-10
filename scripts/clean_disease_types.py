#!/usr/bin/env python3
"""
清理和规范化疾病类型数据
从JSON格式提取疾病名称，统一格式
"""

import pandas as pd
import re
import json
from pathlib import Path
from typing import List, Optional

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


class DiseaseTypeCleaner:
    """疾病类型清理器"""

    def __init__(self):
        self.disease_mapping = {
            # 标准化疾病名称
            'Disease free': 'Healthy/Control',
            'Disease': 'Unknown',  # 过于通用的术语
        }

    def extract_disease_name(self, disease_str: str) -> Optional[str]:
        """
        从JSON格式或其他格式中提取疾病名称

        Args:
            disease_str: 疾病字符串（可能包含JSON）

        Returns:
            清理后的疾病名称
        """
        if not disease_str or pd.isna(disease_str) or str(disease_str).strip() == '':
            return 'Unknown'

        disease_str = str(disease_str).strip()

        # 如果已经是干净的格式
        if disease_str in ['Unknown', 'Healthy/Control']:
            return disease_str

        # 检查是否包含 {'@type': 'CvParam' 格式
        if "'@type'" in disease_str or '"@type"' in disease_str:
            return self._parse_json_diseases(disease_str)

        # 否则直接返回
        return disease_str

    def _parse_json_diseases(self, disease_str: str) -> str:
        """
        解析包含JSON格式的疾病字符串

        Args:
            disease_str: 包含JSON的字符串

        Returns:
            提取的疾病名称（多个用分号分隔）
        """
        disease_names = []

        # 将单引号替换为双引号以便JSON解析
        disease_str_json = disease_str.replace("'", '"')

        # 尝试提取所有 "name" 字段的值
        name_pattern = r'"name":\s*"([^"]+)"'
        matches = re.findall(name_pattern, disease_str_json)

        for match in matches:
            disease_name = match.strip()

            # 应用映射
            disease_name = self.disease_mapping.get(disease_name, disease_name)

            # 过滤掉过于通用的术语
            if disease_name and disease_name != 'Unknown':
                disease_names.append(disease_name)

        if not disease_names:
            return 'Unknown'

        # 去重并排序
        disease_names = sorted(set(disease_names))

        # 用分号连接
        return '; '.join(disease_names)

    def standardize_disease_name(self, disease_name: str) -> str:
        """
        标准化疾病名称

        Args:
            disease_name: 疾病名称

        Returns:
            标准化后的疾病名称
        """
        if not disease_name or disease_name == 'Unknown':
            return 'Unknown'

        # 首字母大写
        disease_name = disease_name.strip()

        # 应用映射
        disease_name = self.disease_mapping.get(disease_name, disease_name)

        return disease_name

    def clean_all_diseases(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清理所有数据集的疾病类型

        Args:
            df: 输入DataFrame

        Returns:
            清理后的DataFrame
        """
        print("\n" + "="*60)
        print("Cleaning Disease Types")
        print("="*60 + "\n")

        # 清理disease_type字段
        if 'disease_type' in df.columns:
            print("Cleaning 'disease_type' column...")
            df['disease_type_original'] = df['disease_type'].copy()
            df['disease_type'] = df['disease_type'].apply(self.extract_disease_name)
            print("✓ Cleaned 'disease_type' column")

        # 清理diseases字段（如果存在）
        if 'diseases' in df.columns:
            print("Cleaning 'diseases' column...")
            df['diseases_original'] = df['diseases'].copy()
            df['diseases'] = df['diseases'].apply(self.extract_disease_name)
            print("✓ Cleaned 'diseases' column")

        # 重新分类疾病类别（基于清理后的数据）
        print("\nRe-classifying disease categories...")
        df = self._reclassify_disease_categories(df)

        # 统计
        self._print_statistics(df)

        return df

    def _reclassify_disease_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """重新分类疾病类别"""
        cancer_keywords = [
            'cancer', 'carcinoma', 'melanoma', 'leukemia', 'lymphoma',
            'sarcoma', 'glioblastoma', 'neuroblastoma', 'adenocarcinoma',
            'neoplasm', 'tumor', 'tumour'
        ]

        neurodegenerative_keywords = [
            'alzheimer', 'parkinson', 'dementia', 'multiple sclerosis',
            'als', 'huntington'
        ]

        infectious_keywords = [
            'covid', 'sars', 'influenza', 'hiv', 'virus', 'bacterial',
            'infection', 'tuberculosis', 'hepatitis', 'theileriasis'
        ]

        autoimmune_keywords = [
            'rheumatoid', 'lupus', 'arthritis', 'spondylitis',
            'ankylos', 'autoimmune'
        ]

        other_disease_keywords = [
            'diabetes', 'fibrosis', 'chorioretinopathy', 'lyme'
        ]

        def classify_category(row):
            disease = str(row.get('disease_type', '')).lower()

            if disease in ['unknown', 'nan', '']:
                return 'Unknown'

            if 'healthy' in disease or 'control' in disease or 'disease free' in disease:
                return 'Healthy'

            # 检查各类疾病
            if any(keyword in disease for keyword in cancer_keywords):
                return 'Cancer'

            if any(keyword in disease for keyword in neurodegenerative_keywords):
                return 'Neurodegenerative'

            if any(keyword in disease for keyword in infectious_keywords):
                return 'Infectious Disease'

            if any(keyword in disease for keyword in autoimmune_keywords):
                return 'Autoimmune Disease'

            if any(keyword in disease for keyword in other_disease_keywords):
                return 'Metabolic/Other Disease'

            return 'Other'

        df['disease_category'] = df.apply(classify_category, axis=1)

        return df

    def _print_statistics(self, df: pd.DataFrame):
        """打印清理后的统计信息"""
        print("\n" + "="*60)
        print("Disease Type Statistics (After Cleaning)")
        print("="*60)

        # 统计Unknown的数量
        unknown_count = (df['disease_type'] == 'Unknown').sum()
        print(f"\nUnknown diseases: {unknown_count} ({unknown_count/len(df)*100:.1f}%)")

        # 统计Healthy/Control的数量
        healthy_count = (df['disease_type'] == 'Healthy/Control').sum()
        print(f"Healthy/Control: {healthy_count} ({healthy_count/len(df)*100:.1f}%)")

        # 疾病类别分布
        print("\nDisease Category Distribution:")
        category_counts = df['disease_category'].value_counts()
        for category, count in category_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")

        # 显示前20个具体疾病
        print("\nTop 20 Specific Diseases:")
        disease_counts = df['disease_type'].value_counts().head(20)
        for disease, count in disease_counts.items():
            if disease not in ['Unknown', 'Healthy/Control']:
                print(f"  {disease}: {count}")

    def save_results(self, df: pd.DataFrame, filename: str):
        """保存清理后的结果"""
        csv_path = DATA_PROCESSED_DIR / f"{filename}.csv"
        json_path = DATA_PROCESSED_DIR / f"{filename}.json"
        excel_path = DATA_PROCESSED_DIR / f"{filename}.xlsx"

        # 保存CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n✓ Saved CSV to: {csv_path}")

        # 保存JSON
        df.to_json(json_path, orient='records', indent=2, force_ascii=False)
        print(f"✓ Saved JSON to: {json_path}")

        # 保存Excel（只包含主要列，不包含original列）
        main_columns = [col for col in df.columns if not col.endswith('_original')]
        df[main_columns].to_excel(excel_path, index=False)
        print(f"✓ Saved Excel to: {excel_path}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("Disease Type Cleaning Tool")
    print("="*60 + "\n")

    # 读取分类后的元数据
    input_file = DATA_PROCESSED_DIR / "all_metadata_classified.csv"

    if not input_file.exists():
        print(f"✗ Error: {input_file} not found!")
        return

    print(f"Loading data from: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df)} datasets\n")

    # 显示清理前的示例
    print("Example of disease types BEFORE cleaning:")
    print(df['disease_type'].head(10).to_string())
    print()

    # 清理疾病类型
    cleaner = DiseaseTypeCleaner()
    df_cleaned = cleaner.clean_all_diseases(df)

    # 显示清理后的示例
    print("\n" + "="*60)
    print("Example of disease types AFTER cleaning:")
    print(df_cleaned['disease_type'].head(10).to_string())
    print()

    # 保存结果
    cleaner.save_results(df_cleaned, "all_metadata_cleaned")

    print("\n✓ Disease type cleaning complete!")
    print("\nNext step:")
    print("  Run generate_excel.py to regenerate the Excel report with cleaned data")
    print("\n")


if __name__ == "__main__":
    main()
