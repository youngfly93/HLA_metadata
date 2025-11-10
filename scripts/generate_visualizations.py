#!/usr/bin/env python3
"""
生成HLA元数据的精美可视化图表
包含多种图表类型：饼图、柱状图、热力图、时间序列等
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Set style: clean white background without grid
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['figure.facecolor'] = 'white'
sns.set_style("white")  # Clean white background, no grid
sns.set_palette("husl")

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
VIS_DIR = PROJECT_ROOT / "visualizations"
VIS_DIR.mkdir(exist_ok=True)

# 颜色方案
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'success': '#06A77D',
    'warning': '#F77F00',
    'danger': '#D62828',
    'info': '#4ECDC4',
    'purple': '#9B5DE5',
    'pink': '#F15BB5',
    'orange': '#FEE440',
    'teal': '#00BBF9',
}

HLA_COLORS = {
    'HLA I': '#2E86AB',
    'HLA II': '#A23B72',
    'HLA I/II': '#06A77D',
    'Non-HLA': '#F77F00',
    'HLA (needs confirmation)': '#D62828',
}


def load_data():
    """加载数据"""
    print("Loading data...")
    csv_file = DATA_DIR / "all_metadata_classified.csv"
    if not csv_file.exists():
        csv_file = DATA_DIR / "all_metadata_cleaned.csv"

    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} records")
    return df


def create_hla_distribution_chart(df):
    """创建HLA类型分布图（饼图+柱状图组合）"""
    print("\nCreating HLA type distribution chart...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # 左侧：饼图
    hla_counts = df['hla_type'].value_counts()
    colors_list = [HLA_COLORS.get(hla, COLORS['info']) for hla in hla_counts.index]

    wedges, texts, autotexts = ax1.pie(
        hla_counts.values,
        labels=hla_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors_list,
        explode=[0.05 if i == 0 else 0 for i in range(len(hla_counts))],
        textprops={'fontsize': 11, 'weight': 'bold'}
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)

    ax1.set_title('HLA Type Distribution\n(Percentage)', fontsize=14, weight='bold', pad=20)

    # 右侧：柱状图
    bars = ax2.barh(hla_counts.index, hla_counts.values, color=colors_list, alpha=0.8)
    ax2.set_xlabel('Number of Datasets', fontsize=12, weight='bold')
    ax2.set_title('HLA Type Distribution\n(Count)', fontsize=14, weight='bold', pad=20)

    # 添加数值标签
    for i, (bar, count) in enumerate(zip(bars, hla_counts.values)):
        ax2.text(count + 1, i, f'{count}', va='center', fontsize=11, weight='bold')

    plt.tight_layout()
    output_file = VIS_DIR / "1_hla_distribution.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_disease_distribution_chart(df):
    """创建疾病类别分布图"""
    print("\nCreating disease category distribution chart...")

    fig, ax = plt.subplots(figsize=(12, 8))

    disease_counts = df['disease_category'].value_counts()
    colors_gradient = sns.color_palette("RdYlGn_r", len(disease_counts))

    bars = ax.bar(range(len(disease_counts)), disease_counts.values,
                   color=colors_gradient, alpha=0.85, edgecolor='black', linewidth=1.5)

    ax.set_xticks(range(len(disease_counts)))
    ax.set_xticklabels(disease_counts.index, rotation=45, ha='right', fontsize=11)
    ax.set_ylabel('Number of Datasets', fontsize=12, weight='bold')
    ax.set_title('Disease Category Distribution', fontsize=16, weight='bold', pad=20)

    # 添加数值标签
    for i, (bar, count) in enumerate(zip(bars, disease_counts.values)):
        height = bar.get_height()
        percentage = (count / len(df)) * 100
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count}\n({percentage:.1f}%)',
                ha='center', va='bottom', fontsize=10, weight='bold')

    plt.tight_layout()
    output_file = VIS_DIR / "2_disease_distribution.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_sample_type_chart(df):
    """创建样本类型分布图（水平柱状图）"""
    print("\nCreating sample type distribution chart...")

    fig, ax = plt.subplots(figsize=(14, 10))

    # 获取样本类型分布（前15个）
    sample_counts = df['sample_type'].value_counts().head(15)

    # 创建颜色映射
    colors = []
    for sample in sample_counts.index:
        if 'Cell line' in sample:
            colors.append(COLORS['primary'])
        elif 'Blood' in sample:
            colors.append(COLORS['danger'])
        elif 'Tissue' in sample:
            colors.append(COLORS['success'])
        else:
            colors.append(COLORS['warning'])

    bars = ax.barh(range(len(sample_counts)), sample_counts.values,
                    color=colors, alpha=0.85, edgecolor='black', linewidth=1.2)

    ax.set_yticks(range(len(sample_counts)))
    ax.set_yticklabels(sample_counts.index, fontsize=11)
    ax.set_xlabel('Number of Datasets', fontsize=12, weight='bold')
    ax.set_title('Sample Type Distribution (Top 15)', fontsize=16, weight='bold', pad=20)

    # 添加数值标签
    for i, (bar, count) in enumerate(zip(bars, sample_counts.values)):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10, weight='bold')

    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS['primary'], label='Cell Line'),
        Patch(facecolor=COLORS['danger'], label='Blood'),
        Patch(facecolor=COLORS['success'], label='Tissue'),
        Patch(facecolor=COLORS['warning'], label='Unknown/Other'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    plt.tight_layout()
    output_file = VIS_DIR / "3_sample_distribution.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_completeness_heatmap(df):
    """创建数据完整性热力图"""
    print("\nCreating data completeness heatmap...")

    fig, ax = plt.subplots(figsize=(14, 8))

    # 选择关键字段
    key_fields = [
        'title', 'description', 'organisms', 'diseases', 'tissues',
        'cell_types', 'instruments', 'ptms', 'keywords',
        'pubmed_ids', 'dois', 'sample_protocol', 'data_protocol'
    ]

    # 计算每个字段的完整性
    completeness_data = []
    for field in key_fields:
        if field in df.columns:
            non_empty = df[field].notna() & (df[field] != '') & (df[field] != 'nan')
            completeness = (non_empty.sum() / len(df)) * 100
            completeness_data.append(completeness)
        else:
            completeness_data.append(0)

    # 创建热力图数据
    data_matrix = np.array(completeness_data).reshape(-1, 1)

    # 绘制热力图
    sns.heatmap(data_matrix, annot=True, fmt='.1f', cmap='RdYlGn',
                yticklabels=key_fields, xticklabels=['Completeness (%)'],
                cbar_kws={'label': 'Completeness %'},
                vmin=0, vmax=100, linewidths=1, linecolor='white',
                ax=ax, annot_kws={'fontsize': 10, 'weight': 'bold'})

    ax.set_title('Data Field Completeness Analysis', fontsize=16, weight='bold', pad=20)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=11)

    plt.tight_layout()
    output_file = VIS_DIR / "4_completeness_heatmap.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_timeline_chart(df):
    """创建数据集发布时间序列图"""
    print("\nCreating timeline chart...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))

    # 处理日期
    df_copy = df.copy()
    df_copy['publication_date'] = pd.to_datetime(df_copy['publication_date'], errors='coerce')
    df_copy = df_copy.dropna(subset=['publication_date'])
    df_copy['year'] = df_copy['publication_date'].dt.year
    df_copy['year_month'] = df_copy['publication_date'].dt.to_period('M')

    # 上图：按年统计
    year_counts = df_copy['year'].value_counts().sort_index()
    ax1.plot(year_counts.index, year_counts.values, marker='o', linewidth=2.5,
             markersize=8, color=COLORS['primary'], alpha=0.8)
    ax1.fill_between(year_counts.index, year_counts.values, alpha=0.3, color=COLORS['primary'])
    ax1.set_xlabel('Year', fontsize=12, weight='bold')
    ax1.set_ylabel('Number of Datasets', fontsize=12, weight='bold')
    ax1.set_title('Dataset Publications Over Time (By Year)', fontsize=14, weight='bold', pad=15)

    # 添加数值标签
    for x, y in zip(year_counts.index, year_counts.values):
        ax1.text(x, y + 0.5, str(y), ha='center', va='bottom', fontsize=9, weight='bold')

    # 下图：按HLA类型分组的年度趋势
    hla_by_year = df_copy.groupby(['year', 'hla_type']).size().unstack(fill_value=0)

    for hla_type in hla_by_year.columns:
        color = HLA_COLORS.get(hla_type, COLORS['info'])
        ax2.plot(hla_by_year.index, hla_by_year[hla_type],
                marker='o', linewidth=2, markersize=6,
                label=hla_type, color=color, alpha=0.8)

    ax2.set_xlabel('Year', fontsize=12, weight='bold')
    ax2.set_ylabel('Number of Datasets', fontsize=12, weight='bold')
    ax2.set_title('Dataset Publications by HLA Type', fontsize=14, weight='bold', pad=15)
    ax2.legend(loc='upper left', fontsize=10)

    plt.tight_layout()
    output_file = VIS_DIR / "5_timeline.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_repository_comparison(df):
    """创建数据库对比图"""
    print("\nCreating repository comparison chart...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # 1. 数据库分布（饼图）
    repo_counts = df['repository'].value_counts()
    colors = sns.color_palette("Set2", len(repo_counts))
    ax1.pie(repo_counts.values, labels=repo_counts.index, autopct='%1.1f%%',
            startangle=90, colors=colors, textprops={'fontsize': 11, 'weight': 'bold'})
    ax1.set_title('Dataset Distribution by Repository', fontsize=13, weight='bold', pad=15)

    # 2. 各数据库的HLA类型分布
    repo_hla = pd.crosstab(df['repository'], df['hla_type'])
    repo_hla.plot(kind='bar', stacked=True, ax=ax2,
                  color=[HLA_COLORS.get(col, COLORS['info']) for col in repo_hla.columns],
                  alpha=0.85)
    ax2.set_xlabel('Repository', fontsize=11, weight='bold')
    ax2.set_ylabel('Number of Datasets', fontsize=11, weight='bold')
    ax2.set_title('HLA Type Distribution by Repository', fontsize=13, weight='bold', pad=15)
    ax2.legend(title='HLA Type', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')

    # 3. 数据质量对比
    if 'metadata_quality' in df.columns:
        repo_quality = pd.crosstab(df['repository'], df['metadata_quality'])
        repo_quality = repo_quality[['High', 'Medium', 'Low']] if all(col in repo_quality.columns for col in ['High', 'Medium', 'Low']) else repo_quality
        repo_quality.plot(kind='bar', ax=ax3, color=['#06A77D', '#FEE440', '#D62828'], alpha=0.85)
        ax3.set_xlabel('Repository', fontsize=11, weight='bold')
        ax3.set_ylabel('Number of Datasets', fontsize=11, weight='bold')
        ax3.set_title('Data Quality by Repository', fontsize=13, weight='bold', pad=15)
        ax3.legend(title='Quality', fontsize=9)
        ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45, ha='right')
    else:
        ax3.text(0.5, 0.5, 'Quality data not available',
                ha='center', va='center', fontsize=12, transform=ax3.transAxes)
        ax3.axis('off')

    # 4. 需要人工审核的数据集比例
    if 'needs_manual_review' in df.columns:
        manual_review = df.groupby('repository')['needs_manual_review'].apply(
            lambda x: (x == True).sum() if x.dtype == bool else (x == 'True').sum()
        )
        total_counts = df['repository'].value_counts()
        review_percentage = (manual_review / total_counts * 100).fillna(0)

        bars = ax4.bar(review_percentage.index, review_percentage.values,
                       color=COLORS['warning'], alpha=0.85, edgecolor='black', linewidth=1.2)
        ax4.set_xlabel('Repository', fontsize=11, weight='bold')
        ax4.set_ylabel('Percentage (%)', fontsize=11, weight='bold')
        ax4.set_title('Datasets Requiring Manual Review', fontsize=13, weight='bold', pad=15)
        ax4.set_xticklabels(review_percentage.index, rotation=45, ha='right')

        for bar, pct in zip(bars, review_percentage.values):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{pct:.1f}%', ha='center', va='bottom', fontsize=10, weight='bold')
    else:
        ax4.text(0.5, 0.5, 'Manual review data not available',
                ha='center', va='center', fontsize=12, transform=ax4.transAxes)
        ax4.axis('off')

    plt.tight_layout()
    output_file = VIS_DIR / "6_repository_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def create_comprehensive_dashboard(df):
    """创建综合仪表盘"""
    print("\nCreating comprehensive dashboard...")

    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 1. 核心指标卡片（左上）
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')

    total_datasets = len(df)
    hla_accuracy = (df['hla_type'] != 'HLA (需人工确认)').sum() / total_datasets * 100
    disease_complete = (df['disease_type'] != 'Unknown').sum() / total_datasets * 100
    sample_complete = (df['sample_type'] != 'Unknown').sum() / total_datasets * 100

    stats_text = f"""
    ╔══════════════════════════════╗
    ║   HLA Metadata Overview      ║
    ╠══════════════════════════════╣
    ║                              ║
    ║  Total Datasets:    {total_datasets:>6}  ║
    ║                              ║
    ║  HLA Classification: {hla_accuracy:>5.1f}% ║
    ║  Disease Complete:   {disease_complete:>5.1f}% ║
    ║  Sample Complete:    {sample_complete:>5.1f}% ║
    ║                              ║
    ╚══════════════════════════════╝
    """

    ax1.text(0.5, 0.5, stats_text, ha='center', va='center',
            fontsize=11, family='monospace', weight='bold',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    # 2. HLA类型分布（中上）
    ax2 = fig.add_subplot(gs[0, 1:])
    hla_counts = df['hla_type'].value_counts()
    colors_list = [HLA_COLORS.get(hla, COLORS['info']) for hla in hla_counts.index]
    bars = ax2.bar(hla_counts.index, hla_counts.values, color=colors_list, alpha=0.85)
    ax2.set_title('HLA Type Distribution', fontsize=13, weight='bold')
    ax2.set_ylabel('Count', fontsize=10, weight='bold')
    for bar, count in zip(bars, hla_counts.values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{count}', ha='center', va='bottom', fontsize=9, weight='bold')

    # 3. 疾病类别（左中）
    ax3 = fig.add_subplot(gs[1, 0])
    disease_counts = df['disease_category'].value_counts().head(6)
    colors = sns.color_palette("Set3", len(disease_counts))
    ax3.pie(disease_counts.values, labels=disease_counts.index, autopct='%1.1f%%',
            colors=colors, textprops={'fontsize': 9})
    ax3.set_title('Disease Categories', fontsize=12, weight='bold')

    # 4. 样本类型（中中）
    ax4 = fig.add_subplot(gs[1, 1])
    sample_main = df['sample_type'].apply(
        lambda x: 'Cell line' if 'Cell line' in str(x)
        else 'Blood' if 'Blood' in str(x)
        else 'Tissue' if 'Tissue' in str(x)
        else 'Unknown'
    ).value_counts()
    colors = [COLORS['primary'], COLORS['danger'], COLORS['success'], COLORS['warning']]
    bars = ax4.bar(sample_main.index, sample_main.values, color=colors[:len(sample_main)], alpha=0.85)
    ax4.set_title('Sample Types (Main Categories)', fontsize=12, weight='bold')
    ax4.set_ylabel('Count', fontsize=10, weight='bold')
    for bar, count in zip(bars, sample_main.values):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{count}', ha='center', va='bottom', fontsize=9, weight='bold')

    # 5. 数据库分布（右中）
    ax5 = fig.add_subplot(gs[1, 2])
    repo_counts = df['repository'].value_counts()
    colors = sns.color_palette("Pastel1", len(repo_counts))
    ax5.pie(repo_counts.values, labels=repo_counts.index, autopct='%1.1f%%',
            colors=colors, textprops={'fontsize': 9})
    ax5.set_title('Repository Distribution', fontsize=12, weight='bold')

    # 6. 时间趋势（下部，跨列）
    ax6 = fig.add_subplot(gs[2, :])
    df_copy = df.copy()
    df_copy['publication_date'] = pd.to_datetime(df_copy['publication_date'], errors='coerce')
    df_copy = df_copy.dropna(subset=['publication_date'])
    df_copy['year'] = df_copy['publication_date'].dt.year
    year_counts = df_copy['year'].value_counts().sort_index()
    ax6.plot(year_counts.index, year_counts.values, marker='o', linewidth=2.5,
            markersize=8, color=COLORS['primary'], alpha=0.8)
    ax6.fill_between(year_counts.index, year_counts.values, alpha=0.3, color=COLORS['primary'])
    ax6.set_xlabel('Year', fontsize=11, weight='bold')
    ax6.set_ylabel('Number of Datasets', fontsize=11, weight='bold')
    ax6.set_title('Dataset Publications Timeline', fontsize=13, weight='bold')

    # 总标题
    fig.suptitle('HLA Metadata Collection - Comprehensive Dashboard',
                 fontsize=18, weight='bold', y=0.98)

    output_file = VIS_DIR / "7_comprehensive_dashboard.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file}")
    plt.close()


def main():
    """主函数"""
    print("="*60)
    print("HLA Metadata Visualization Generator")
    print("="*60)

    # 加载数据
    df = load_data()

    # 生成各种图表
    create_hla_distribution_chart(df)
    create_disease_distribution_chart(df)
    create_sample_type_chart(df)
    create_completeness_heatmap(df)
    create_timeline_chart(df)
    create_repository_comparison(df)
    create_comprehensive_dashboard(df)

    print("\n" + "="*60)
    print("All visualizations generated successfully!")
    print(f"Output directory: {VIS_DIR}")
    print("="*60)

    # 列出生成的文件
    print("\nGenerated files:")
    for i, file in enumerate(sorted(VIS_DIR.glob("*.png")), 1):
        print(f"  {i}. {file.name}")


if __name__ == "__main__":
    main()
