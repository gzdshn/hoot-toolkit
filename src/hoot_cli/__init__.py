import dataclasses
import click
from pathlib import Path
import json

@click.group()
def cli():
    pass

from . import downloader
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
    metadata = downloader.download_metadata()

    for data_type in metadata['classData']:
        #make all data subfolders
        data_type_dir = dest.joinpath(data_type)
        data_type_dir.mkdir(exist_ok=True)

        for c in metadata['classes']:
            class_data_dir = data_type_dir.joinpath(c['name'])
            class_data_dir.mkdir(exist_ok=True)
            

from src.utils import package_folder, PackageInfo, validate_class_name
import shutil
import multiprocessing
from tqdm import tqdm
from typing import Optional
from src.hoot_cli.publisher import HootDataset, TargetClass, AnnotatedFrameSet

def archive_job(args) -> PackageInfo:
    (id, frame_set_dir, dest_frame_set_zip) = args
    return package_folder(id, frame_set_dir, dest_frame_set_zip)

@cli.command()
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Directory To Archive')
@click.option('--destination', '--dest', type=click.Path(), prompt='Destination directory')
@click.option('--version', type=str, prompt='Version: (eg 1.0)')
@click.option('--threads', type=int, default=None)
def make_archive(directory: str, destination: str, version: str, threads: Optional[int]=None):
    '''builds a complete hoot archive + metadata.json'''
    
    # handle directories
    dir = Path(directory)
    dest = Path(destination)
    if dest.exists():
        assert dest.is_dir()
        shutil.rmtree(dest)
    dest.mkdir(exist_ok=False)

    # create base dataset object
    dataset = HootDataset(
        version='1.0',
        change_log='Initial Release'
    )

    # iterate over all the class directories
    class_directories = [d for d in sorted(dir.iterdir()) if d.is_dir()]
    for class_dir in class_directories:
        assert validate_class_name(class_dir.name)
        target_class = TargetClass(class_dir.name)
        dataset.classes.append(target_class)
        dest_class_dir = dest.joinpath(class_dir.name)
        dest_class_dir.mkdir(exist_ok=False)

        # process each annotation-frame-set using archive_job on n threads (likely disk-speed bound)
        frame_sets = [d for d in sorted(class_dir.iterdir()) if d.is_dir()]
        arg_set = [(f.name, f, dest_class_dir.joinpath(f'{f.name}.zip')) for f in frame_sets]
        with multiprocessing.Pool(threads) as p:
            results = p.map(archive_job, arg_set)
            # results = tqdm(
                # results = p.map(archive_job, arg_set)#,
                # total=len(frame_sets),
            # )

        # assemble dataclasses
        for r in results:
            target_class.videos.append(AnnotatedFrameSet(r.id, f'/{class_dir.name}/{r.zip_path.name}', r.sha256, r.zip_size, r.zip_size))
        
    # render dataclasses to json
    with open(dest.joinpath('metadata.json'), 'w') as f:
        json.dump(dataclasses.asdict(dataset), fp=f, default=str)

from http.server import HTTPServer, SimpleHTTPRequestHandler
@cli.command()
@click.option('--directory', '--dir', type=click.Path(), prompt='Hoot Archive to Host')
def local_server(directory: str):

    class HootHTTPRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

    httpd = HTTPServer(('localhost', 8000), HootHTTPRequestHandler)
    httpd.serve_forever()
