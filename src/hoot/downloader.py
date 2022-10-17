
# Full datasets are broken into different versions and image_qualities
# Each combination is given a separate URL
# eg.   version = 1.0, 1.1, 1.2, 2.0
#       image_quality = HD, UHD
#       host_url = https://data.hootbenchmark.org/HOOT_v1/HD/

import requests
import json
from http import HTTPStatus
from pathlib import Path
import zipfile
from tqdm import tqdm
import os
import shutil
from hoot.metadata import load_from_json
from typing import List

## Downloader class 
class Downloader:
    def __init__(self, host_url: str) -> None:
        self.host_url = host_url

    def download_metadata(self) -> dict:
        #fetch metadata json
        breakpoint()
        response = requests.get(self.host_url + 'metadata.json')
        assert response.status_code == HTTPStatus.OK, f'Service returned error {response.status_code}'
        return response.json()

    def download_url(self, url: str, directory: Path, zip_size: int, clean):
        
        local_filepath = directory.joinpath(Path(url).name)
        tmp_local_filepath = str(local_filepath)+".tmp"
        ## If not clean, skip if file already exists
        ## Sha would have been checked before movinf from .tmp
        if not clean and os.path.exists(local_filepath):
            return local_filepath

        # NOTE the stream=True parameter below
        with requests.get(self.host_url + url, stream=True) as r:
            r.raise_for_status()
            with open(tmp_local_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    #if chunk: 
                    f.write(chunk)
        
        ## Check with zip size, if correct, move from .tmp
        new_zip_size = os.path.getsize(tmp_local_filepath)
        if new_zip_size == zip_size:
            shutil.move(tmp_local_filepath, local_filepath)

        return local_filepath

    def download_additional_files(self, files: List[str], dest: Path):
        for f in files:
            response = requests.get(self.host_url + f)
            assert response.status_code == HTTPStatus.OK, f'Service returned error {response.status_code}'
            with open(dest.joinpath(f), 'w') as fw:
                fw.write(response.text)

def download_archives(destination: Path, version: str, extract: bool=False, clean: bool=False, test_only: bool=False, remove_archives: bool=False):
    ## Create dest dir if it doesn't already exist
    dest = Path(destination)
    dest.mkdir(exist_ok=True)

    base_url = 'http://ilab.usc.edu/hoot/'
    version_folder, quality = version.split("-")
    download_url = f'{base_url}{version_folder}/{quality}/'
    dl = Downloader(download_url)
    ## Fetch the latest metadata
    metadata = load_from_json(dl.download_metadata())

    ## Download license, test.txt, train.txt
    dl.download_additional_files(metadata.additional_files, dest)

    ## Collect videos to download
    to_download = []
    for c in metadata.classes:
        class_dir = dest.joinpath(c.name)
        class_dir.mkdir(exist_ok=True)
        for v in c.videos:
            if test_only:
                if v.test_split:
                    to_download.append([class_dir, v])
            else:
                ## ADD ANY DOWNLOAD FILTERS HERE ##
                ## Use v.occlusion_tags, v.frame_occlusion_level etc.
                ## Filter downloaded videos with an if statement like:
                ## if "solid" in v.occlusion_tags:
                to_download.append([class_dir, v])

    ## Download videos
    ## If clean is set, the video is skipped if it's already downloaded
    for class_dir, v in tqdm(to_download, desc = "Downloading videos..."):
        dl.download_url(v.path, class_dir, v.download_size, clean)
    
    ## Extract zip archives
    if extract:
        for class_dir, v in tqdm(to_download, desc = "Extracting zip files..."):
            ## Setup paths
            v_zip_path = v.path
            zip_path = dest.joinpath(v_zip_path)
            v_folder = class_dir.joinpath(v.id)
            v_folder.mkdir(exist_ok=True)
            
            ## Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(v_folder)

            ## If remove_archives is set, delete the zip file from the class folder
            if remove_archives and os.path.isfile(zip_path):
                os.remove(zip_path)