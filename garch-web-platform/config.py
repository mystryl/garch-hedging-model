import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Flask配置
# 注意：在生产环境中，必须设置 SECRET_KEY 环境变量
SECRET_KEY = os.environ.get('SECRET_KEY', None)
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print("⚠️  警告: 使用自动生成的 SECRET_KEY。重启服务后会话将失效。")
    print("    请在生产环境设置 SECRET_KEY 环境变量。")

# DEBUG 模式：默认关闭，可通过环境变量启用
# 生产环境必须设置为 False
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
HOST = '0.0.0.0'
# 注意：避免使用浏览器不安全端口（如 6000, 6665-6669 等）
# 推荐端口：5000, 5001, 8000, 8080, 3000 等
PORT = int(os.environ.get('PORT', '5000'))  # 改为 5000（Flask 默认端口）

# 文件上传配置
UPLOAD_FOLDER = BASE_DIR / 'outputs' / 'uploaded'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# 输出配置
OUTPUT_DIR = BASE_DIR / 'outputs'

# 模型配置
MODEL_CONFIG = {
    'basic_garch': {
        'name': 'Basic GARCH',
        'description': '基础GARCH模型，快速计算',
        'p': 1, 'q': 1,
        'corr_window': 120,
        'tax_rate': 0.13
    },
    'dcc_garch': {
        'name': 'DCC-GARCH',
        'description': '动态条件相关GARCH，捕捉时变相关性',
        'p': 1, 'q': 1,
        'dist': 'norm',
        'tax_rate': 0.13
    },
    'ecm_garch': {
        'name': 'ECM-GARCH',
        'description': '误差修正GARCH，考虑协整关系',
        'p': 1, 'q': 1,
        'coint_window': 120,
        'tax_adjust': True,
        'coupling_method': 'ect-garch',
        'tax_rate': 0.13
    }
}
