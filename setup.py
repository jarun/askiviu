import re
from pathlib import Path

from setuptools import setup

README = Path(__file__).parent / "README.md"
DOTZ = Path(__file__).parent / "dotz.py"

version = re.search(
    r'^_VERSION_\s*=\s*[\"\']([^\"\']+)[\"\']',
    DOTZ.read_text(encoding="utf-8"),
    re.MULTILINE,
).group(1)

setup(
    name="dotz",
    version=version,
    description="Render images and video previews as Braille art in the terminal with color and animation support.",
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Arun Prakash Jana",
    license="MIT",
    url="https://github.com/jarun/dotz",
    project_urls={
        "Homepage": "https://github.com/jarun/dotz",
        "Repository": "https://github.com/jarun/dotz",
        "Issues": "https://github.com/jarun/dotz/issues",
    },
    py_modules=["dotz"],
    install_requires=[
        "numpy>=1.20",
        "Pillow>=8.0",
    ],
    entry_points={
        "console_scripts": [
            "dotz=dotz:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console :: Curses",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Terminals",
    ],
    keywords="terminal image-viewer braille curses gif video ffmpeg",
)
