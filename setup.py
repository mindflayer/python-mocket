import io
import subprocess
import sys

from setuptools import find_packages, os, setup

major, minor = sys.version_info[:2]


def list_requirements(dev=False):
    """ Try to use `requirements.txt` if available, generating a new one otherwise. """
    reqs_filename = "requirements.txt"
    if os.path.isfile(reqs_filename):
        with open(reqs_filename) as f:
            return f.readlines()[1:]
    command = "pipenv lock -r"
    if dev:
        command += " --dev"
    return (
        subprocess.check_output(command, shell=True).decode("ascii").split("\n")[1:-1]
    )


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
    packages=find_packages(exclude=exclude_packages),
    install_requires=list_requirements(),
    extras_require={
        "speedups": [
            'xxhash;platform_python_implementation=="CPython"',
            'xxhash-cffi;platform_python_implementation=="PyPy"',
        ],
        "tests": list_requirements(dev=True),
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
