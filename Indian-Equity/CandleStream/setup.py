from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '1.0.1'
DESCRIPTION = 'Fastes historical candle data Loader'
LONG_DESCRIPTION = 'A package that allows to fetch the historical data in fastest way with its own cache system'

setup(
    name="Candlestream",
    version=VERSION,
    author="Sachin Sachan",
    author_email="<sachinsachan722@gmail.com>",
    description=DESCRIPTION,
    long_description = "Fastest historical candle data loader with caching system.",
    long_description_content_type = "text/plain",
    packages=find_packages(),
    url="https://github.com/sac-1999/CandleStream",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
    install_requires=[
        "logzero==1.7.0",
        "mplfinance==0.12.10b0",
        "pandas_ta==0.3.14b0",
        "pyotp==2.8.0",
        "smartapi-python==1.4.8",
        "appdirs==1.4.4",
        "websocket==0.2.1",
        "python-dotenv",
        "pandas",
    ],
)