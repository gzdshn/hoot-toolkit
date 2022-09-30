import re

valid_class_name_regex = re.compile(r'([a-z]+_)*[a-z]+')
def validate_class_name(class_name: str) -> bool:
    '''validtor used to ensure class names are letters and underscores only'''
    result = valid_class_name_regex.match(class_name)
    if result is not None:
        return True
    return False

valid_version_regex = re.compile(r'[vV]?(\d+)\.(\d+)')
def validate_version(version: str) -> bool:
    '''validtor used to ensure version numbers are correct'''
    result = valid_version_regex.match(version)
    if result is not None:
        return True
    return False

import hashlib
import zipfile
import os
from pathlib import Path
import zipfile
from typing import NamedTuple, List

class PackageInfo(NamedTuple):
    id: str
    original_size: int
    sha256: str
    zip_path: str

def package_folder(id: str, directory: Path, zip_output: Path, allowed_file_types: List[str]) -> PackageInfo:
    '''
    Walks a directory alphabetically and builds a hash digest + zip archive
    Hash digest includes utf-8 encoded filenames (eg. "0001.png")
    '''

    data_size = 0
    data_hash = hashlib.sha256()
    data_zip = zipfile.ZipFile(zip_output, mode='w')

    for root, dirs, files in os.walk(directory, topdown=True, followlinks=False):
        #breakpoint()
        for name in sorted(files):
            #print(os.path.splitext(name), allowed_file_types)
            if os.path.splitext(name)[1] not in allowed_file_types:
                continue

            #include the file name in the hash
            data_hash.update(name.encode('utf-8'))

            # hash and write to zip using the same read stream
            z_info = zipfile.ZipInfo.from_file(Path(root) / name, name)
            with open(os.path.join(root, name), "rb") as f, data_zip.open(z_info, mode='w') as zip_stream:
                for chunk in iter(lambda: f.read(16384), b""):
                    data_hash.update(chunk)
                    data_size += len(chunk)
                    zip_stream.write(chunk)

            # print(os.path.join(root, name))
            #break #TODO: returning after 1 file for quick testing

    return PackageInfo(id, data_size, data_hash.hexdigest(), zip_output)
