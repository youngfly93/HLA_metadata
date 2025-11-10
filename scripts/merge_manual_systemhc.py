#!/usr/bin/env python3
"""
合并手动从SysteMHC补充的数据
"""

import pandas as pd
import re
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"


def parse_hla_type_from_alleles(alleles_str: str) -> str:
    """从等位基因字符串判断HLA类型"""
    if not alleles_str or pd.isna(alleles_str) or alleles_str.strip() == '':
        return None

    alleles = alleles_str.upper()
    has_class_i = bool(re.search(r'HLA-[ABC]', alleles))
    has_class_ii = bool(re.search(r'HLA-D[RQPM]', alleles))

    if has_class_i and has_class_ii:
        return 'HLA I/II'
    elif has_class_i:
        return 'HLA I'
    elif has_class_ii:
        return 'HLA II'
    return None


def merge_manual_data():
    """合并手动填写的SysteMHC数据"""

    print("="*70)
    print("Merging Manual SysteMHC Data")
    print("="*70 + "\n")

    # 读取主数据
    main_file = DATA_PROCESSED_DIR / "all_metadata_crosschecked.csv"
    if not main_file.exists():
        print(f"✗ Error: {main_file} not found!")
        return

    df = pd.read_csv(main_file)
    print(f"✓ Loaded main data: {len(df)} datasets")

    # 读取手动填写的模板（优先使用filled版本）
    filled_file = DATA_VALIDATION_DIR / "systemhc_manual_template_filled.csv"
    manual_file = DATA_VALIDATION_DIR / "systemhc_manual_template.csv"

    if filled_file.exists():
        manual_df = pd.read_csv(filled_file)
        print(f"✓ Loaded filled template: {len(manual_df)} datasets")
    elif manual_file.exists():
        manual_df = pd.read_csv(manual_file)
        print(f"✓ Loaded manual template: {len(manual_df)} datasets")
    else:
        print(f"✗ Error: No template file found!")
        print(f"  Please fill out the template first!")
        return

    # 统计填写情况
    filled = manual_df[
        (manual_df['hla_alleles_found'].notna() & (manual_df['hla_alleles_found'] != '')) |
        (manual_df['tissues_found'].notna() & (manual_df['tissues_found'] != '')) |
        (manual_df['cell_types_found'].notna() & (manual_df['cell_types_found'] != '')) |
        (manual_df['diseases_found'].notna() & (manual_df['diseases_found'] != ''))
    ]
    print(f"✓ Filled datasets: {len(filled)}/{len(manual_df)}\n")

    if len(filled) == 0:
        print("⚠ Warning: No datasets have been filled yet!")
        print("  Please fill out the template before running this script.")
        return

    # 记录优化前统计
    before_stats = {
        'hla_unknown': len(df[df['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])]),
        'disease_unknown': len(df[df['disease_type'] == 'Unknown']),
        'sample_unknown': len(df[df['sample_type'] == 'Unknown'])
    }

    # 合并数据
    updates = []
    for idx, row in filled.iterrows():
        dataset_id = row['dataset_id']

        # 找到主数据中的对应行
        main_idx = df[df['dataset_id'] == dataset_id].index
        if len(main_idx) == 0:
            print(f"⚠ Warning: {dataset_id} not found in main data")
            continue

        main_idx = main_idx[0]
        changes = []

        # 1. 更新HLA类型
        if row['hla_alleles_found'] and pd.notna(row['hla_alleles_found']) and row['hla_alleles_found'].strip():
            new_hla_type = parse_hla_type_from_alleles(row['hla_alleles_found'])
            if new_hla_type:
                old_type = df.at[main_idx, 'hla_type']
                if old_type in ['Unknown', 'HLA (需人工确认)']:
                    df.at[main_idx, 'hla_type'] = new_hla_type
                    changes.append(f"HLA: {old_type} → {new_hla_type}")

        # 2. 更新疾病类型
        if row['diseases_found'] and pd.notna(row['diseases_found']) and row['diseases_found'].strip():
            if df.at[main_idx, 'disease_type'] == 'Unknown':
                df.at[main_idx, 'disease_type'] = row['diseases_found']
                df.at[main_idx, 'disease_inferred'] = True
                df.at[main_idx, 'inference_source'] = 'SysteMHC (manual)'
                changes.append(f"Disease: Unknown → {row['diseases_found']}")

        # 3. 更新样本类型
        if df.at[main_idx, 'sample_type'] == 'Unknown':
            cell_types = row.get('cell_types_found', '')
            tissues = row.get('tissues_found', '')

            if cell_types and pd.notna(cell_types) and cell_types.strip():
                new_sample = f"Cell line ({cell_types})"
                df.at[main_idx, 'sample_type'] = new_sample
                changes.append(f"Sample: Unknown → {new_sample}")
            elif tissues and pd.notna(tissues) and tissues.strip():
                new_sample = f"Tissue ({tissues})"
                df.at[main_idx, 'sample_type'] = new_sample
                changes.append(f"Sample: Unknown → {new_sample}")

        # 4. 标记为已验证
        df.at[main_idx, 'systemhc_verified'] = True
        df.at[main_idx, 'needs_manual_review'] = False

        if changes:
            updates.append({
                'dataset_id': dataset_id,
                'changes': changes
            })
            print(f"\n✓ Updated {dataset_id}:")
            for change in changes:
                print(f"    {change}")

    # 收集优化后统计
    after_stats = {
        'hla_unknown': len(df[df['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])]),
        'disease_unknown': len(df[df['disease_type'] == 'Unknown']),
        'sample_unknown': len(df[df['sample_type'] == 'Unknown'])
    }

    # 保存更新后的数据
    output_file = DATA_PROCESSED_DIR / "all_metadata_manually_enriched.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved to: {output_file}")

    # 生成报告
    report_file = DATA_VALIDATION_DIR / "manual_enrichment_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("手动补充数据报告\n")
        f.write("="*70 + "\n\n")

        f.write(f"一、补充概况\n")
        f.write("-"*70 + "\n")
        f.write(f"手动填写数据集: {len(filled)}\n")
        f.write(f"成功更新数据集: {len(updates)}\n\n")

        f.write("二、改进统计\n")
        f.write("-"*70 + "\n")

        f.write(f"\nHLA类型:\n")
        f.write(f"  优化前: {before_stats['hla_unknown']} Unknown\n")
        f.write(f"  优化后: {after_stats['hla_unknown']} Unknown\n")
        f.write(f"  改善: {before_stats['hla_unknown'] - after_stats['hla_unknown']}个\n")

        f.write(f"\n疾病类型:\n")
        f.write(f"  优化前: {before_stats['disease_unknown']} Unknown\n")
        f.write(f"  优化后: {after_stats['disease_unknown']} Unknown\n")
        f.write(f"  改善: {before_stats['disease_unknown'] - after_stats['disease_unknown']}个\n")

        f.write(f"\n样本类型:\n")
        f.write(f"  优化前: {before_stats['sample_unknown']} Unknown\n")
        f.write(f"  优化后: {after_stats['sample_unknown']} Unknown\n")
        f.write(f"  改善: {before_stats['sample_unknown'] - after_stats['sample_unknown']}个\n")

        f.write("\n三、详细更改\n")
        f.write("-"*70 + "\n\n")
        for update in updates:
            f.write(f"{update['dataset_id']}:\n")
            for change in update['changes']:
                f.write(f"  • {change}\n")
            f.write("\n")

        total_improvement = sum([
            before_stats['hla_unknown'] - after_stats['hla_unknown'],
            before_stats['disease_unknown'] - after_stats['disease_unknown'],
            before_stats['sample_unknown'] - after_stats['sample_unknown']
        ])

        f.write("四、数据质量提升\n")
        f.write("-"*70 + "\n")
        f.write(f"总改善字段数: {total_improvement}\n")
        f.write(f"新的Unknown比例: {after_stats['disease_unknown']/147*100:.1f}%\n")

    print(f"✓ Report saved to: {report_file}")

    # 打印摘要
    print("\n" + "="*70)
    print("Merge Summary")
    print("="*70)
    print(f"\nManually filled: {len(filled)} datasets")
    print(f"Successfully updated: {len(updates)} datasets")

    print(f"\nImprovements:")
    print(f"  HLA: {before_stats['hla_unknown']} → {after_stats['hla_unknown']} Unknown")
    print(f"  Disease: {before_stats['disease_unknown']} → {after_stats['disease_unknown']} Unknown")
    print(f"  Sample: {before_stats['sample_unknown']} → {after_stats['sample_unknown']} Unknown")

    print(f"\nNext step: Run generate_excel.py to update the Excel report")
    print()


if __name__ == "__main__":
    merge_manual_data()
