"""
项目安装配置文件。

定义项目的依赖关系和安装配置。
"""

from setuptools import find_packages, setup

setup(
    name="operate-log-client",
    version="0.1.2",
    packages=find_packages(),
    install_requires=["kafka-python>=2.0.2", "python-json-logger>=2.0.7", "pydantic>=2.0.0"],
    author="21epub",
    author_email="wangjian@21epub.com",
    description="A Python library for operation logging with Kafka support",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/21epub/python-operate-log-client",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
