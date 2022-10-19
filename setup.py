from setuptools import setup, find_packages

setup(
    name='hoot',
    version='1.0',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        'click>=8.0.0',
        'requests>=2.27.0',
        'tqdm==4.64.0',
        'dacite==1.6.0',
        'pycocotools==2.0.5',
        'opencv-python==4.5.5.*'
    ],
    entry_points='''
        [console_scripts]
        hoot=hoot_cli:cli
    '''
)