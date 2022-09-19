from setuptools import setup

setup(
    name='hoot',
    version='0.1',
    py_modules=['src/hoot_cli', 'src/hoot'],
    install_requires=[
        'click==8.1.3',
        'requests==2.28.0',
        'tqdm==4.64.0',
        'dacite==1.6.0'
    ],
    entry_points='''
        [console_scripts]
        hoot=src.hoot_cli:cli
    '''
)