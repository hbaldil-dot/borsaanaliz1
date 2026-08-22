from setuptools import setup, find_packages
import sys

# Python versiyon kontrolü
if sys.version_info < (3, 12):
    sys.exit("Python 3.12+ required")

setup(
    name="borsaanaliz1",
    version="2.0.0",
    packages=find_packages(include=['app', 'app.*']),
    install_requires=[
        "fastapi>=0.115.6",
        "uvicorn[standard]>=0.34.0",
        "pymongo>=4.10.1",
        "pandas>=2.2.3",
        "numpy>=1.26.4",
        "python-dotenv>=1.0.1",
        "pydantic>=2.10.4",
        "yfinance>=0.2.41",
        "ta>=0.10.2",
        "requests>=2.32.3",
        "beautifulsoup4>=4.12.3",
        "lxml>=5.3.0",
        "python-multipart>=0.0.20",
        "aiofiles>=24.1.0",
        "pytz>=2024.2"
    ],
    python_requires=">=3.12,<3.13",
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
