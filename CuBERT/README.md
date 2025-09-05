# CuBERT Embedding Project

## Overview

This project uses the CuBERT model to generate embeddings for Python code and stores them in a Qdrant vector database.  
It relies on a custom tokenizer (`python_tokenizer.py`) from the [google-research/cubert](https://github.com/google-research/google-research/tree/master/cubert) repository.

## Folder Structure

Your repository should have the following structure:

```
repo-root/
│
├── CuBERT/
│   ├── python_tokenizer.py
│   ├── cubert/                # (optional, if needed by python_tokenizer.py)
│   ├── requirements.txt
│   └── .env                   # configuration file
│
├── CuBERT2.py                 # main script
└── README.md
```

- **CuBERT/python_tokenizer.py**: The custom tokenizer required for tokenizing Python code.
- **CuBERT/.env**: Configuration file for environment variables (model name, Qdrant settings, etc.).
- **CuBERT/requirements.txt**: List of Python dependencies.
- **CuBERT2.py**: Main script for generating embeddings and interacting with Qdrant.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r CuBERT/requirements.txt
   ```

2. **Configure environment variables:**
   - Edit `CuBERT/.env` to set your model and Qdrant settings.

3. **Run the script:**
   ```bash
   python CuBERT2.py
   ```

## Notes

- The script expects `python_tokenizer.py` to be inside the `CuBERT` folder.
- If `python_tokenizer.py` depends on other modules (e.g., `cubert_tokenizer.py`), ensure the `cubert` folder from the original repo is also present inside `CuBERT`.
- All paths are set up to work relative to the script location for portability.

## References

- [CuBERT Model Paper](https://arxiv.org/abs/2001.00059)
- [CuBERT Source Code](https://github.com/google-research/google-research/tree/master/cubert)
- [Qdrant Vector Database](https://qdrant.tech/)