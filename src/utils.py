import re

valid_class_name = re.compile(r'([a-z]+_)*[a-z]+')
def validate_class_name(class_name: str) -> bool:
    result = valid_class_name.match(class_name)
    if result is not None:
        return True
    return False


import hashlib
import zipfile
import os
import shutil
from pathlib import Path
import zipfile
from typing import NamedTuple

class PackageInfo(NamedTuple):
    id: str
    size: int
    sha256: str
    zip_size: int
    zip_path: str

def package_folder(id: str, directory: Path, zip_output: Path) -> PackageInfo:
    # walk directory alphabetically, build a hash on the data in each file (ignore file attr)
    # MUST BE DETERMINISTIC - walk in alphabetic order; hash only filename+data
    print(zip_output.parent.joinpath(zip_output.stem), directory)
    data_size = 0
    data_hash = hashlib.sha256()
    data_zip = zipfile.ZipFile(zip_output, mode='w')

    # hash and write to zip using the same read stream
    for root, dirs, files in os.walk(directory, topdown=True, followlinks=False):
        for name in files:
            z_info = zipfile.ZipInfo.from_file(Path(root) / name, name)
            with open(os.path.join(root, name), "rb") as f, data_zip.open(z_info, mode='w') as zip_stream:
                for chunk in iter(lambda: f.read(16384), b""):
                    data_hash.update(chunk)
                    data_size += len(chunk)
                    zip_stream.write(chunk)
            print(os.path.join(root, name))
            break
    print(data_size, data_hash.hexdigest())
    return PackageInfo(id, data_size, data_hash.hexdigest(), os.path.getsize(zip_output), zip_output)