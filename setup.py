from setuptools import setup

setup(
    name='hoot',
    version='0.1',
    package_dir={'': 'src'},
    py_modules=['hoot_cli', 'hoot'],
    install_requires=[
        'click==8.1.3',
        'requests==2.28.1',
        'attrs==22.1.0',
        'tqdm==4.64.0',
        'dacite==1.6.0',
        'pycocotools==2.0.5',
        'opencv-python==4.5.5.64'
    ],
    entry_points='''
        [console_scripts]
        hoot=src.hoot_cli:cli
    '''
)