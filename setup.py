from setuptools import setup, find_packages

setup(
    name="filetags",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["Click", "lark"],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "mypy",
        ]
    },
    entry_points={"console_scripts": ["ftag = filetags.src.new_cli:cli"]},
)
