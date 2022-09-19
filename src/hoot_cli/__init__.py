import dataclasses
import click
from pathlib import Path
import json

@click.group()
def cli():
    pass


## 'hoot make-archive' CLI command
from typing import Optional
from src.hoot.archiver import make_archive

@cli.command(name='make-archive')
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Directory To Archive')
@click.option('--destination', '--dest', type=click.Path(), prompt='Destination directory')
@click.option('--version', type=str, prompt='Version: (eg 1.0)')
@click.option('--threads', type=int, default=None)
@click.option('--clean', type=bool, default=False)
def launch_make_archive(directory: str, destination: str, version: str, threads: Optional[int]=None, clean: bool=False):
    make_archive(directory, destination, version, threads, clean)



## 'hoot download' CLI command
from src.downloader import Downloader
from src.utils import valid_version_regex

@cli.command()
@click.option('--destination', '--dest', type=click.Path(), prompt='File Destination')
@click.option('--quality', type=click.Choice(['ORIGINAL', 'REDUCED']), default='ORIGINAL')
@click.option('--class', '-c', 'classes', type=str, multiple=True, default=[])
def download(destination: Path, quality: str, classes: tuple):
    #log options
    print(f'YOU HAVE CHOSEN "{quality}", download destination is "{destination}", classes: {classes}')

    #create dest dir if it doesn't already exist
    dest = Path(destination)
    dest.mkdir(exist_ok=True)

    #fetch the latest metadata
    # metadata = downloader.download_metadata()

    # for data_type in metadata['classData']:
    #     #make all data subfolders
    #     data_type_dir = dest.joinpath(data_type)
    #     data_type_dir.mkdir(exist_ok=True)

    #     for c in metadata['classes']:
    #         class_data_dir = data_type_dir.joinpath(c['name'])
    #         class_data_dir.mkdir(exist_ok=True)
            


## 'hoot test-server' command for local DL testing
from src.test_server import start_local_server
@cli.command()
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Archive to Host')
@click.option('--port', type=int, default=8080)
def test_server(directory: str, port: int):
    start_local_server(directory, port)
