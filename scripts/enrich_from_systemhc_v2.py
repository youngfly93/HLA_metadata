#!/usr/bin/env python3
"""
从SysteMHC自动提取数据并补充我们的元数据 (使用JavaScript渲染)
"""

import pandas as pd
import re
import time
from pathlib import Path
from typing import Dict, Optional, List
from requests_html import HTMLSession, AsyncHTMLSession
import asyncio

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"

class SysteMHCEnricherV2:
    """SysteMHC数据补充器 (支持JavaScript渲染)"""

    def __init__(self):
        self.base_url = "https://systemhc.sjtu.edu.cn"
        self.session = HTMLSession()

    async def fetch_dataset_with_js(self, dataset_id: str) -> Optional[Dict]:
        """
        使用JavaScript渲染获取数据集信息
        """
        try:
            url = f"{self.base_url}/dataset/?dataset_id={dataset_id}"
            print(f"  Fetching (with JS rendering): {url}")

            # 创建异步session
            asession = AsyncHTMLSession()
            r = await asession.get(url)

            # 等待JavaScript渲染
            print(f"    Rendering JavaScript...")
            await r.html.arender(timeout=30, sleep=3)

            # 解析渲染后的内容
            data = self._parse_rendered_page(r.html, dataset_id)

            await asession.close()

            if data and (data.get('hla_alleles') or data.get('tissues') or
                        data.get('diseases') or data.get('cell_types')):
                return data
            else:
                print(f"    ⚠ No useful data extracted after rendering")
                return None

        except Exception as e:
            print(f"    ✗ Error: {e}")
            return None

    def _parse_rendered_page(self, html, dataset_id: str) -> Dict:
        """
        从渲染后的页面提取信息
        """
        data = {
            'dataset_id': dataset_id,
            'hla_alleles': [],
            'tissues': [],
            'diseases': [],
            'cell_types': [],
            'organisms': []
        }

        # 获取页面文本
        page_text = html.text

        # 方法1: 查找表格（使用pyquery选择器）
        try:
            # 查找dataset表格
            tables = html.find('table')
            for table in tables:
                # 查找所有行
                rows = table.find('tr')
                for row in rows[1:]:  # 跳过表头
                    cells = row.find('td')
                    if len(cells) >= 3:
                        # 提取Organism
                        if len(cells) > 2:
                            organism = cells[2].text.strip()
                            if organism and organism not in data['organisms']:
                                data['organisms'].append(organism)

                        # 提取TissueType
                        if len(cells) > 3:
                            tissue = cells[3].text.strip()
                            if tissue and tissue not in ['', '-', 'N/A']:
                                if tissue not in data['tissues']:
                                    data['tissues'].append(tissue)

                        # 提取CellType
                        if len(cells) > 4:
                            cell_type = cells[4].text.strip()
                            if cell_type and cell_type not in ['', '-', 'N/A']:
                                if cell_type not in data['cell_types']:
                                    data['cell_types'].append(cell_type)

                        # 提取MHCAllele
                        if len(cells) > 5:
                            mhc = cells[5].text.strip()
                            if mhc and mhc not in ['', '-', 'N/A']:
                                # 分割多个等位基因
                                alleles = re.split(r'[,;/\s]+', mhc)
                                for allele in alleles:
                                    allele = allele.strip()
                                    if allele and allele not in data['hla_alleles']:
                                        data['hla_alleles'].append(allele)
        except Exception as e:
            print(f"    ⚠ Table parsing error: {e}")

        # 方法2: 使用正则表达式从整个页面提取HLA信息
        hla_patterns = [
            r'HLA-[A-Z]\*\d+:\d+(?::\d+)?(?::\d+)?',  # HLA-A*02:01
            r'HLA-[A-Z][A-Z]\*\d+:\d+',               # HLA-DR*01:01
            r'HLA-[A-Z][A-Z][A-Z]\d+\*\d+:\d+',       # HLA-DRB1*01:01
        ]

        for pattern in hla_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                if match not in data['hla_alleles']:
                    data['hla_alleles'].append(match)

        # 方法3: 从页面文本提取疾病信息
        self._extract_diseases_from_text(page_text, data['diseases'])

        # 方法4: 查找特定的div或section
        try:
            # 查找可能包含元数据的区域
            info_sections = html.find('.info, .metadata, .details, [class*="info"]')
            for section in info_sections:
                text = section.text
                # 提取疾病
                self._extract_diseases_from_text(text, data['diseases'])

                # 提取组织类型
                tissue_keywords = ['tissue', 'organ', 'sample']
                for keyword in tissue_keywords:
                    if keyword in text.lower():
                        # 尝试提取相关信息
                        lines = text.split('\n')
                        for line in lines:
                            if keyword in line.lower():
                                # 简单提取
                                parts = line.split(':')
                                if len(parts) > 1:
                                    value = parts[1].strip()
                                    if value and value not in data['tissues']:
                                        data['tissues'].append(value)
        except Exception as e:
            print(f"    ⚠ Section parsing error: {e}")

        return data

    def _extract_diseases_from_text(self, text: str, diseases_list: List):
        """从文本中提取疾病关键词"""
        disease_patterns = {
            'Melanoma': r'\bmelanoma\b',
            'Breast cancer': r'\bbreast cancer\b',
            'Lung cancer': r'\blung cancer\b',
            'Colon cancer': r'\bcolon cancer\b',
            'Leukemia': r'\bleukemia\b',
            'Lymphoma': r'\blymphoma\b',
            'COVID-19': r'\b(?:COVID-19|SARS-CoV-2|coronavirus)\b',
            'Influenza': r'\binfluenza\b',
            'Tuberculosis': r'\btuberculosis\b',
            'HIV': r'\bHIV\b',
            'Diabetes': r'\bdiabetes\b',
            'Multiple sclerosis': r'\bmultiple sclerosis\b',
            'Alzheimer': r'\bAlzheimer',
            'Parkinson': r'\bParkinson',
        }

        text_lower = text.lower()
        for disease, pattern in disease_patterns.items():
            if re.search(pattern, text_lower):
                if disease not in diseases_list:
                    diseases_list.append(disease)

    async def batch_fetch_async(self, dataset_ids: List[str]) -> Dict[str, Dict]:
        """
        批量异步获取数据集信息
        """
        results = {}
        total = len(dataset_ids)

        for i, dataset_id in enumerate(dataset_ids, 1):
            print(f"\n[{i}/{total}] Processing {dataset_id}")

            data = await self.fetch_dataset_with_js(dataset_id)

            if data:
                results[dataset_id] = data
                print(f"    ✓ Extracted:")
                if data.get('hla_alleles'):
                    print(f"      HLA: {len(data['hla_alleles'])} alleles")
                if data.get('tissues'):
                    print(f"      Tissues: {', '.join(data['tissues'][:3])}")
                if data.get('cell_types'):
                    print(f"      Cell types: {', '.join(data['cell_types'][:3])}")
                if data.get('diseases'):
                    print(f"      Diseases: {', '.join(data['diseases'])}")

            # 延迟，避免过载
            if i < total:
                await asyncio.sleep(3)

        return results

    def compare_and_supplement(self, our_df: pd.DataFrame,
                               systemhc_data: Dict[str, Dict]) -> tuple:
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

            # 1. 补充HLA类型
            if row['hla_type'] in ['Unknown', 'HLA (需人工确认)']:
                if systemhc_info.get('hla_alleles'):
                    alleles = systemhc_info['hla_alleles']
                    has_class_i = any(re.search(r'HLA-[ABC]', a, re.I) for a in alleles)
                    has_class_ii = any(re.search(r'HLA-D[RQPM]', a, re.I) for a in alleles)

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

            # 2. 补充疾病类型
            if row['disease_type'] == 'Unknown':
                if systemhc_info.get('diseases'):
                    new_disease = '; '.join(systemhc_info['diseases'])
                    changes.append(f"Disease: Unknown → {new_disease}")
                    our_df.at[idx, 'disease_type'] = new_disease
                    our_df.at[idx, 'disease_inferred'] = True
                    our_df.at[idx, 'inference_source'] = 'SysteMHC'

            # 3. 补充样本类型
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

            # 4. 补充HLA等位基因
            if systemhc_info.get('hla_alleles'):
                alleles_str = '; '.join(systemhc_info['hla_alleles'][:15])
                current = row.get('hla_alleles')
                if pd.isna(current) or not current or current == '':
                    our_df.at[idx, 'hla_alleles'] = alleles_str
                    changes.append(f"Added HLA alleles ({len(systemhc_info['hla_alleles'])})")

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
            f.write("SysteMHC数据补充报告 (JavaScript渲染版)\n")
            f.write("="*70 + "\n\n")

            f.write("一、数据补充概况\n")
            f.write("-"*70 + "\n")
            f.write(f"总补充数据集数: {len(comparison_report)}\n\n")

            f.write("二、字段改进统计\n")
            f.write("-"*70 + "\n")

            # HLA类型
            hla_before = before_stats.get('hla_unknown', 0)
            hla_after = after_stats.get('hla_unknown', 0)
            f.write(f"\nHLA类型:\n")
            f.write(f"  优化前 Unknown: {hla_before}\n")
            f.write(f"  优化后 Unknown: {hla_after}\n")
            f.write(f"  改善: {hla_before - hla_after} 个数据集\n")

            # 疾病类型
            disease_before = before_stats.get('disease_unknown', 0)
            disease_after = after_stats.get('disease_unknown', 0)
            f.write(f"\n疾病类型:\n")
            f.write(f"  优化前 Unknown: {disease_before}\n")
            f.write(f"  优化后 Unknown: {disease_after}\n")
            f.write(f"  改善: {disease_before - disease_after} 个数据集\n")

            # 样本类型
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

            if comparison_report:
                total_before = sum([before_stats.get('hla_unknown', 0),
                                   before_stats.get('disease_unknown', 0),
                                   before_stats.get('sample_unknown', 0)])
                total_after = sum([after_stats.get('hla_unknown', 0),
                                  after_stats.get('disease_unknown', 0),
                                  after_stats.get('sample_unknown', 0)])

                f.write("四、数据质量提升\n")
                f.write("-"*70 + "\n")
                f.write(f"\n总Unknown字段数:\n")
                f.write(f"  优化前: {total_before}\n")
                f.write(f"  优化后: {total_after}\n")
                f.write(f"  改善: {total_before - total_after} 个字段\n")
                if total_before > 0:
                    f.write(f"  改善率: {((total_before - total_after) / total_before * 100):.1f}%\n")

        print(f"✓ Enrichment report saved to: {report_file}")


