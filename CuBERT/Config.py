# Config.py
# Configuration settings for the application.

# Model and tokenizer settings
# MODEL_NAME = "claudios/cubert-20210711-Python-512"
# TOKENIZER_NAME = "google/cubert-base"
MODEL_NAME=google/cubert-base
TOKENIZER_NAME=google/cubert-base

# Qdrant settings
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=ira-pem-logs
MAX_LENGTH=512