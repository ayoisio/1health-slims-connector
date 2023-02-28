import codecs
import os
import re

from setuptools import find_packages, setup

###############################################################################

NAME = "1health-integration-gateway"
PACKAGES = find_packages(where="src")
META_PATH = os.path.join("src", "onehealthintegration", "__init__.py")
KEYWORDS = ["1health", "integration", "gateway", "genohm", "slims"]
CLASSIFIERS = [
  "Development Status :: 4 - Beta",
  "Intended Audience :: Developers",
  "Natural Language :: English",
  "Operating System :: OS Independent",
  "Programming Language :: Python",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.9",
  "Programming Language :: Python :: Implementation :: CPython",
  "Programming Language :: Python :: Implementation :: PyPy",
  "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
]
INSTALL_REQUIRES = [
  "slims-python-api>=6.8.0,<6.9.0", 
  "numpy>=1.24.2,<1.25.0",
  "pandas>=1.5.3,<1.6.0",
  "python-dateutil>=2.8.2,<2.9.0",
  "pytz>=2022.7.1,<2022.8.0", 
  "requests>=2.28.2,<2.29.0",
  "urllib3>=1.26.14,<1.27.0"
]

###############################################################################

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
  """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
  with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
    return f.read()


META_FILE = read(META_PATH)


def find_meta(meta):
  """
    Extract __*meta*__ from META_FILE.
    """
  meta_match = re.search(
    r"^__{meta}__ = ['\"]([^'\"]*)['\"]".format(meta=meta), META_FILE, re.M)
  if meta_match:
    return meta_match.group(1)
  raise RuntimeError("Unable to find __{meta}__ string.".format(meta=meta))


VERSION = find_meta("version")
URI = find_meta("uri")
LONG = (read("README.md"))

if __name__ == "__main__":
  setup(
    name=NAME,
    description=find_meta("description"),
    license=find_meta("license"),
    url=URI,
    version=VERSION,
    author=find_meta("author"),
    author_email=find_meta("email"),
    maintainer=find_meta("author"),
    maintainer_email=find_meta("email"),
    keywords=KEYWORDS,
    long_description=LONG,
    long_description_content_type='text/markdown',
    packages=PACKAGES,
    package_dir={"": "src"},
    zip_safe=False,
    classifiers=CLASSIFIERS,
    install_requires=INSTALL_REQUIRES,
  )
