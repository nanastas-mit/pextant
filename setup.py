from distutils.core import setup

setup(
    name='pextant',
    packages=['pextant'],
    version='2.0',
    author='Johannes Norheim',
    author_email='norheim@mit.edu',
    url='http://pypi.python.org/pypi/pextant/',
    download_url='https://github.com/norheim/pextant/archive/1.0.tar.gz',
    keywords=['testing', 'logging', 'example'], # arbitrary keywords
    classifiers=[],
    license='The MIT License: http://www.opensource.org/licenses/mit-license.php',
    description='Python version of SEXTANT pathfinding tool',
    long_description=open('README.txt').read(),
    python_requires='>=3.7',
    install_requires=[
        'jupyter',
        'numpy',
        'gdal',
        'pyproj',
        'shapely',
        'pandas',
        'bokeh',
        'cmake',
        'scikit-image'
    ],
)
