"""
生成性能对比图表
从benchmark_results.json读取数据，生成高质量图表
"""

import json
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_results(filename="benchmark_results.json"):
    """加载测试结果"""

    with open(filename, 'r', encoding='utf-8') as f:
        results = json.load(f)

    print(f"✓ 已加载 {len(results)} 个测试场景的结果")
    return results

def generate_latency_chart(results, output_file="latency_comparison.png"):
    """生成延迟对比柱状图"""

    print(f"\n生成延迟对比图...")

    # 提取数据
    test_names = [r['test_name'].replace("Q", "Q") for r in results]  # 简化名称
    sql_latencies = [r['sql_avg_ms'] for r in results]
    nosql_latencies = [r['nosql_avg_ms'] for r in results]

    # 设置图表
    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(test_names))
    width = 0.35

    # 绘制柱状图
    bars1 = ax.bar(x - width/2, sql_latencies, width,
                   label='SQL (PostgreSQL)',
                   color='#3498db',
                   edgecolor='black',
                   linewidth=1)

    bars2 = ax.bar(x + width/2, nosql_latencies, width,
                   label='NoSQL (MongoDB + Redis)',
                   color='#e74c3c',
                   edgecolor='black',
                   linewidth=1)

    # 在柱子上方显示数值
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom',
                   fontsize=10, fontweight='bold')

    # 设置标签和标题
    ax.set_xlabel('Query Scenario', fontsize=14, fontweight='bold')
    ax.set_ylabel('Average Latency (ms)', fontsize=14, fontweight='bold')
    ax.set_title('SQL vs NoSQL: Average Latency Comparison',
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(test_names, rotation=15, ha='right', fontsize=11)

    # 图例
    ax.legend(fontsize=12, loc='upper left', frameon=True, shadow=True)

    # 网格线
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # 设置Y轴从0开始
    ax.set_ylim(bottom=0)

    # 调整布局
    plt.tight_layout()

    # 保存图表
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 延迟对比图已保存: {output_file}")

    plt.close()

def generate_throughput_chart(results, output_file="throughput_comparison.png"):
    """生成吞吐量对比柱状图"""

    print(f"\n生成吞吐量对比图...")

    # 提取数据
    test_names = [r['test_name'].replace("Q", "Q") for r in results]
    sql_qps = [r['sql_qps'] for r in results]
    nosql_qps = [r['nosql_qps'] for r in results]

    # 设置图表
    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(test_names))
    width = 0.35

    # 绘制柱状图
    bars1 = ax.bar(x - width/2, sql_qps, width,
                   label='SQL (PostgreSQL)',
                   color='#3498db',
                   edgecolor='black',
                   linewidth=1)

    bars2 = ax.bar(x + width/2, nosql_qps, width,
                   label='NoSQL (MongoDB + Redis)',
                   color='#e74c3c',
                   edgecolor='black',
                   linewidth=1)

    # 在柱子上方显示数值
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom',
                   fontsize=10, fontweight='bold')

    # 设置标签和标题
    ax.set_xlabel('Query Scenario', fontsize=14, fontweight='bold')
    ax.set_ylabel('Throughput (QPS)', fontsize=14, fontweight='bold')
    ax.set_title('SQL vs NoSQL: Throughput Comparison',
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(test_names, rotation=15, ha='right', fontsize=11)

    # 图例
    ax.legend(fontsize=12, loc='upper left', frameon=True, shadow=True)

    # 网格线
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # 设置Y轴从0开始
    ax.set_ylim(bottom=0)

    # 调整布局
    plt.tight_layout()

    # 保存图表
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 吞吐量对比图已保存: {output_file}")

    plt.close()

def generate_speedup_chart(results, output_file="speedup_comparison.png"):
    """生成性能提升倍数图"""

    print(f"\n生成性能提升倍数图...")

    # 提取数据
    test_names = [r['test_name'].replace("Q", "Q") for r in results]
    speedups = [r['speedup'] for r in results]
    winners = [r['winner'] for r in results]

    # 设置颜色（NoSQL赢家用红色，SQL赢家用蓝色）
    colors = ['#e74c3c' if w == 'NoSQL' else '#3498db' for w in winners]

    # 设置图表
    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(test_names))
    bars = ax.bar(x, speedups, color=colors, edgecolor='black', linewidth=1)

    # 在柱子上方显示数值和赢家
    for i, (bar, winner, speedup) in enumerate(zip(bars, winners, speedups)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{speedup:.2f}x\n({winner})',
               ha='center', va='bottom',
               fontsize=10, fontweight='bold')

    # 添加基准线
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=2, label='Baseline (1x)')

    # 设置标签和标题
    ax.set_xlabel('Query Scenario', fontsize=14, fontweight='bold')
    ax.set_ylabel('Performance Speedup', fontsize=14, fontweight='bold')
    ax.set_title('Performance Improvement: NoSQL vs SQL',
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(test_names, rotation=15, ha='right', fontsize=11)

    # 图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#e74c3c', edgecolor='black', label='NoSQL Winner'),
        Patch(facecolor='#3498db', edgecolor='black', label='SQL Winner'),
        plt.Line2D([0], [0], color='gray', linewidth=2, linestyle='--', label='Baseline (1x)')
    ]
    ax.legend(handles=legend_elements, fontsize=12, loc='upper left', frameon=True, shadow=True)

    # 网格线
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # 设置Y轴从0开始
    ax.set_ylim(bottom=0)

    # 调整布局
    plt.tight_layout()

    # 保存图表
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 性能提升倍数图已保存: {output_file}")

    plt.close()

def main():
    """主函数"""

    print("="*60)
    print("图表生成工具")
    print("="*60)

    # 加载测试结果
    results = load_results("benchmark_results.json")

    # 生成三种图表
    generate_latency_chart(results)
    generate_throughput_chart(results)
    generate_speedup_chart(results)

    print("\n" + "="*60)
    print("✅ 所有图表生成完成!")
    print("="*60)
    print("\n生成的文件:")
    print("  1. latency_comparison.png     - 延迟对比图")
    print("  2. throughput_comparison.png  - 吞吐量对比图")
    print("  3. speedup_comparison.png     - 性能提升倍数图")

if __name__ == "__main__":
    main()