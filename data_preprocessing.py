"""
数据预处理模块
功能：读取Excel数据，清洗数据，计算收益率和基差
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


def preprocess_data(file_path: str, output_dir: str = 'outputs') -> pd.DataFrame:
    """
    数据预处理主函数

    Parameters:
    -----------
    file_path : str
        Excel文件路径
    output_dir : str
        输出目录

    Returns:
    --------
    data : pd.DataFrame
        预处理后的数据，包含以下字段：
        - date: 日期
        - spot: 现货价格
        - futures: 期货价格
        - r_s: 现货收益率
        - r_f: 期货收益率
        - spread: 基差 (spot - futures)
    """

    print("=" * 60)
    print("步骤1: 数据预处理")
    print("=" * 60)

    # 1. 读取Excel文件
    print("\n[1/5] 读取Excel文件...")
    try:
        # 跳过前两行表头，从第3行开始读取
        df_raw = pd.read_excel(file_path, header=None, skiprows=[0, 1])

        # 提取所需列（根据列索引）
        data = pd.DataFrame({
            'date': pd.to_datetime(df_raw[0]),           # 日期（第1列，索引0）
            'spot': df_raw[3].astype(float),             # 上海现货价格（第4列，索引3）
            'futures': df_raw[2].astype(float)           # 期货价格（第3列，索引2）
        })

        print(f"   ✓ 成功读取 {len(data)} 行数据")
    except Exception as e:
        print(f"   ✗ 读取失败: {e}")
        raise

    # 2. 数据清洗
    print("\n[2/5] 数据清洗...")

    # 删除缺失值
    n_before = len(data)
    data = data.dropna()
    n_after = len(data)
    print(f"   ✓ 删除缺失值: {n_before} → {n_after} 行")

    # 处理异常值（使用IQR方法）
    def remove_outliers(df, column, threshold=3.0):
        """使用Z-score方法识别异常值"""
        mean = df[column].mean()
        std = df[column].std()
        z_scores = np.abs((df[column] - mean) / std)
        return df[z_scores < threshold]

    data_clean = remove_outliers(data, 'spot').copy()
    data_clean = remove_outliers(data_clean, 'futures').copy()

    n_outliers = len(data) - len(data_clean)
    if n_outliers > 0:
        print(f"   ✓ 删除异常值: {n_outliers} 行")
    else:
        print(f"   ✓ 未检测到异常值")

    data = data_clean

    # 按日期排序
    data = data.sort_values('date').reset_index(drop=True)
    print(f"   ✓ 数据已按日期排序")

    # 检查日期连续性
    date_range = (data['date'].max() - data['date'].min()).days
    expected_days = len(data)
    print(f"   ✓ 数据时间范围: {data['date'].min().strftime('%Y-%m-%d')} 至 {data['date'].max().strftime('%Y-%m-%d')}")
    print(f"   ✓ 实际交易日: {expected_days} 天（跨度 {date_range} 天）")

    # 3. 计算对数收益率
    print("\n[3/5] 计算对数收益率...")
    data['r_s'] = np.log(data['spot'] / data['spot'].shift(1))
    data['r_f'] = np.log(data['futures'] / data['futures'].shift(1))

    # 删除第一行（NaN）
    data = data.dropna().reset_index(drop=True)

    print(f"   ✓ 现货收益率均值: {data['r_s'].mean():.6f}")
    print(f"   ✓ 现货收益率标准差: {data['r_s'].std():.6f}")
    print(f"   ✓ 期货收益率均值: {data['r_f'].mean():.6f}")
    print(f"   ✓ 期货收益率标准差: {data['r_f'].std():.6f}")

    # 4. 计算基差
    print("\n[4/5] 计算基差...")
    data['spread'] = data['spot'] - data['futures']

    print(f"   ✓ 基差均值: {data['spread'].mean():.2f}")
    print(f"   ✓ 基差标准差: {data['spread'].std():.2f}")
    print(f"   ✓ 基差最小值: {data['spread'].min():.2f}")
    print(f"   ✓ 基差最大值: {data['spread'].max():.2f}")

    # 5. 保存预处理后的数据
    print("\n[5/5] 保存预处理后的数据...")
    import os
    os.makedirs(output_dir, exist_ok=True)

    # 保存为CSV
    output_csv = os.path.join(output_dir, 'preprocessed_data.csv')
    data.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"   ✓ 已保存: {output_csv}")

    # 保存为Excel
    output_excel = os.path.join(output_dir, 'preprocessed_data.xlsx')
    data.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"   ✓ 已保存: {output_excel}")

    # 6. 数据摘要统计
    print("\n" + "=" * 60)
    print("数据摘要统计")
    print("=" * 60)

    summary = data[['spot', 'futures', 'r_s', 'r_f', 'spread']].describe()
    print(summary.to_string())

    print("\n" + "=" * 60)
    print("✓ 数据预处理完成！")
    print("=" * 60)

    return data


if __name__ == "__main__":
    # 测试数据预处理
    file_path = "基差数据.xlsx"
    data = preprocess_data(file_path)

    print(f"\n最终数据集包含 {len(data)} 个观测值")
    print(f"\n数据预览:")
    print(data.head(10))
