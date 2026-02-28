"""
中文字体配置模块
自动检测并配置可用的中文字体
"""
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def setup_chinese_font():
    """
    自动检测并配置可用的中文字体

    按优先级尝试以下字体：
    1. macOS: Hiragino Sans GB, PingFang SC, STHeiti
    2. Windows: Microsoft YaHei, SimHei
    3. Linux: WenQuanYi Micro Hei, Noto Sans CJK
    4. 通用: Arial Unicode MS

    Returns:
    --------
    font_name : str
        实际使用的字体名称
    """
    # 按平台和优先级排序的字体列表
    font_candidates = [
        # macOS 专用字体
        'Hiragino Sans GB',
        'PingFang SC',
        'STHeiti',
        'Heiti TC',
        # Windows 专用字体
        'Microsoft YaHei',
        'SimHei',
        # Linux 专用字体
        'WenQuanYi Micro Hei',
        'WenQuanYi Zen Hei',
        'Noto Sans CJK SC',
        'Noto Sans CJK TC',
        # 通用字体
        'Arial Unicode MS',
        'DejaVu Sans',
    ]

    # 获取系统所有可用字体
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    # 查找第一个可用的中文字体
    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams['font.sans-serif'] = [font] + plt.rcParams['font.sans-serif']
            plt.rcParams['axes.unicode_minus'] = False

            # 验证字体是否真的可以渲染中文
            try:
                test_prop = fm.FontProperties(family=font)
                # 如果可以获取字体名称，说明字体可用
                test_prop.get_name()
                return font
            except:
                continue

    # 如果没有找到任何中文字体，使用默认设置
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