async def main_async():
    """异步主函数"""
    print("\n" + "="*70)
    print("SysteMHC Data Enrichment Tool (JavaScript Rendering)")
    print("="*70 + "\n")

    # 读取数据
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

    # 找出需要补充的数据集
    candidates = df[
        (df['in_systemhc'] == True) &
        (
            (df['disease_type'] == 'Unknown') |
            (df['sample_type'] == 'Unknown') |
            (df['hla_type'].isin(['Unknown', 'HLA (需人工确认)']))
        )
    ]

    print(f"Found {len(candidates)} datasets to enrich")
    print(f"  Disease Unknown: {len(candidates[candidates['disease_type'] == 'Unknown'])}")
    print(f"  Sample Unknown: {len(candidates[candidates['sample_type'] == 'Unknown'])}")
    print(f"  HLA Unknown: {len(candidates[candidates['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])])}\n")

    # 限制数量以测试（处理前5个）
    test_mode = True
    if test_mode:
        dataset_ids = candidates['dataset_id'].tolist()[:5]
        print(f"⚠ TEST MODE: Processing first 5 datasets only")
        print(f"  To process all {len(candidates)} datasets, set test_mode=False\n")
    else:
        dataset_ids = candidates['dataset_id'].tolist()

    # 初始化enricher
    enricher = SysteMHCEnricherV2()

    print(f"Starting JavaScript-based data extraction...")
    print(f"Note: First run will download Chromium (~150MB)")
    print(f"This may take ~10-15 seconds per dataset\n")

    # 批量获取数据
    systemhc_data = await enricher.batch_fetch_async(dataset_ids)

    print(f"\n✓ Successfully extracted data for {len(systemhc_data)} datasets")

    if not systemhc_data:
        print("\n⚠ Warning: No data was extracted")
        print("Possible reasons:")
        print("  1. Network issues")
        print("  2. JavaScript rendering timeout")
        print("  3. Website structure changed")
        return

    # 比较和补充
    df_updated, comparison_report = enricher.compare_and_supplement(df, systemhc_data)

    # 收集优化后统计
    after_stats = {
        'hla_unknown': len(df_updated[df_updated['hla_type'].isin(['Unknown', 'HLA (需人工确认)'])]),
        'disease_unknown': len(df_updated[df_updated['disease_type'] == 'Unknown']),
        'sample_unknown': len(df_updated[df_updated['sample_type'] == 'Unknown'])
    }

    # 生成报告
    enricher.generate_comparison_report(comparison_report, before_stats, after_stats)

    # 保存结果
    output_file = DATA_PROCESSED_DIR / "all_metadata_enriched.csv"
    df_updated.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ Saved to: {output_file}")

    # 摘要
    print("\n" + "="*70)
    print("Enrichment Summary")
    print("="*70)
    print(f"\nHLA Type: {before_stats['hla_unknown']} → {after_stats['hla_unknown']} Unknown")
    print(f"Disease Type: {before_stats['disease_unknown']} → {after_stats['disease_unknown']} Unknown")
    print(f"Sample Type: {before_stats['sample_unknown']} → {after_stats['sample_unknown']} Unknown")
    print("\nNext: Run generate_excel.py to update Excel report\n")


def main():
    """主函数包装器"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
