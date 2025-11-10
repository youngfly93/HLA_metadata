#!/usr/bin/env python3
"""
从标题和描述中智能推断缺失的疾病类型
"""

import pandas as pd
import re
from pathlib import Path
from typing import Optional

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


class DiseaseInferencer:
    """疾病类型推断器"""

    def __init__(self):
        # 疾病关键词字典（按优先级排序）
        self.disease_patterns = {
            # 癌症类型
            'Melanoma': [r'\bmelanoma\b', r'\bmelanomat\w*\b'],
            'Breast cancer': [r'\bbreast cancer\b', r'\bbreast carcinoma\b', r'\bbreast tumor\b'],
            'Lung cancer': [r'\blung cancer\b', r'\blung carcinoma\b', r'\blung tumor\b', r'\bNSCLC\b', r'\bSCLC\b'],
            'Colon cancer': [r'\bcolon cancer\b', r'\bcolorectal\b', r'\bcolon carcinoma\b'],
            'Ovarian cancer': [r'\bovarian cancer\b', r'\bovarian carcinoma\b', r'\bovary cancer\b'],
            'Prostate cancer': [r'\bprostate cancer\b', r'\bprostate carcinoma\b'],
            'Pancreatic cancer': [r'\bpancreatic cancer\b', r'\bpancreatic carcinoma\b'],
            'Glioblastoma': [r'\bglioblastoma\b', r'\bGBM\b', r'\bbrain tumor\b'],
            'Leukemia': [r'\bleukemia\b', r'\bleukaemia\b', r'\bAML\b', r'\bCML\b', r'\bALL\b', r'\bCLL\b'],
            'Lymphoma': [r'\blymphoma\b'],
            'Hepatocellular carcinoma': [r'\bhepatocellular carcinoma\b', r'\bHCC\b', r'\bliver cancer\b'],

            # 感染性疾病
            'COVID-19': [r'\bCOVID\b', r'\bSARS-CoV-2\b', r'\bcoronavirus\b'],
            'Influenza': [r'\binfluenza\b', r'\bflu\b'],
            'Tuberculosis': [r'\btuberculosis\b', r'\bTB\b', r'\bMycobacterium tuberculosis\b'],
            'HIV': [r'\bHIV\b', r'\bhuman immunodeficiency virus\b', r'\bAIDS\b'],
            'Hepatitis': [r'\bhepatitis\b', r'\bHBV\b', r'\bHCV\b'],

            # 神经退行性疾病
            'Alzheimer disease': [r'\bAlzheimer\b', r'\bAD\b'],
            'Parkinson disease': [r'\bParkinson\b', r'\bPD\b'],
            'Multiple sclerosis': [r'\bmultiple sclerosis\b', r'\bMS\b'],

            # 自身免疫性疾病
            'Rheumatoid arthritis': [r'\brheumatoid arthritis\b', r'\bRA\b'],
            'Lupus': [r'\blupus\b', r'\bSLE\b'],
            'Diabetes': [r'\bdiabetes\b', r'\bT1D\b', r'\bT2D\b'],

            # 其他疾病
            "Behçet's disease": [r"\bBehçet\b", r"\bBehcet\b"],
            'Ankylosing spondylitis': [r'\bankylosing spondylitis\b'],
            'Sarcoidosis': [r'\bsarcoidosis\b'],
        }

        # 健康/对照关键词
        self.healthy_patterns = [
            r'\bhealthy\b', r'\bnormal\b', r'\bcontrol\b', r'\bhealthy control\b',
            r'\bhealthy donor\b', r'\bnon-disease\b', r'\bdisease-free\b'
        ]

        # 方法学研究关键词（不涉及特定疾病）
        self.method_patterns = [
            r'\bmethodology\b', r'\bmethod development\b', r'\bpipeline\b',
            r'\balgorithm\b', r'\bcomputational\b', r'\bin silico\b',
            r'\bprediction\b', r'\bbenchmark\b', r'\bvalidation\b'
        ]

    def infer_disease_from_text(self, text: str) -> Optional[str]:
        """
        从文本中推断疾病类型

        Args:
            text: 标题或描述文本

        Returns:
            推断的疾病名称，如果无法推断返回None
        """
        if not text or pd.isna(text):
            return None

        text_lower = str(text).lower()

        # 首先检查是否是健康对照
        for pattern in self.healthy_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return 'Healthy/Control'

        # 检查是否是方法学研究（无特定疾病）
        method_count = sum(1 for p in self.method_patterns
                          if re.search(p, text_lower, re.IGNORECASE))
        if method_count >= 2:  # 至少匹配2个方法学关键词
            return 'Method development (no specific disease)'

        # 搜索疾病关键词
        matched_diseases = []
        for disease_name, patterns in self.disease_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matched_diseases.append(disease_name)
                    break

        if matched_diseases:
            # 如果匹配多个，用分号连接
            return '; '.join(matched_diseases[:3])  # 最多返回3个

        return None

    def infer_missing_diseases(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为Unknown的疾病类型进行智能推断

        Args:
            df: 输入DataFrame

        Returns:
            推断后的DataFrame
        """
        print("\n" + "="*70)
        print("智能推断缺失的疾病类型")
        print("="*70 + "\n")

        # 统计推断前的Unknown数量
        before_unknown = (df['disease_type'] == 'Unknown').sum()
        print(f"推断前Unknown数量: {before_unknown}")

        # 创建新列保存推断结果
        df['disease_inferred'] = False
        df['inference_source'] = ''

        inferred_count = 0

        # 遍历Unknown的数据集
        for idx, row in df[df['disease_type'] == 'Unknown'].iterrows():
            # 尝试从标题推断
            title_inference = self.infer_disease_from_text(row.get('title', ''))

            if title_inference:
                df.at[idx, 'disease_type'] = title_inference
                df.at[idx, 'disease_inferred'] = True
                df.at[idx, 'inference_source'] = 'title'
                inferred_count += 1
                continue

            # 尝试从描述推断
            desc_inference = self.infer_disease_from_text(row.get('description', ''))

            if desc_inference:
                df.at[idx, 'disease_type'] = desc_inference
                df.at[idx, 'disease_inferred'] = True
                df.at[idx, 'inference_source'] = 'description'
                inferred_count += 1
                continue

            # 尝试从组织信息推断
            tissues = str(row.get('tissues', ''))
            if tissues and tissues != 'nan':
                tissue_inference = self._infer_from_tissue(tissues)
                if tissue_inference:
                    df.at[idx, 'disease_type'] = tissue_inference
                    df.at[idx, 'disease_inferred'] = True
                    df.at[idx, 'inference_source'] = 'tissue'
                    inferred_count += 1

        # 统计推断后的Unknown数量
        after_unknown = (df['disease_type'] == 'Unknown').sum()

        # 重新分类疾病类别
        df = self._reclassify_disease_categories(df)

        print(f"推断后Unknown数量: {after_unknown}")
        print(f"成功推断: {inferred_count} 个")
        print(f"推断成功率: {inferred_count/before_unknown*100:.1f}%")

        # 显示推断示例
        self._show_inference_examples(df)

        return df

    def _infer_from_tissue(self, tissues: str) -> Optional[str]:
        """从组织信息推断疾病"""
        tissues_lower = tissues.lower()

        tissue_disease_map = {
            'tumor': 'Cancer (tumor tissue)',
            'cancer': 'Cancer',
            'carcinoma': 'Carcinoma',
            'melanoma': 'Melanoma',
            'leukemia': 'Leukemia',
        }

        for keyword, disease in tissue_disease_map.items():
            if keyword in tissues_lower:
                return disease

        return None

    def _reclassify_disease_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """重新分类疾病类别"""
        cancer_keywords = [
            'cancer', 'carcinoma', 'melanoma', 'leukemia', 'lymphoma',
            'sarcoma', 'glioblastoma', 'neuroblastoma', 'adenocarcinoma',
            'neoplasm', 'tumor', 'tumour'
        ]

        neurodegenerative_keywords = [
            'alzheimer', 'parkinson', 'dementia', 'multiple sclerosis'
        ]

        infectious_keywords = [
            'covid', 'influenza', 'hiv', 'tuberculosis', 'hepatitis'
        ]

        autoimmune_keywords = [
            'rheumatoid', 'lupus', 'arthritis', 'diabetes'
        ]

        method_keywords = ['method development']

        def classify_category(row):
            disease = str(row.get('disease_type', '')).lower()

            if disease in ['unknown', 'nan', '']:
                return 'Unknown'

            if 'healthy' in disease or 'control' in disease:
                return 'Healthy'

            if any(keyword in disease for keyword in method_keywords):
                return 'Method Study'

            if any(keyword in disease for keyword in cancer_keywords):
                return 'Cancer'

            if any(keyword in disease for keyword in neurodegenerative_keywords):
                return 'Neurodegenerative'

            if any(keyword in disease for keyword in infectious_keywords):
                return 'Infectious Disease'

            if any(keyword in disease for keyword in autoimmune_keywords):
                return 'Autoimmune Disease'

            return 'Other'

        df['disease_category'] = df.apply(classify_category, axis=1)

        return df

    def _show_inference_examples(self, df: pd.DataFrame):
        """显示推断示例"""
        inferred_df = df[df['disease_inferred'] == True]

        if len(inferred_df) == 0:
            return

        print("\n" + "="*70)
        print("推断示例（前10个）")
        print("="*70 + "\n")

        for i, (idx, row) in enumerate(inferred_df.head(10).iterrows(), 1):
            print(f"{i}. {row['dataset_id']} - {row['disease_type']}")
            print(f"   来源: {row['inference_source']}")
            if row['inference_source'] == 'title':
                print(f"   标题: {row['title'][:60]}...")
            elif row['inference_source'] == 'description':
                print(f"   描述: {str(row['description'])[:60]}...")
            print()

    def save_results(self, df: pd.DataFrame):
        """保存结果"""
        output_file = DATA_PROCESSED_DIR / "all_metadata_inferred.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✓ Saved to: {output_file}")

        # 生成推断报告
        self._generate_inference_report(df)

    def _generate_inference_report(self, df: pd.DataFrame):
        """生成推断报告"""
        report_file = PROJECT_ROOT / "data" / "validation" / "disease_inference_report.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("疾病类型智能推断报告\n")
            f.write("="*70 + "\n\n")

            # 统计
            total = len(df)
            inferred = (df['disease_inferred'] == True).sum()
            unknown = (df['disease_type'] == 'Unknown').sum()

            f.write(f"总数据集: {total}\n")
            f.write(f"成功推断: {inferred}\n")
            f.write(f"仍为Unknown: {unknown}\n")
            f.write(f"推断覆盖率: {inferred/(total-unknown+inferred)*100:.1f}%\n\n")

            # 推断来源统计
            f.write("推断来源分布:\n")
            source_counts = df[df['disease_inferred'] == True]['inference_source'].value_counts()
            for source, count in source_counts.items():
                f.write(f"  {source}: {count}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("疾病类型新分布:\n")
            f.write("="*70 + "\n\n")

            disease_counts = df['disease_type'].value_counts().head(20)
            for disease, count in disease_counts.items():
                pct = count / total * 100
                f.write(f"{disease:40s}: {count:3d} ({pct:5.1f}%)\n")

        print(f"✓ Inference report saved to: {report_file}")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("疾病类型智能推断工具")
    print("="*70 + "\n")

    # 读取清理后的数据
    input_file = DATA_PROCESSED_DIR / "all_metadata_cleaned.csv"

    if not input_file.exists():
        print(f"✗ Error: {input_file} not found!")
        return

    print(f"Loading data from: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df)} datasets\n")

    # 执行推断
    inferencer = DiseaseInferencer()
    df_inferred = inferencer.infer_missing_diseases(df)

    # 保存结果
    inferencer.save_results(df_inferred)

    print("\n✓ Disease inference complete!")
    print("\nNext step:")
    print("  Run generate_excel.py to create updated Excel report")
    print("\n")


if __name__ == "__main__":
    main()
