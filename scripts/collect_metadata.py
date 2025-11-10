#!/usr/bin/env python3
"""
HLA元数据收集主脚本
从ProteomeXchange (PXD)、MassIVE (MSV)、jPOST (JPST)、PeptideAtlas (PASS)收集元数据
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PRIDE_API_DIR = DATA_RAW_DIR / "pride_api_responses"
SDRF_DIR = DATA_RAW_DIR / "sdrf_files"
MANUAL_DIR = DATA_RAW_DIR / "manual_extracts"

# 创建必要目录
for dir_path in [PRIDE_API_DIR, SDRF_DIR, MANUAL_DIR, DATA_PROCESSED_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


class ProteomicsMetadataCollector:
    """蛋白质组学元数据收集器"""

    def __init__(self):
        self.pride_base_url = "https://www.ebi.ac.uk/pride/ws/archive/v2"
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})

    def read_dataset_list(self, file_path: str) -> List[str]:
        """读取数据集ID列表"""
        datasets = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                dataset_id = line.strip()
                if dataset_id and len(dataset_id) > 3:
                    datasets.append(dataset_id)
        return datasets

    def get_pride_metadata(self, pxd_id: str, retry: int = 3) -> Optional[Dict]:
        """
        从PRIDE API获取单个数据集的元数据

        Args:
            pxd_id: ProteomeXchange数据集ID (如 PXD012348)
            retry: 重试次数

        Returns:
            元数据字典，如果失败返回None
        """
        url = f"{self.pride_base_url}/projects/{pxd_id}"

        for attempt in range(retry):
            try:
                print(f"  Fetching {pxd_id} (attempt {attempt + 1}/{retry})...")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                data = response.json()

                # 保存原始API响应
                output_file = PRIDE_API_DIR / f"{pxd_id}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"  ✓ Successfully fetched {pxd_id}")
                return data

            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    print(f"  ✗ {pxd_id} not found (404)")
                    return None
                print(f"  ! HTTP error for {pxd_id}: {e}")
            except requests.exceptions.RequestException as e:
                print(f"  ! Request error for {pxd_id}: {e}")
            except json.JSONDecodeError as e:
                print(f"  ! JSON decode error for {pxd_id}: {e}")

            if attempt < retry - 1:
                time.sleep(2 ** attempt)  # 指数退避

        print(f"  ✗ Failed to fetch {pxd_id} after {retry} attempts")
        return None

    def extract_metadata_fields(self, pxd_id: str, data: Dict) -> Dict:
        """
        从PRIDE API响应中提取关键元数据字段

        Args:
            pxd_id: 数据集ID
            data: PRIDE API响应数据

        Returns:
            提取的元数据字典
        """
        metadata = {
            'dataset_id': pxd_id,
            'repository': 'PRIDE',
            'title': data.get('title', ''),
            'description': data.get('projectDescription', ''),

            # 生物学信息
            'organisms': self._extract_list(data.get('organisms', []), 'name'),
            'diseases': self._extract_list(data.get('diseases', [])),
            'tissues': self._extract_list(data.get('tissues', [])),
            'cell_types': self._extract_list(data.get('cellTypes', [])),

            # 技术信息
            'instruments': self._extract_list(data.get('instruments', []), 'name'),
            'ptms': self._extract_list(data.get('ptmList', []), 'name'),
            'quantification_methods': self._extract_list(data.get('quantificationMethods', []), 'name'),

            # 项目标签和关键词
            'project_tags': self._extract_list(data.get('projectTags', [])),
            'keywords': self._extract_list(data.get('keywords', [])),

            # 实验方案
            'sample_protocol': data.get('sampleProcessingProtocol', ''),
            'data_protocol': data.get('dataProcessingProtocol', ''),

            # 日期和出版
            'publication_date': data.get('publicationDate', ''),
            'submission_date': data.get('submissionDate', ''),
            'submission_type': data.get('submissionType', ''),

            # 引用
            'pubmed_ids': self._extract_pubmed_ids(data.get('references', [])),
            'dois': self._extract_dois(data.get('references', [])),

            # 链接
            'pride_url': f"https://www.ebi.ac.uk/pride/archive/projects/{pxd_id}",
        }

        # 检查是否有SDRF文件
        metadata['has_sdrf'] = self._check_sdrf_exists(pxd_id)

        return metadata

    def _extract_list(self, items: List, field: Optional[str] = None) -> str:
        """从列表中提取字段并拼接为字符串"""
        if not items:
            return ''
        if field:
            return '; '.join(str(item.get(field, '')) for item in items if item.get(field))
        return '; '.join(str(item) for item in items if item)

    def _extract_pubmed_ids(self, references: List[Dict]) -> str:
        """提取PubMed ID"""
        pubmed_ids = []
        for ref in references:
            if ref.get('pubmedId'):
                pubmed_ids.append(str(ref['pubmedId']))
        return '; '.join(pubmed_ids)

    def _extract_dois(self, references: List[Dict]) -> str:
        """提取DOI"""
        dois = []
        for ref in references:
            if ref.get('doi'):
                dois.append(ref['doi'])
        return '; '.join(dois)

    def _check_sdrf_exists(self, pxd_id: str) -> bool:
        """检查SDRF文件是否存在"""
        # SDRF文件通常命名为 {PXD}.sdrf.tsv
        sdrf_url = f"https://www.ebi.ac.uk/pride/data/archive/{pxd_id}/{pxd_id}.sdrf.tsv"
        try:
            response = self.session.head(sdrf_url, timeout=10)
            return response.status_code == 200
        except:
            return False

    def download_sdrf(self, pxd_id: str) -> Optional[str]:
        """
        下载SDRF文件

        Args:
            pxd_id: 数据集ID

        Returns:
            SDRF文件路径，如果下载失败返回None
        """
        sdrf_url = f"https://www.ebi.ac.uk/pride/data/archive/{pxd_id}/{pxd_id}.sdrf.tsv"
        output_file = SDRF_DIR / f"{pxd_id}.sdrf.tsv"

        # 如果文件已存在，跳过
        if output_file.exists():
            print(f"  ↷ SDRF already exists for {pxd_id}")
            return str(output_file)

        try:
            print(f"  Downloading SDRF for {pxd_id}...")
            response = self.session.get(sdrf_url, timeout=60)
            response.raise_for_status()

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"  ✓ SDRF downloaded for {pxd_id}")
            return str(output_file)

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Failed to download SDRF for {pxd_id}: {e}")
            return None

    def collect_pxd_datasets(self, dataset_ids: List[str]) -> pd.DataFrame:
        """
        批量收集PXD数据集的元数据

        Args:
            dataset_ids: PXD数据集ID列表

        Returns:
            包含所有元数据的DataFrame
        """
        pxd_datasets = [did for did in dataset_ids if did.startswith('PXD')]
        print(f"\n{'='*60}")
        print(f"Collecting metadata for {len(pxd_datasets)} PXD datasets")
        print(f"{'='*60}\n")

        all_metadata = []

        for i, pxd_id in enumerate(pxd_datasets, 1):
            print(f"[{i}/{len(pxd_datasets)}] Processing {pxd_id}")

            # 获取基础元数据
            raw_data = self.get_pride_metadata(pxd_id)

            if raw_data:
                metadata = self.extract_metadata_fields(pxd_id, raw_data)

                # 如果有SDRF文件，尝试下载
                if metadata.get('has_sdrf'):
                    sdrf_path = self.download_sdrf(pxd_id)
                    metadata['sdrf_file'] = sdrf_path if sdrf_path else ''
                else:
                    metadata['sdrf_file'] = ''

                all_metadata.append(metadata)
            else:
                # 记录失败的数据集
                all_metadata.append({
                    'dataset_id': pxd_id,
                    'repository': 'PRIDE',
                    'error': 'Failed to fetch metadata'
                })

            # 速率限制
            time.sleep(1)

        print(f"\n✓ Completed PXD collection: {len(all_metadata)} records\n")
        return pd.DataFrame(all_metadata)

    def collect_msv_datasets(self, dataset_ids: List[str]) -> pd.DataFrame:
        """
        收集MSV (MassIVE) 数据集的元数据
        使用ppx包（如果可用）或标记为需要手动处理

        Args:
            dataset_ids: 包含MSV数据集的ID列表

        Returns:
            包含MSV元数据的DataFrame
        """
        msv_datasets = [did for did in dataset_ids if did.startswith('MSV')]

        if not msv_datasets:
            return pd.DataFrame()

        print(f"\n{'='*60}")
        print(f"Collecting metadata for {len(msv_datasets)} MSV datasets")
        print(f"{'='*60}\n")

        # 尝试导入ppx
        try:
            import ppx
            use_ppx = True
            print("✓ ppx package found, will use for MSV datasets\n")
        except ImportError:
            use_ppx = False
            print("! ppx package not found, MSV datasets will be marked for manual processing\n")

        all_metadata = []

        for i, msv_id in enumerate(msv_datasets, 1):
            print(f"[{i}/{len(msv_datasets)}] Processing {msv_id}")

            if use_ppx:
                try:
                    proj = ppx.find_project(msv_id)
                    metadata = {
                        'dataset_id': msv_id,
                        'repository': 'MassIVE',
                        'title': getattr(proj, 'title', ''),
                        'description': getattr(proj, 'description', ''),
                        'organisms': ', '.join(getattr(proj, 'organisms', [])),
                        'instruments': ', '.join(getattr(proj, 'instruments', [])),
                        'modifications': ', '.join(getattr(proj, 'modifications', [])),
                        'url': proj.url,
                        'pride_url': f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task={msv_id}",
                    }
                    print(f"  ✓ Successfully processed {msv_id}")
                except Exception as e:
                    print(f"  ✗ Error processing {msv_id}: {e}")
                    metadata = {
                        'dataset_id': msv_id,
                        'repository': 'MassIVE',
                        'error': str(e),
                        'manual_review': True
                    }
            else:
                metadata = {
                    'dataset_id': msv_id,
                    'repository': 'MassIVE',
                    'manual_review': True,
                    'note': 'ppx package not installed - requires manual extraction',
                    'pride_url': f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task={msv_id}",
                }
                print(f"  → {msv_id} marked for manual review")

            all_metadata.append(metadata)
            time.sleep(1)

        print(f"\n✓ Completed MSV collection: {len(all_metadata)} records\n")
        return pd.DataFrame(all_metadata)

    def prepare_manual_datasets(self, dataset_ids: List[str]) -> pd.DataFrame:
        """
        为JPST和PASS数据集准备手动提取模板

        Args:
            dataset_ids: 数据集ID列表

        Returns:
            包含手动处理信息的DataFrame
        """
        manual_datasets = [
            did for did in dataset_ids
            if did.startswith('JPST') or did.startswith('PASS')
        ]

        if not manual_datasets:
            return pd.DataFrame()

        print(f"\n{'='*60}")
        print(f"Preparing {len(manual_datasets)} datasets for manual extraction")
        print(f"{'='*60}\n")

        all_metadata = []

        for dataset_id in manual_datasets:
            if dataset_id.startswith('JPST'):
                url = f"https://repository.jpostdb.org/entry/{dataset_id}"
                repository = 'jPOST'
            else:  # PASS
                url = f"http://www.peptideatlas.org/PASS/{dataset_id}"
                repository = 'PeptideAtlas'

            metadata = {
                'dataset_id': dataset_id,
                'repository': repository,
                'manual_review': True,
                'note': 'No public API - requires manual web extraction',
                'pride_url': url,
            }
            all_metadata.append(metadata)
            print(f"  → {dataset_id} prepared for manual extraction")
            print(f"     URL: {url}")

        print(f"\n✓ Prepared {len(all_metadata)} datasets for manual review\n")
        return pd.DataFrame(all_metadata)

    def save_results(self, df: pd.DataFrame, filename: str):
        """保存结果到CSV和JSON"""
        csv_path = DATA_PROCESSED_DIR / f"{filename}.csv"
        json_path = DATA_PROCESSED_DIR / f"{filename}.json"

        # 保存CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ Saved CSV to: {csv_path}")

        # 保存JSON
        df.to_json(json_path, orient='records', indent=2, force_ascii=False)
        print(f"✓ Saved JSON to: {json_path}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("HLA Metadata Collection Tool")
    print("="*60 + "\n")

    # 初始化收集器
    collector = ProteomicsMetadataCollector()

    # 读取数据集列表
    metadata_list_file = PROJECT_ROOT / "metadata_list"
    if not metadata_list_file.exists():
        print(f"✗ Error: metadata_list file not found at {metadata_list_file}")
        sys.exit(1)

    print(f"Reading dataset list from: {metadata_list_file}")
    dataset_ids = collector.read_dataset_list(metadata_list_file)
    print(f"✓ Found {len(dataset_ids)} datasets\n")

    # 统计数据集分布
    pxd_count = sum(1 for d in dataset_ids if d.startswith('PXD'))
    msv_count = sum(1 for d in dataset_ids if d.startswith('MSV'))
    jpst_count = sum(1 for d in dataset_ids if d.startswith('JPST'))
    pass_count = sum(1 for d in dataset_ids if d.startswith('PASS'))

    print("Dataset distribution:")
    print(f"  PXD (ProteomeXchange): {pxd_count}")
    print(f"  MSV (MassIVE): {msv_count}")
    print(f"  JPST (jPOST): {jpst_count}")
    print(f"  PASS (PeptideAtlas): {pass_count}")

    # 收集PXD数据集
    pxd_df = collector.collect_pxd_datasets(dataset_ids)
    collector.save_results(pxd_df, "pxd_metadata")

    # 收集MSV数据集
    msv_df = collector.collect_msv_datasets(dataset_ids)
    if not msv_df.empty:
        collector.save_results(msv_df, "msv_metadata")

    # 准备手动提取数据集
    manual_df = collector.prepare_manual_datasets(dataset_ids)
    if not manual_df.empty:
        collector.save_results(manual_df, "manual_datasets")

    # 合并所有结果
    all_dfs = [df for df in [pxd_df, msv_df, manual_df] if not df.empty]
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        collector.save_results(combined_df, "all_metadata_raw")

        print("\n" + "="*60)
        print("Collection Summary")
        print("="*60)
        print(f"Total datasets processed: {len(combined_df)}")
        print(f"  PXD datasets: {len(pxd_df)}")
        print(f"  MSV datasets: {len(msv_df)}")
        print(f"  Manual datasets (JPST/PASS): {len(manual_df)}")
        print(f"\nDatasets with SDRF files: {pxd_df['has_sdrf'].sum() if 'has_sdrf' in pxd_df else 0}")
        print(f"Datasets requiring manual review: {combined_df.get('manual_review', pd.Series([False])).sum()}")
        print("\n✓ Collection complete!")
        print(f"\nNext steps:")
        print(f"  1. Run parse_sdrf.py to extract detailed sample information")
        print(f"  2. Run classify_metadata.py to classify HLA types and sample types")
        print(f"  3. Run generate_excel.py to create the final report")

    print("\n")


if __name__ == "__main__":
    main()
