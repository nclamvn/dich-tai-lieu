#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Translator - Setup Configuration
Enables optional dependency groups for OCR features.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

# Optional dependencies for OCR
ocr_requirements = [
    "paddleocr>=2.7.0",
    "paddlepaddle>=2.5.0",  # CPU version
    "opencv-python-headless>=4.8.0",
]

mathpix_requirements = [
    "httpx>=0.26.0",  # Already in requirements.txt but listed here for clarity
]

setup(
    name="ai-translator",
    version="3.0.0",
    description="AI-powered document translator with STEM support and hybrid OCR",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Translator Team",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        # OCR features
        "ocr": ocr_requirements,
        "mathpix": mathpix_requirements,
        "ocr-full": ocr_requirements + mathpix_requirements,

        # Development dependencies
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
        ],

        # All optional features
        "all": ocr_requirements + mathpix_requirements,
    },
    entry_points={
        "console_scripts": [
            "translator=quick_translate:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Text Processing :: Linguistic",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="translation ai ocr stem paddle mathpix nlp",
)
