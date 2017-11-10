from distutils.core import setup
from setuptools import find_packages

setup(name='polyinterface',
      version='1.0.9',
      description='UDI Polyglot v2 Interface',
      url='https://github.com/Einstein42/udi-polyglot-interface',
      author='James Milne',
      author_email='milne.james@gmail.com',
      license='MIT',
      packages=find_packages(),
      install_requires=[
	"paho-mqtt",
	"python-dotenv",
        ],
      python_requires='~=3.5',
      zip_safe=False,
          # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How Mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ])
