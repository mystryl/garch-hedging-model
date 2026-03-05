"""
中文字体配置模块
自动检测并配置可用的中文字体
"""
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import warnings


def setup_chinese_font():
    """
    自动检测并配置可用的中文字体

    使用字体文件路径而不是字体名称，更可靠

    Returns:
    --------
    font_name : str
        实际使用的字体名称
    """
    # macOS 上的中文字体文件路径
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',  # PingFang SC
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
    ]

    # 尝试每个字体文件
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                # 使用字体文件路径创建 FontProperties
                font_prop = fm.FontProperties(fname=font_path)
                font_name = font_prop.get_name()

                # 设置为默认字体
                plt.rcParams['font.family'] = font_name
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False

                # 验证是否可以渲染中文
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    fig = plt.figure()
                    ax = fig.add_subplot(111)
                    ax.text(0.5, 0.5, '测试', fontproperties=font_prop)

                    # 检查是否有字体相关的警告
                    font_warnings = [warning for warning in w
                                   if 'font' in str(warning.message).lower()
                                   or 'glyph' in str(warning.message).lower()]

                    plt.close(fig)

                    if not font_warnings:
                        print(f"✓ 已设置中文字体: {font_name}")
                        print(f"  字体文件: {os.path.basename(font_path)}")
                        return font_name
            except Exception as e:
                continue

    # 如果直接路径失败，尝试按名称查找
    print("尝试按名称查找中文字体...")
    font_candidates = [
        'PingFang SC',
        'Hiragino Sans GB',
        'STHeiti',
        'Heiti TC',
        'Arial Unicode MS',
    ]

    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            print(f"✓ 已设置中文字体(按名称): {font}")
            return font

    # 如果都失败了
    print("⚠️  警告: 未找到可用的中文字体，图表中的中文可能无法正常显示")
    return None


def get_font_info():
    """
    获取当前字体配置信息

    Returns:
    --------
    info : dict
        字体信息字典
    """
    current_font = plt.rcParams['font.sans-serif'][0] if plt.rcParams['font.sans-serif'] else 'default'

    # 获取所有包含中文支持的字体
    chinese_fonts = []
    for font in fm.fontManager.ttflist:
        font_name = font.name
        # 查找常见的支持中文的字体
        keywords = ['ping', 'fang', 'hei', 'song', 'kai', 'yuan',
                   'noto.*cjk', 'chinese', 'hiragino', 'unicode',
                   'yahei', 'simhei', 'simsun', 'stzh']
        for keyword in keywords:
            if keyword in font_name.lower():
                chinese_fonts.append(font_name)
                break

    chinese_fonts = sorted(list(set(chinese_fonts)))

    return {
        'current_font': current_font,
        'available_chinese_fonts': chinese_fonts[:20],  # 限制数量
    }


# 自动配置（模块导入时执行）
if __name__ != '__main__':
    setup_chinese_font()
