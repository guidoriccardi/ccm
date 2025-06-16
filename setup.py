from setuptools import setup, find_packages

setup(
    name='ccm',
    version='0.1',
    description='CPU usage and CO2 emission tracker decorator',
    author='Guido Riccardi',
    packages=find_packages(),
    install_requires=['psutil'],
    python_requires='>=3.6',
)
