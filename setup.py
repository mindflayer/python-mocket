import io
import os
import sys

from setuptools import find_packages, setup

os.environ.setdefault("PIPENV_SKIP_LOCK", "1")

major, minor = sys.version_info[:2]

install_requires = [
    line
    for line in io.open(
        os.path.join(os.path.dirname(__file__), "requirements.txt")
    ).readlines()
    if not line.startswith("-i")
]

pook_requires = ("pook>=0.2.1",)
exclude_packages = ("tests", "tests.*")


def read_version(package):
    init_path = os.path.join(package, "__init__.py")
    with io.open(init_path, "r") as fd:
        for line in fd:
            if line.startswith("__version__ = "):
                return line.split()[-1].strip().strip('"')


setup(
    name="mocket",
    version=read_version("mocket"),
    author="Giorgio Salluzzo",
    author_email="giorgio.salluzzo@gmail.com",
    url="https://github.com/mindflayer/python-mocket",
    description="Socket Mock Framework - for all kinds of socket animals, web-clients included - \
        with gevent/asyncio/SSL support",
    long_description=io.open("README.rst", encoding="utf-8").read(),
    long_description_content_type="text/x-rst",
    packages=find_packages(exclude=exclude_packages),
    install_requires=install_requires,
    setup_requires=[],
    extras_require={
        "speedups": [
            'xxhash;platform_python_implementation=="CPython"',
            'xxhash-cffi;platform_python_implementation=="PyPy"',
        ],
        "dev": [],
        "pook": pook_requires,  # plugins version supporting mocket.plugins.pook.MocketEngine
    },
    test_suite="runtests.runtests",
    license="BSD",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: BSD License",
    ],
)
