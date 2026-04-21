from setuptools import setup, find_packages

setup(
    name="dot",
    version="0.1.0",
    description="Render images and video previews as Braille dot art in the terminal with color and animation support.",
    author="Arun Prakash Jana",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "Pillow"
    ],
    entry_points={
        'console_scripts': [
            'dot=dot.__main__:main',
        ],
    },
    python_requires='>=3.7',
)
