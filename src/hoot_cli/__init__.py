import dataclasses
import click
from pathlib import Path
import json

@click.group()
def cli():
    pass


## 'hoot make-archive' CLI command
from typing import Optional
from hoot.archiver import make_archive

@cli.command(name='make-archive')
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Directory To Archive')
@click.option('--destination', '--dest', type=click.Path(), prompt='Destination directory')
@click.option('--version', type=str, prompt='Version: (eg 1.0)')
@click.option('--threads', type=int, default=None)
@click.option('--clean', type=bool, default=False, is_flag=True)
def launch_make_archive(directory: str, destination: str, version: str, threads: Optional[int]=None, clean: bool=False):
    make_archive(directory, destination, version, threads, clean)

## 'hoot download' CLI command
from hoot.downloader import download_archives
RELEASED_VERSIONS = ["v1_0-HD", "v1_0-UHD"]

@cli.command(name="download")
@click.option('--destination', '--dest', type=click.Path(), prompt='File Destination')
@click.option('--version', type=click.Choice(RELEASED_VERSIONS), prompt="Dataset Version")
@click.option('--extract', type=bool, default=False, is_flag=True)
@click.option('--clean', type=bool, default=False, is_flag=True)
@click.option('--test-only', type=bool, default=False, is_flag=True)
@click.option('--remove-archives', type=bool, default=False, is_flag=True)
def download(destination: Path, version: str, extract: bool=False, clean: bool=False, test_only: bool=False, remove_archives: bool=False):
    download_archives(destination, version, extract, clean, test_only, remove_archives)

## 'hoot visualize' command for quickly visualizing videos
from hoot.visualizer import visualize_videos

@cli.command(name='visualize')
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Directory')
@click.option('--output', '--dest', type=click.Path(), default=None)
@click.option('--video', type=str, default=None)
def launch_visualizer(directory: str, output: Optional[str], video: Optional[str]):
    visualize_videos(directory, output, video)           

## 'hoot test-server' command for local DL testing
from hoot.test_server import start_local_server
@cli.command(name='test-server')
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Archive to Host')
@click.option('--port', type=int, default=8080)
def test_server(directory: str, port: int):
    start_local_server(directory, port)
