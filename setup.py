from setuptools import find_packages, setup
import ast
import re

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("graphene_djangorestframework/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )


with open("requirements/requirements-usage.txt", "r") as f:
    requirements = f.read().splitlines()


with open("requirements/requirements-testing.txt", "r") as f:
    test_requirements = f.read().splitlines()


setup(
    name="graphene-djangorestframework",
    version=version,
    description="Graphene Django Rest Framework Integration",
    long_description=open("README.rst").read(),
    url="https://github.com/HausMart/graphene-djangorestframework",
    author="Hilmar Hilmarsson",
    author_email="hilmar@hausmart.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    setup_requires=["pytest-runner"],
    keywords="",
    packages=find_packages(exclude=["tests"]),
    extras_require={"test": test_requirements},
    install_requires=requirements,
    tests_require=test_requirements,
    include_package_data=True,
    zip_safe=False,
    platforms="any",
)
