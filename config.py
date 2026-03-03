import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Flask配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'garch-platform-dev-key')
DEBUG = True
HOST = '0.0.0.0'
PORT = 5001  # Changed from 5000 to avoid macOS AirPlay Receiver conflict

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
