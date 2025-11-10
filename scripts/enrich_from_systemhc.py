#!/usr/bin/env python3
"""
从SysteMHC自动提取数据并补充我们的元数据
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from pathlib import Path
from typing import Dict, Optional, List
from urllib.parse import quote

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"

class SysteMHCEnricher:
    """SysteMHC数据补充器"""

    def __init__(self):
        self.base_url = "https://systemhc.sjtu.edu.cn"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.systemhc_data = {}

    def try_simple_fetch(self, dataset_id: str) -> Optional[Dict]:
        """
        尝试简单的HTTP请求获取数据集页面
        """
        try:
            url = f"{self.base_url}/dataset/?dataset_id={dataset_id}"
            print(f"  Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 尝试从页面中提取信息
            data = self._parse_dataset_page(soup, dataset_id)

            if data and any(data.values()):
                return data
            else:
                print(f"    ⚠ Page loaded but no data extracted (JavaScript-rendered)")
                return None

        except Exception as e:
            print(f"    ✗ Error: {e}")
            return None

    def _parse_dataset_page(self, soup: BeautifulSoup, dataset_id: str) -> Dict:
        """
        从BeautifulSoup对象中解析数据集信息
        尝试多种方式提取数据
        """
        data = {
            'dataset_id': dataset_id,
            'hla_alleles': [],
            'tissues': [],
            'diseases': [],
            'cell_types': [],
            'organisms': []
        }

        # 方法1: 查找表格数据
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # 跳过表头
                cells = row.find_all('td')
                if len(cells) >= 5:
                    # 假设列顺序: SampleID, NumReplicates, Organism, TissueType, CellType, MHCAllele
                    if len(cells) > 2:
                        organism = cells[2].get_text(strip=True)
                        if organism and organism not in data['organisms']:
                            data['organisms'].append(organism)

                    if len(cells) > 3:
                        tissue = cells[3].get_text(strip=True)
                        if tissue and tissue not in data['tissues']:
                            data['tissues'].append(tissue)

                    if len(cells) > 4:
                        cell_type = cells[4].get_text(strip=True)
                        if cell_type and cell_type not in data['cell_types']:
                            data['cell_types'].append(cell_type)

                    if len(cells) > 5:
                        mhc_allele = cells[5].get_text(strip=True)
                        if mhc_allele and mhc_allele not in data['hla_alleles']:
                            data['hla_alleles'].append(mhc_allele)

        # 方法2: 查找页面中的关键词
        page_text = soup.get_text()

        # 提取HLA等位基因
        hla_patterns = [
            r'HLA-[A-Z]\*\d+:\d+',
            r'HLA-[A-Z][A-Z]+\*\d+:\d+',
        ]
        for pattern in hla_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                if match not in data['hla_alleles']:
                    data['hla_alleles'].append(match)

        # 方法3: 查找meta标签或JSON-LD数据
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            if meta.get('name') == 'description':
                desc = meta.get('content', '')
                # 从描述中提取疾病关键词
                self._extract_diseases_from_text(desc, data['diseases'])

        # 查找JSON-LD数据
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                json_data = json.loads(script.string)
                # 尝试从JSON中提取相关信息
                if isinstance(json_data, dict):
                    if 'disease' in json_data:
                        disease = json_data['disease']
                        if disease not in data['diseases']:
                            data['diseases'].append(disease)
            except:
                pass

        return data

    def _extract_diseases_from_text(self, text: str, diseases_list: List):
        """从文本中提取疾病关键词"""
        disease_keywords = [
            'melanoma', 'cancer', 'leukemia', 'lymphoma', 'carcinoma',
            'COVID-19', 'influenza', 'tuberculosis', 'HIV',
            'diabetes', 'alzheimer', 'parkinson', 'multiple sclerosis'
        ]
        text_lower = text.lower()
        for keyword in disease_keywords:
            if keyword in text_lower and keyword not in [d.lower() for d in diseases_list]:
                diseases_list.append(keyword.title())

    def fetch_dataset_info(self, dataset_id: str) -> Optional[Dict]:
        """
        获取单个数据集的信息
        """
        print(f"\nProcessing: {dataset_id}")

        # 尝试简单的HTTP请求
        data = self.try_simple_fetch(dataset_id)

        if data:
            print(f"    ✓ Extracted data:")
            if data.get('hla_alleles'):
                print(f"      HLA alleles: {', '.join(data['hla_alleles'][:3])}{'...' if len(data['hla_alleles']) > 3 else ''}")
            if data.get('tissues'):
                print(f"      Tissues: {', '.join(data['tissues'][:3])}")
            if data.get('diseases'):
                print(f"      Diseases: {', '.join(data['diseases'])}")

        return data

    def batch_fetch_datasets(self, dataset_ids: List[str]) -> Dict[str, Dict]:
        """
        批量获取数据集信息
        """
        results = {}
        total = len(dataset_ids)

        for i, dataset_id in enumerate(dataset_ids, 1):
            print(f"\n[{i}/{total}] Processing {dataset_id}")

            data = self.fetch_dataset_info(dataset_id)
            if data:
                results[dataset_id] = data

            # 礼貌性延迟
            if i < total:
                time.sleep(2)

        return results

    def compare_and_supplement(self, our_df: pd.DataFrame,
                               systemhc_data: Dict[str, Dict]) -> pd.DataFrame:
        """
        比较SysteMHC数据与我们的数据，并补充Unknown字段
        """
        print("\n" + "="*70)
        print("Comparing and Supplementing Data")
        print("="*70 + "\n")

        comparison_report = []
        updated_count = 0

        for idx, row in our_df.iterrows():
            dataset_id = row['dataset_id']

            if dataset_id not in systemhc_data:
                continue

            systemhc_info = systemhc_data[dataset_id]
            changes = []

            # 1. 比较和补充HLA类型
            if row['hla_type'] == 'Unknown' or row['hla_type'] == 'HLA (需人工确认)':
                if systemhc_info.get('hla_alleles'):
                    # 从等位基因判断HLA类型
                    alleles = systemhc_info['hla_alleles']
                    has_class_i = any(re.search(r'HLA-[ABC]', a) for a in alleles)
                    has_class_ii = any(re.search(r'HLA-D[RQPM]', a) for a in alleles)

                    new_hla_type = None
                    if has_class_i and has_class_ii:
                        new_hla_type = 'HLA I/II'
                    elif has_class_i:
                        new_hla_type = 'HLA I'
                    elif has_class_ii:
                        new_hla_type = 'HLA II'

                    if new_hla_type:
                        changes.append(f"HLA type: {row['hla_type']} → {new_hla_type}")
                        our_df.at[idx, 'hla_type'] = new_hla_type
                        our_df.at[idx, 'needs_manual_review'] = False
                        our_df.at[idx, 'systemhc_verified'] = True

            # 2. 比较和补充疾病类型
            if row['disease_type'] == 'Unknown':
                if systemhc_info.get('diseases'):
                    new_disease = '; '.join(systemhc_info['diseases'])
                    changes.append(f"Disease: Unknown → {new_disease}")
                    our_df.at[idx, 'disease_type'] = new_disease
                    our_df.at[idx, 'disease_inferred'] = True
                    our_df.at[idx, 'inference_source'] = 'SysteMHC'

            # 3. 比较和补充样本类型
            if row['sample_type'] == 'Unknown':
                tissues = systemhc_info.get('tissues', [])
                cell_types = systemhc_info.get('cell_types', [])

                if cell_types:
                    new_sample = f"Cell line ({', '.join(cell_types[:2])})"
                    changes.append(f"Sample type: Unknown → {new_sample}")
                    our_df.at[idx, 'sample_type'] = new_sample
                elif tissues:
                    new_sample = f"Tissue ({', '.join(tissues[:2])})"
                    changes.append(f"Sample type: Unknown → {new_sample}")
                    our_df.at[idx, 'sample_type'] = new_sample

            # 4. 补充HLA等位基因信息
            if systemhc_info.get('hla_alleles'):
                alleles_str = '; '.join(systemhc_info['hla_alleles'][:10])
                if pd.isna(row.get('hla_alleles')) or not row.get('hla_alleles'):
                    our_df.at[idx, 'hla_alleles'] = alleles_str
                    changes.append(f"Added HLA alleles: {alleles_str[:50]}...")

            if changes:
                updated_count += 1
                comparison_report.append({
                    'dataset_id': dataset_id,
                    'changes': changes
                })
                print(f"\n✓ Updated {dataset_id}:")
                for change in changes:
                    print(f"    {change}")

        print(f"\n" + "="*70)
        print(f"Summary: Updated {updated_count} datasets")
        print("="*70 + "\n")

        return our_df, comparison_report

    def generate_comparison_report(self, comparison_report: List[Dict],
                                   before_stats: Dict, after_stats: Dict):
        """
        生成详细的比较和补充报告
        """
        report_file = DATA_VALIDATION_DIR / "systemhc_enrichment_report.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("SysteMHC数据补充报告\n")
            f.write("="*70 + "\n\n")

            f.write("一、数据补充概况\n")
            f.write("-"*70 + "\n")
            f.write(f"总补充数据集数: {len(comparison_report)}\n\n")

            f.write("二、字段改进统计\n")
            f.write("-"*70 + "\n")

            # HLA类型改进
            hla_before = before_stats.get('hla_unknown', 0)
            hla_after = after_stats.get('hla_unknown', 0)
            f.write(f"\nHLA类型:\n")
            f.write(f"  优化前 Unknown: {hla_before}\n")
            f.write(f"  优化后 Unknown: {hla_after}\n")
            f.write(f"  改善: {hla_before - hla_after} 个数据集\n")

            # 疾病类型改进
            disease_before = before_stats.get('disease_unknown', 0)
            disease_after = after_stats.get('disease_unknown', 0)
            f.write(f"\n疾病类型:\n")
            f.write(f"  优化前 Unknown: {disease_before}\n")
            f.write(f"  优化后 Unknown: {disease_after}\n")
            f.write(f"  改善: {disease_before - disease_after} 个数据集\n")

            # 样本类型改进
            sample_before = before_stats.get('sample_unknown', 0)
            sample_after = after_stats.get('sample_unknown', 0)
            f.write(f"\n样本类型:\n")
            f.write(f"  优化前 Unknown: {sample_before}\n")
            f.write(f"  优化后 Unknown: {sample_after}\n")
            f.write(f"  改善: {sample_before - sample_after} 个数据集\n")

            f.write("\n三、详细更改记录\n")
            f.write("-"*70 + "\n\n")

            for item in comparison_report:
                f.write(f"{item['dataset_id']}:\n")
                for change in item['changes']:
                    f.write(f"  • {change}\n")
                f.write("\n")

            f.write("四、数据质量提升\n")
            f.write("-"*70 + "\n")
            total_before = sum([before_stats.get('hla_unknown', 0),
                               before_stats.get('disease_unknown', 0),
                               before_stats.get('sample_unknown', 0)])
            total_after = sum([after_stats.get('hla_unknown', 0),
                              after_stats.get('disease_unknown', 0),
                              after_stats.get('sample_unknown', 0)])
            f.write(f"\n总Unknown字段数:\n")
            f.write(f"  优化前: {total_before}\n")
            f.write(f"  优化后: {total_after}\n")
            f.write(f"  改善: {total_before - total_after} 个字段\n")
            f.write(f"  改善率: {((total_before - total_after) / total_before * 100):.1f}%\n")

        print(f"✓ Enrichment report saved to: {report_file}")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("SysteMHC Data Enrichment Tool")
    print("="*70 + "\n")

    # 读取我们的数据
    input_file = DATA_PROCESSED_DIR / "all_metadata_crosschecked.csv"
    if not input_file.exists():
        print(f"✗ Error: {input_file} not found!")
        return

    print(f"Loading data from: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df)} datasets\n")

    # 收集优化前统计
    before_stats = {
        'hla_unknown': len(df[df['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])]),
        'disease_unknown': len(df[df['disease_type'] == 'Unknown']),
        'sample_unknown': len(df[df['sample_type'] == 'Unknown'])
    }

    # 找出需要补充的数据集（在SysteMHC中且有Unknown字段）
    candidates = df[
        (df['in_systemhc'] == True) &
        (
            (df['disease_type'] == 'Unknown') |
            (df['sample_type'] == 'Unknown') |
            (df['hla_type'].isin(['Unknown', 'HLA (需人工确认)']))
        )
    ]

    print(f"Found {len(candidates)} datasets to enrich from SysteMHC")
    print(f"  Disease Unknown: {len(candidates[candidates['disease_type'] == 'Unknown'])}")
    print(f"  Sample Unknown: {len(candidates[candidates['sample_type'] == 'Unknown'])}")
    print(f"  HLA Unknown: {len(candidates[candidates['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])])}\n")

    # 初始化enricher
    enricher = SysteMHCEnricher()

    # 批量获取SysteMHC数据
    dataset_ids = candidates['dataset_id'].tolist()
    print(f"Starting to fetch data from SysteMHC...")
    print(f"Note: This may take a while ({len(dataset_ids)} datasets × ~2 seconds/dataset)\n")

    systemhc_data = enricher.batch_fetch_datasets(dataset_ids)

    print(f"\n✓ Successfully fetched data for {len(systemhc_data)} datasets")

    if not systemhc_data:
        print("\n⚠ Warning: No data was extracted from SysteMHC")
        print("This may be because:")
        print("  1. The website requires JavaScript rendering")
        print("  2. The page structure has changed")
        print("  3. Network issues")
        print("\nRecommendation: Manual review may be required")
        return

    # 比较和补充数据
    df_updated, comparison_report = enricher.compare_and_supplement(df, systemhc_data)

    # 收集优化后统计
    after_stats = {
        'hla_unknown': len(df_updated[df_updated['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])]),
        'disease_unknown': len(df_updated[df_updated['disease_type'] == 'Unknown']),
        'sample_unknown': len(df_updated[df_updated['sample_type'] == 'Unknown'])
    }

    # 生成报告
    enricher.generate_comparison_report(comparison_report, before_stats, after_stats)

    # 保存更新后的数据
    output_file = DATA_PROCESSED_DIR / "all_metadata_enriched.csv"
    df_updated.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ Saved enriched data to: {output_file}")

    # 显示改进摘要
    print("\n" + "="*70)
    print("Enrichment Summary")
    print("="*70)
    print(f"\nHLA Type:")
    print(f"  Before: {before_stats['hla_unknown']} Unknown")
    print(f"  After: {after_stats['hla_unknown']} Unknown")
    print(f"  Improved: {before_stats['hla_unknown'] - after_stats['hla_unknown']} datasets")

    print(f"\nDisease Type:")
    print(f"  Before: {before_stats['disease_unknown']} Unknown")
    print(f"  After: {after_stats['disease_unknown']} Unknown")
    print(f"  Improved: {before_stats['disease_unknown'] - after_stats['disease_unknown']} datasets")

    print(f"\nSample Type:")
    print(f"  Before: {before_stats['sample_unknown']} Unknown")
    print(f"  After: {after_stats['sample_unknown']} Unknown")
    print(f"  Improved: {before_stats['sample_unknown'] - after_stats['sample_unknown']} datasets")

    print("\nNext step: Run generate_excel.py to update the Excel report")
    print()


if __name__ == "__main__":
    main()
