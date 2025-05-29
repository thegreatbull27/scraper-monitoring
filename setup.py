from setuptools import setup, find_packages

setup(
    name="scraper-monitoring",
    version="1.0.0",
    description="Centralized monitoring helper library for scrapers",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "prometheus-client>=0.16.0",
        "structlog>=23.1.0",
        "python-json-logger>=2.0.7",
        "requests>=2.31.0",
        "psutil>=5.9.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
