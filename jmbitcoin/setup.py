from setuptools import setup


setup(name='joinmarketbitcoin',
      version='0.9.10',
      description='Joinmarket client library for Bitcoin coinjoins',
      url='https://github.com/JoinMarket-Org/joinmarket-clientserver/tree/master/jmbitcoin',
      author='',
      author_email='',
      license='GPL',
      packages=['jmbitcoin'],
      python_requires='>=3.7',
      install_requires=['python-bitcointx==1.1.3'],
      zip_safe=False)
