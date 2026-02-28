"""
Basic GARCH Analyzer 命令行入口

Usage:
    python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格

    python -m basic_garch_analyzer --data data.xlsx --interactive
"""
import argparse
import sys
from pathlib import Path
from basic_garch_analyzer import run_analysis, ModelConfig


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Basic GARCH 套保策略回测分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用
  python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格

  # 自定义参数
  python -m basic_garch_analyzer --data data.xlsx --spot 现货 --futures 期货 --tax-rate 0.0

  # 交互模式
  python -m basic_garch_analyzer --data data.xlsx --interactive

  # 指定工作表
  python -m basic_garch_analyzer --data data.xlsx --spot 现货 --futures 期货 --sheet "数据"
        """
    )

    # 必需参数
    parser.add_argument(
        '--data', '-d',
        required=True,
        help='Excel数据文件路径'
    )

    # 交互模式
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='交互式选择列名（无需指定 --spot 和 --futures）'
    )

    # 列名参数
    parser.add_argument(
        '--spot',
        help='现货价格列名'
    )
    parser.add_argument(
        '--futures',
        help='期货价格列名'
    )
    parser.add_argument(
        '--date-col',
        help='日期列名（默认自动检测）'
    )
    parser.add_argument(
        '--sheet',
        default=0,
        help='工作表名或索引（默认: 0）'
    )

    # GARCH 模型参数
    parser.add_argument(
        '--p',
        type=int,
        default=1,
        help='GARCH(p,q) 的 p 阶数（默认: 1）'
    )
    parser.add_argument(
        '--q',
        type=int,
        default=1,
        help='GARCH(p,q) 的 q 阶数（默认: 1）'
    )

    # 套保参数
    parser.add_argument(
        '--corr-window',
        type=int,
        default=120,
        help='动态相关系数滚动窗口大小，单位天（默认: 120）'
    )
    parser.add_argument(
        '--tax-rate',
        type=float,
        default=0.13,
        help='税点调整比例（默认: 0.13）'
    )

    # 输出配置
    parser.add_argument(
        '--output-dir', '-o',
        default='outputs',
        help='输出目录路径（默认: outputs）'
    )

    return parser.parse_args()


def validate_args(args):
    """验证参数"""
    # 检查文件存在性
    if not Path(args.data).exists():
        print(f"❌ 错误: 文件不存在 - {args.data}")
        sys.exit(1)

    # 交互模式不需要指定列名
    if not args.interactive:
        if not args.spot:
            print("❌ 错误: 非交互模式必须指定 --spot 参数")
            sys.exit(1)
        if not args.futures:
            print("❌ 错误: 非交互模式必须指定 --futures 参数")
            sys.exit(1)

    # 验证数值参数
    if args.p < 1 or args.q < 1:
        print(f"❌ 错误: GARCH阶数必须 >= 1")
        sys.exit(1)

    if args.corr_window < 30:
        print(f"❌ 错误: 相关系数窗口至少30天")
        sys.exit(1)

    if not 0 <= args.tax_rate <= 1:
        print(f"❌ 错误: 税率必须在[0,1]之间")
        sys.exit(1)


def main():
    """主入口函数"""
    # 解析参数
    args = parse_args()

    # 验证参数
    validate_args(args)

    # 创建配置对象
    config = ModelConfig(
        p=args.p,
        q=args.q,
        corr_window=args.corr_window,
        tax_rate=args.tax_rate,
        output_dir=args.output_dir
    )

    # 运行分析
    try:
        result = run_analysis(
            excel_path=args.data,
            spot_col=args.spot,
            futures_col=args.futures,
            date_col=args.date_col,
            config=config,
            interactive=args.interactive
        )

        # 输出报告路径
        print(f"\n" + "=" * 70)
        print("📊 报告已生成:")
        print(f"  HTML: {result['report_info']['html_path']}")
        print(f"  CSV:  {result['report_info']['csv_path']}")
        print("=" * 70)

        return 0

    except FileNotFoundError as e:
        print(f"❌ 文件错误: {e}")
        return 1
    except ValueError as e:
        print(f"❌ 数据错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
