# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Define data files to include
datas = [
    ('services', 'services'),
    ('api', 'api'),
    ('database', 'database'),
    ('requirements.txt', '.'),
    ('config.yaml', '.'),
]

# Core hidden imports for AI/ML
hiddenimports = [
    # Core FastAPI and web
    'fastapi',
    'uvicorn',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.server',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    'pydantic',
    'pydantic_core',
    'starlette',
    'starlette.applications',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.responses',
    'starlette.routing',
    'multipart',
    'python_multipart',
    'h11',
    'anyio',
    'sniffio',
    'click',
    'colorama',
    
    # AI/ML core
    'whisper',
    'torch',
    'torch.nn',
    'torch.nn.functional',
    'torch.utils',
    'torch.utils.data',
    'transformers',
    'sentence_transformers',
    'tiktoken',
    'tokenizers',
    'huggingface_hub',
    'safetensors',
    
    # Audio processing
    'numpy',
    'scipy',
    'soundfile',
    'librosa',
    'audio2numpy',
    
    # HTTP clients
    'httpx',
    'requests',
    'aiohttp',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    
    # Text processing
    'fuzzywuzzy',
    'Levenshtein',
    'rapidfuzz',
    'pyyaml',
    'regex',
    
    # Database
    'sqlalchemy',
    'aiosqlite',
    'pandas',
    'pytz',
    
    # Utilities
    'tqdm',
    'packaging',
    'typing_extensions',
    'annotated_types',
    'greenlet',
    'filelock',
    'fsspec',
    'joblib',
    'threadpoolctl',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib.tests',
        'numpy.tests',
        'scipy.tests',
        'pandas.tests',
        'torch.test',
        'transformers.tests',
        'pytest',
        # Remove unittest from excludes to fix the error
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='feedvox_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='feedvox_backend',
) 