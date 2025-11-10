#!/usr/bin/env python3
"""
SDRF文件解析脚本
从SDRF (Sample and Data Relationship Format) 文件中提取详细的样本元数据
"""

import os
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
SDRF_DIR = PROJECT_ROOT / "data" / "raw" / "sdrf_files"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


class SDRFParser:
    """SDRF文件解析器"""

    def __init__(self):
        self.characteristics_prefix = "characteristics["
        self.comment_prefix = "comment["
        self.factor_prefix = "factor value["

    def parse_sdrf_file(self, sdrf_path: str) -> Optional[Dict]:
        """
        解析单个SDRF文件

        Args:
            sdrf_path: SDRF文件路径

        Returns:
            包含样本元数据的字典
        """
        try:
            # 读取SDRF文件
            df = pd.read_csv(sdrf_path, sep='\t', low_memory=False)

            if df.empty:
                return None

            # 提取数据集ID
            dataset_id = Path(sdrf_path).stem.replace('.sdrf', '')

            # 提取样本特征
            characteristics = self._extract_characteristics(df)

            # 提取技术信息
            technical_info = self._extract_technical_info(df)

            # 提取因子值
            factors = self._extract_factors(df)

            # 合并所有信息
            metadata = {
                'dataset_id': dataset_id,
                'sample_count': len(df),
                **characteristics,
                **technical_info,
                **factors,
            }

            return metadata

        except Exception as e:
            print(f"  ✗ Error parsing {sdrf_path}: {e}")
            return None

    def _extract_characteristics(self, df: pd.DataFrame) -> Dict:
        """提取characteristics列（样本特征）"""
        characteristics = {}

        # 查找所有characteristics列
        char_columns = [col for col in df.columns if col.startswith(self.characteristics_prefix)]

        for col in char_columns:
            # 提取字段名（去掉前缀和后缀）
            field_name = col.replace(self.characteristics_prefix, '').replace(']', '')

            # 获取唯一值
            unique_values = df[col].dropna().unique()

            if len(unique_values) > 0:
                # 如果值太多（超过10个），只记录数量
                if len(unique_values) > 10:
                    characteristics[f'sdrf_{field_name}'] = f"{len(unique_values)} unique values"
                else:
                    # 拼接唯一值
                    characteristics[f'sdrf_{field_name}'] = '; '.join(str(v) for v in unique_values)

        return characteristics

    def _extract_technical_info(self, df: pd.DataFrame) -> Dict:
        """提取技术信息（comment列）"""
        technical = {}

        # 查找所有comment列
        comment_columns = [col for col in df.columns if col.startswith(self.comment_prefix)]

        for col in comment_columns:
            field_name = col.replace(self.comment_prefix, '').replace(']', '')
            unique_values = df[col].dropna().unique()

            if len(unique_values) > 0:
                if len(unique_values) > 10:
                    technical[f'tech_{field_name}'] = f"{len(unique_values)} unique values"
                else:
                    technical[f'tech_{field_name}'] = '; '.join(str(v) for v in unique_values)

        return technical

    def _extract_factors(self, df: pd.DataFrame) -> Dict:
        """提取实验因子"""
        factors = {}

        # 查找所有factor value列
        factor_columns = [col for col in df.columns if col.startswith(self.factor_prefix)]

        for col in factor_columns:
            field_name = col.replace(self.factor_prefix, '').replace(']', '')
            unique_values = df[col].dropna().unique()

            if len(unique_values) > 0:
                if len(unique_values) > 10:
                    factors[f'factor_{field_name}'] = f"{len(unique_values)} unique values"
                else:
                    factors[f'factor_{field_name}'] = '; '.join(str(v) for v in unique_values)

        return factors

    def parse_all_sdrf_files(self) -> pd.DataFrame:
        """
        解析所有SDRF文件

        Returns:
            包含所有SDRF元数据的DataFrame
        """
        if not SDRF_DIR.exists():
            print(f"✗ SDRF directory not found: {SDRF_DIR}")
            return pd.DataFrame()

        sdrf_files = list(SDRF_DIR.glob("*.sdrf.tsv"))

        if not sdrf_files:
            print(f"✗ No SDRF files found in {SDRF_DIR}")
            return pd.DataFrame()

        print(f"\n{'='*60}")
        print(f"Parsing {len(sdrf_files)} SDRF files")
        print(f"{'='*60}\n")

        all_metadata = []

        for i, sdrf_file in enumerate(sdrf_files, 1):
            dataset_id = sdrf_file.stem.replace('.sdrf', '')
            print(f"[{i}/{len(sdrf_files)}] Parsing {dataset_id}")

            metadata = self.parse_sdrf_file(str(sdrf_file))

            if metadata:
                all_metadata.append(metadata)
                print(f"  ✓ Successfully parsed {dataset_id} ({metadata['sample_count']} samples)")
            else:
                print(f"  ✗ Failed to parse {dataset_id}")

        print(f"\n✓ Completed SDRF parsing: {len(all_metadata)} files\n")

        return pd.DataFrame(all_metadata)

    def merge_with_main_metadata(self, sdrf_df: pd.DataFrame) -> pd.DataFrame:
        """
        将SDRF元数据与主元数据合并

        Args:
            sdrf_df: SDRF解析结果

        Returns:
            合并后的DataFrame
        """
        # 读取主元数据
        main_metadata_file = DATA_PROCESSED_DIR / "all_metadata_raw.csv"

        if not main_metadata_file.exists():
            print(f"✗ Main metadata file not found: {main_metadata_file}")
            print("  Please run collect_metadata.py first")
            return sdrf_df

        print(f"Loading main metadata from: {main_metadata_file}")
        main_df = pd.read_csv(main_metadata_file)

        # 合并数据
        print(f"Merging SDRF data with main metadata...")
        merged_df = main_df.merge(
            sdrf_df,
            on='dataset_id',
            how='left',
            suffixes=('', '_sdrf')
        )

        print(f"✓ Merged {len(merged_df)} records")

        # 填充缺失的疾病、组织信息（从SDRF）
        self._enrich_metadata(merged_df)

        return merged_df

    def _enrich_metadata(self, df: pd.DataFrame):
        """
        使用SDRF数据丰富主元数据
        如果主元数据中某些字段为空，尝试从SDRF数据中填充
        """
        # 疾病信息
        if 'sdrf_disease' in df.columns:
            df['diseases'] = df.apply(
                lambda row: row['sdrf_disease'] if pd.isna(row['diseases']) or row['diseases'] == ''
                else row['diseases'],
                axis=1
            )

        # 组织信息
        if 'sdrf_organism part' in df.columns:
            df['tissues'] = df.apply(
                lambda row: row['sdrf_organism part'] if pd.isna(row['tissues']) or row['tissues'] == ''
                else row['tissues'],
                axis=1
            )

        # 细胞类型
        if 'sdrf_cell type' in df.columns:
            df['cell_types'] = df.apply(
                lambda row: row['sdrf_cell type'] if pd.isna(row['cell_types']) or row['cell_types'] == ''
                else row['cell_types'],
                axis=1
            )

        # 细胞系
        if 'sdrf_cell line' in df.columns and 'cell_line' not in df.columns:
            df['cell_line'] = df['sdrf_cell line']

        # 年龄
        if 'sdrf_age' in df.columns and 'age' not in df.columns:
            df['age'] = df['sdrf_age']

        # 性别
        if 'sdrf_sex' in df.columns and 'sex' not in df.columns:
            df['sex'] = df['sdrf_sex']

        print("✓ Enriched metadata with SDRF information")

    def save_results(self, df: pd.DataFrame, filename: str):
        """保存结果"""
        csv_path = DATA_PROCESSED_DIR / f"{filename}.csv"
        json_path = DATA_PROCESSED_DIR / f"{filename}.json"

        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ Saved CSV to: {csv_path}")

        df.to_json(json_path, orient='records', indent=2, force_ascii=False)
        print(f"✓ Saved JSON to: {json_path}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("SDRF Parser Tool")
    print("="*60 + "\n")

    parser = SDRFParser()

    # 解析所有SDRF文件
    sdrf_df = parser.parse_all_sdrf_files()

    if sdrf_df.empty:
        print("✗ No SDRF data parsed. Exiting.")
        sys.exit(1)

    # 保存SDRF解析结果
    parser.save_results(sdrf_df, "sdrf_parsed")

    # 与主元数据合并
    merged_df = parser.merge_with_main_metadata(sdrf_df)

    if not merged_df.empty:
        parser.save_results(merged_df, "all_metadata_enriched")

        print("\n" + "="*60)
        print("Parsing Summary")
        print("="*60)
        print(f"SDRF files parsed: {len(sdrf_df)}")
        print(f"Total datasets in merged file: {len(merged_df)}")

        # 统计增强的字段
        if 'sdrf_disease' in merged_df.columns:
            disease_count = merged_df['sdrf_disease'].notna().sum()
            print(f"Datasets with disease info from SDRF: {disease_count}")

        if 'sdrf_organism part' in merged_df.columns:
            tissue_count = merged_df['sdrf_organism part'].notna().sum()
            print(f"Datasets with tissue info from SDRF: {tissue_count}")

        if 'sdrf_cell type' in merged_df.columns:
            cell_count = merged_df['sdrf_cell type'].notna().sum()
            print(f"Datasets with cell type info from SDRF: {cell_count}")

        print("\n✓ SDRF parsing complete!")
        print(f"\nNext steps:")
        print(f"  1. Run classify_metadata.py to classify HLA types and sample types")
        print(f"  2. Run generate_excel.py to create the final report")

    print("\n")


if __name__ == "__main__":
    main()
