from setuptools import setup, find_packages

setup(
    name="filetags",
    version="0.2.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["Click", "lark"],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "mypy",
            "flake8",
        ]
    },
    entry_points={"console_scripts": ["ftag = filetags.src.cli:cli"]},
)
