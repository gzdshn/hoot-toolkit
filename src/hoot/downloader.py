
# full datasets are broken into different versions and image_qualities
# Each combination is given a separate URL
# eg.   version = 1.0, 1.1, 1.2, 2.0
#       image_quality = HD, HD
#       host_url = https://data.hootbenchmark.org/v1_1/HD/, https://downloads.host.com/v2_0/UHD/

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

class Downloader:
    def __init__(self, host_url: str) -> None:
        self.host_url = host_url

    def download_metadata(self) -> dict:
        #fetch metadata json
        response = requests.get(self.host_url + '/metadata.json')
        assert response.status_code == HTTPStatus.OK
        assert response.headers['Content-Type'] == 'application/json'
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
            assert response.status_code == HTTPStatus.OK
            assert response.headers['Content-Type'] == 'text/plain'
            with open(dest.joinpath(f), 'w') as fw:
                fw.write(response.text)

def download_archives(destination: Path, extract: bool=False, clean: bool=False, test_only: bool=False, remove_archives: bool=False):
    #create dest dir if it doesn't already exist
    dest = Path(destination)
    dest.mkdir(exist_ok=True)

    host_url = 'http://localhost:8080/'
    dl = Downloader(host_url)
    #fetch the latest metadata
    metadata = load_from_json(dl.download_metadata())

    ## download license, test.txt, train.txt
    dl.download_additional_files(metadata.additional_files, dest)

    ## Collect videos to download
    to_download = []
    for c in metadata.classes:
        class_dir = dest.joinpath(c.name)
        class_dir.mkdir(exist_ok=True)
        for v in c.videos:
            if test_only: ## doesn't support flags
                if v.test_split:
                    to_download.append([class_dir, v])
            else:
                ## ADD ANY DOWNLOAD FILTERS HERE ##
                ## Use v['tags] and v['occlusion_levels']
                ## Only videos with solid occ, similar occ. etc... 
                to_download.append([class_dir, v])

    ## Download videos
    for class_dir, v in tqdm(to_download, desc = "Downloading videos..."):
        dl.download_url(v.path, class_dir, v.download_size, clean)
    
    ## Extract zip archives
    if extract:
        for class_dir, v in tqdm(to_download, desc = "Extracting zip files..."):
            v_zip_path = v.path
            zip_path = dest.joinpath(v_zip_path)
            # breakpoint()
            v_folder = class_dir.joinpath(v.id)
            v_folder.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(v_folder)

            if remove_archives and os.path.isfile(zip_path):
                os.remove(zip_path)