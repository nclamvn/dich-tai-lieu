"""
Centralized constants for AI Translator Pro.
All magic numbers extracted from codebase.
"""

# ===========================================
# BATCH PROCESSING
# ===========================================
BATCH_TIMEOUT_SECONDS = 7200          # 2 hours - from batch_processor.py:343
BATCH_MAX_RETRIES = 3                 # from batch_processor.py
BATCH_CHUNK_SIZE = 500                # from batch_processor.py:531
BATCH_PARALLEL_WORKERS = 4            # default parallel jobs

# ===========================================
# TRANSLATION
# ===========================================
TRANSLATION_MAX_TOKENS = 4096         # max tokens per request
TRANSLATION_TEMPERATURE = 0.3         # LLM temperature
TRANSLATION_CHUNK_SIZE = 3000         # characters per chunk
TRANSLATION_OVERLAP = 50              # overlap between chunks
TRANSLATION_MAX_RETRIES = 5           # from translator.py:37
TRANSLATION_RETRY_DELAY = 3           # from translator.py:36

# ===========================================
# CACHE
# ===========================================
CACHE_TTL_SECONDS = 86400             # 24 hours
CACHE_MAX_SIZE_MB = 500               # max cache size
CACHE_CLEANUP_INTERVAL = 3600         # 1 hour

# ===========================================
# OCR
# ===========================================
OCR_DPI = 300                         # scan resolution
OCR_CONFIDENCE_THRESHOLD = 0.85       # min confidence
OCR_MAX_IMAGE_SIZE = 4096             # pixels
OCR_TIMEOUT_SECONDS = 60              # OCR processing timeout

# ===========================================
# VALIDATION
# ===========================================
VALIDATION_MIN_SCORE = 0.7            # minimum quality score
VALIDATION_MAX_LENGTH_RATIO = 1.5     # translated vs original
VALIDATION_MIN_LENGTH_RATIO = 0.5

# ===========================================
# API / SERVER
# ===========================================
API_RATE_LIMIT = 100                  # requests per minute
API_TIMEOUT_SECONDS = 30              # request timeout
WEBSOCKET_HEARTBEAT = 30              # seconds
DEFAULT_TIMEOUT = 300.0               # from parallel.py:79

# ===========================================
# JOB QUEUE
# ===========================================
JOB_DEFAULT_CHUNK_SIZE = 3000         # from job_queue.py:69
JOB_CONTEXT_WINDOW = 500              # from batch_processor.py:531
JOB_TIMEOUT_SECONDS = 7200            # 2 hours - from batch_processor.py:343

# ===========================================
# FILE HANDLING
# ===========================================
MAX_FILE_SIZE_MB = 50                 # upload limit
SUPPORTED_EXTENSIONS = [
    '.txt', '.docx', '.pdf', '.md',
    '.html', '.xlsx', '.pptx', '.srt'
]
OUTPUT_DIR = 'data/output'
TEMP_DIR = 'data/temp'
CACHE_DIR = 'data/cache'

# ===========================================
# LOGGING
# ===========================================
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'logs/translator.log'
LOG_MAX_SIZE_MB = 10
LOG_BACKUP_COUNT = 5

# ===========================================
# MATHPIX OCR
# ===========================================
MATHPIX_TIMEOUT = 30                  # from ocr/mathpix_client.py:57
MATHPIX_MAX_RETRIES = 3               # from ocr/mathpix_client.py:58
