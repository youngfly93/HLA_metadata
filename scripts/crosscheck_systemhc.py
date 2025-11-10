#!/usr/bin/env python3
"""
与SysteMHC数据库交叉验证和补充元数据
"""

import pandas as pd
import requests
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
import time

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"


class SysteMHCCrossChecker:
    """SysteMHC交叉验证器"""

    def __init__(self):
        self.systemhc_base = "https://systemhc.sjtu.edu.cn"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_systemhc_datasets_page(self) -> Optional[str]:
        """获取SysteMHC的datasets页面"""
        try:
            url = f"{self.systemhc_base}/datasets"
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching SysteMHC datasets: {e}")
            return None

    def parse_dataset_ids_from_html(self, html: str) -> List[Dict]:
        """从HTML中解析数据集ID"""
        datasets = []

        # 查找PXD, MSV, JPST, PASS等ID
        pxd_pattern = r'(PXD\d{6})'
        msv_pattern = r'(MSV\d{9})'
        jpst_pattern = r'(JPST\d{6})'
        pass_pattern = r'(PASS\d{5})'

        # 提取所有匹配
        pxd_ids = re.findall(pxd_pattern, html)
        msv_ids = re.findall(msv_pattern, html)
        jpst_ids = re.findall(jpst_pattern, html)
        pass_ids = re.findall(pass_pattern, html)

        # 合并并去重
        all_ids = set(pxd_ids + msv_ids + jpst_ids + pass_ids)

        print(f"\nFound dataset IDs in SysteMHC:")
        print(f"  PXD: {len(set(pxd_ids))}")
        print(f"  MSV: {len(set(msv_ids))}")
        print(f"  JPST: {len(set(jpst_ids))}")
        print(f"  PASS: {len(set(pass_ids))}")
        print(f"  Total unique: {len(all_ids)}")

        return list(all_ids)

    def cross_check_with_our_data(self, systemhc_ids: List[str],
                                   our_df: pd.DataFrame) -> pd.DataFrame:
        """
        交叉验证我们的数据集与SysteMHC

        Args:
            systemhc_ids: SysteMHC中的数据集ID列表
            our_df: 我们的元数据DataFrame

        Returns:
            添加了交叉验证信息的DataFrame
        """
        print("\n" + "="*70)
        print("Cross-checking with SysteMHC")
        print("="*70 + "\n")

        # 创建新列
        our_df['in_systemhc'] = False
        our_df['systemhc_verified'] = False

        # 检查每个数据集是否在SysteMHC中
        for idx, row in our_df.iterrows():
            dataset_id = row['dataset_id']
            if dataset_id in systemhc_ids:
                our_df.at[idx, 'in_systemhc'] = True
                our_df.at[idx, 'systemhc_verified'] = True

        # 统计
        in_systemhc = our_df['in_systemhc'].sum()
        not_in_systemhc = len(our_df) - in_systemhc

        print(f"Dataset overlap analysis:")
        print(f"  Our datasets: {len(our_df)}")
        print(f"  In SysteMHC: {in_systemhc} ({in_systemhc/len(our_df)*100:.1f}%)")
        print(f"  Not in SysteMHC: {not_in_systemhc} ({not_in_systemhc/len(our_df)*100:.1f}%)")

        return our_df

    def analyze_missing_datasets(self, df: pd.DataFrame) -> Dict:
        """分析不在SysteMHC中的数据集"""
        not_in_systemhc = df[df['in_systemhc'] == False]

        analysis = {
            'total_missing': len(not_in_systemhc),
            'by_repository': not_in_systemhc['repository'].value_counts().to_dict(),
            'by_hla_type': not_in_systemhc['hla_type'].value_counts().to_dict(),
            'unknown_diseases': len(not_in_systemhc[not_in_systemhc['disease_type'] == 'Unknown']),
        }

        print("\n" + "="*70)
        print("Analysis of datasets NOT in SysteMHC")
        print("="*70 + "\n")

        print(f"Total not in SysteMHC: {analysis['total_missing']}")
        print("\nBy repository:")
        for repo, count in analysis['by_repository'].items():
            print(f"  {repo}: {count}")

        print("\nBy HLA type:")
        for hla, count in analysis['by_hla_type'].items():
            print(f"  {hla}: {count}")

        print(f"\nWith Unknown disease: {analysis['unknown_diseases']}")

        return analysis

    def suggest_systemhc_lookup(self, df: pd.DataFrame) -> List[str]:
        """
        建议哪些数据集应该在SysteMHC中手动查找
        优先级：Unknown疾病类型 + 在SysteMHC中
        """
        # 选择：在SysteMHC中但疾病类型为Unknown的数据集
        candidates = df[
            (df['in_systemhc'] == True) &
            (df['disease_type'] == 'Unknown')
        ]

        suggestions = []
        print("\n" + "="*70)
        print("Datasets in SysteMHC that could benefit from manual lookup")
        print("="*70 + "\n")

        print(f"Found {len(candidates)} datasets with Unknown disease in SysteMHC\n")

        for idx, row in candidates.head(20).iterrows():
            suggestions.append(row['dataset_id'])
            print(f"  {row['dataset_id']} - HLA: {row['hla_type']}")
            print(f"    URL: https://systemhc.sjtu.edu.cn/datasets")
            print(f"    Search for: {row['dataset_id']}")
            print()

        return suggestions

    def generate_cross_check_report(self, df: pd.DataFrame, analysis: Dict):
        """生成交叉验证报告"""
        report_file = DATA_VALIDATION_DIR / "systemhc_crosscheck_report.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("SysteMHC交叉验证报告\n")
            f.write("="*70 + "\n\n")

            f.write("一、数据集重叠分析\n")
            f.write("-"*70 + "\n")
            in_systemhc = df['in_systemhc'].sum()
            f.write(f"我们的数据集总数: {len(df)}\n")
            f.write(f"在SysteMHC中的数据集: {in_systemhc} ({in_systemhc/len(df)*100:.1f}%)\n")
            f.write(f"不在SysteMHC中: {len(df)-in_systemhc}\n\n")

            f.write("二、不在SysteMHC中的数据集分布\n")
            f.write("-"*70 + "\n")
            f.write(f"总数: {analysis['total_missing']}\n\n")

            f.write("按数据库分布:\n")
            for repo, count in analysis['by_repository'].items():
                f.write(f"  {repo}: {count}\n")

            f.write("\n按HLA类型分布:\n")
            for hla, count in analysis['by_hla_type'].items():
                f.write(f"  {hla}: {count}\n")

            f.write("\n三、在SysteMHC中但疾病类型为Unknown的数据集\n")
            f.write("-"*70 + "\n")

            unknown_in_systemhc = df[
                (df['in_systemhc'] == True) &
                (df['disease_type'] == 'Unknown')
            ]

            f.write(f"数量: {len(unknown_in_systemhc)}\n\n")
            f.write("建议手动查找的数据集:\n")

            for idx, row in unknown_in_systemhc.iterrows():
                f.write(f"\n{row['dataset_id']}\n")
                f.write(f"  HLA类型: {row['hla_type']}\n")
                f.write(f"  样本类型: {row['sample_type']}\n")
                f.write(f"  标题: {str(row['title'])[:60]}...\n")
                f.write(f"  SysteMHC链接: https://systemhc.sjtu.edu.cn/datasets\n")

            f.write("\n四、使用SysteMHC补充数据的建议\n")
            f.write("-"*70 + "\n")
            f.write("1. 访问 https://systemhc.sjtu.edu.cn/datasets\n")
            f.write("2. 搜索上述数据集ID\n")
            f.write("3. 查看详细的HLA等位基因信息\n")
            f.write("4. 查看疾病类型和样本信息\n")
            f.write("5. 更新我们的元数据表格\n\n")

            f.write("五、SysteMHC的优势\n")
            f.write("-"*70 + "\n")
            f.write("• 专注于HLA/MHC免疫肽组学\n")
            f.write("• 包含详细的HLA等位基因信息\n")
            f.write("• 提供样本统计和图表\n")
            f.write("• 可下载光谱库\n")
            f.write("• 与PRIDE、MassIVE等数据库关联\n\n")

        print(f"\n✓ Cross-check report saved to: {report_file}")

    def save_results(self, df: pd.DataFrame):
        """保存交叉验证后的结果"""
        output_file = DATA_PROCESSED_DIR / "all_metadata_crosschecked.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✓ Saved to: {output_file}")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("SysteMHC Cross-Check Tool")
    print("="*70 + "\n")

    # 读取我们的数据
    input_file = DATA_PROCESSED_DIR / "all_metadata_inferred.csv"
    if not input_file.exists():
        input_file = DATA_PROCESSED_DIR / "all_metadata_cleaned.csv"

    if not input_file.exists():
        print(f"✗ Error: No metadata file found!")
        return

    print(f"Loading our data from: {input_file}")
    our_df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(our_df)} datasets\n")

    # 初始化交叉验证器
    checker = SysteMHCCrossChecker()

    # 获取SysteMHC数据
    print("Fetching SysteMHC dataset information...")
    html = checker.fetch_systemhc_datasets_page()

    if not html:
        print("✗ Failed to fetch SysteMHC data")
        print("\n建议手动访问:")
        print("  https://systemhc.sjtu.edu.cn/datasets")
        return

    # 解析数据集ID
    systemhc_ids = checker.parse_dataset_ids_from_html(html)

    if not systemhc_ids:
        print("✗ No dataset IDs found in SysteMHC")
        return

    # 交叉验证
    our_df = checker.cross_check_with_our_data(systemhc_ids, our_df)

    # 分析缺失数据
    analysis = checker.analyze_missing_datasets(our_df)

    # 生成建议
    suggestions = checker.suggest_systemhc_lookup(our_df)

    # 生成报告
    checker.generate_cross_check_report(our_df, analysis)

    # 保存结果
    checker.save_results(our_df)

    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"✓ Datasets in SysteMHC: {our_df['in_systemhc'].sum()}")
    print(f"✓ Datasets NOT in SysteMHC: {(~our_df['in_systemhc']).sum()}")
    print(f"✓ Unknown diseases in SysteMHC: {len(suggestions)}")
    print("\nNext steps:")
    print("  1. Review the cross-check report")
    print("  2. Manually look up suggested datasets in SysteMHC")
    print("  3. Update metadata with findings")
    print("\n")


if __name__ == "__main__":
    main()
