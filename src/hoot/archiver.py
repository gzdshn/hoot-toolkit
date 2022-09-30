import shutil
import multiprocessing
import dataclasses
from tqdm import tqdm
from typing import Optional, NamedTuple, Tuple, List
from pathlib import Path
import json
import pickle
import re
import os
from hoot.anno import load_video_from_file, OcclusionMasks, OcclusionTags, MotionTags

from hoot.utils import package_folder, validate_class_name, PackageInfo
from hoot.metadata import HootDataset, TargetClass, AnnotatedFrameSet, OcclusionLevels

allowed_file_types = {'.png', '.json', '.txt', '.info'}

class ArchiveArgs(NamedTuple):
    id: str
    frame_set_dir: str
    dest_frame_set_zip: str
    file_allow_list: str

@dataclasses.dataclass
class ArchiveResult:
    package_info: PackageInfo
    occlusion_levels: OcclusionLevels

def archive_job(args: ArchiveArgs) -> PackageInfo:
    '''Used to pass multiple arguments into a multiprocessing pool'''
    assert isinstance(args, ArchiveArgs)
    (id, frame_set_dir, dest_frame_set_zip, file_allow_list) = args
    return package_folder(id, frame_set_dir, dest_frame_set_zip, file_allow_list)

def make_archive(directory: str, destination: str, version: str, threads: Optional[int]=None, clean: bool=False):
    '''builds a complete Hoot archive + metadata.json
        If an archive operation should fail, make_archive will resume from the last successful
        zip operation. To accomplish this, make_archive will write a 'result_cache'
        file to the destination/*class folder for each video:

        eg .hoot.apple.001.e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.1827573571861812
                 id                                   sha265                          original_size

        Once all the zips and result_caches are built, make_archive will assemble all the metadata
    '''
    
    # handle directories
    dir = Path(directory)
    dest = Path(destination)
    #breakpoint()
    if dest.exists() and clean:
        shutil.rmtree(dest)
        dest.mkdir()
    else:
        dest.mkdir(exist_ok=True)


    # copy any files in the root directory (LICENSE.txt, train.txt, test.txt)
    hoot_files = [f for f in sorted(dir.iterdir()) if f.is_file()]
    test_video_keys = set()
    for f in hoot_files:
        if f.name.endswith('.txt') == False:
            continue
        # print(f, dest.joinpath(f.name))
        shutil.copy(f, dest.joinpath(f.name))
        if f.name == "test.txt":
            with open(f, "r") as fr:
                test_video_keys = set([k.strip() for k in fr.readlines()])
    assert len(test_video_keys) != 0

    # assemble all class directories
    class_directories = [d for d in sorted(dir.iterdir()) if d.is_dir()]

    # archive clss folders - MAJORITY OF CPU TIME HERE
    for class_dir in class_directories:
        assert validate_class_name(class_dir.name)
        dest_class_dir = dest.joinpath(class_dir.name)
        dest_class_dir.mkdir(exist_ok=True)

        frame_sets = [d for d in sorted(class_dir.iterdir()) if d.is_dir()]
        frame_set_caches = [c for c in sorted(class_dir.iterdir()) if c.name.startswith(f'.hoot.')]
        print(frame_set_caches)
        for frame_set in tqdm(frame_sets, desc='zipping videos'):
            
            #check frame_set_caches
            has_cache = False
            for c in frame_set_caches:
                if c.name.startswith(f'.hoot.{class_dir.name}.{frame_set.name}'):
                    has_cache = True
                    print(f'found cache file: {clean} {c}')
                    break
            if has_cache and clean == False:
                continue
            
            # zip package and write hidden '.hoot.*...' result cache file
            result = package_folder(frame_set.name, frame_set, dest_class_dir.joinpath(f'{frame_set.name}.zip'), allowed_file_types)
            dest_class_dir.joinpath(f'.hoot.{class_dir.name}.{frame_set.name}.{result.sha256}.{result.original_size}').touch()



    # compile metadata
    dataset = HootDataset(
        version='1.0',
        change_log='Initial Release'
    )

    for class_dir in class_directories:
        target_class = TargetClass(class_dir.name)
        dataset.classes.append(target_class)
        dest_class_dir = dest.joinpath(class_dir.name)

        frame_sets = [d for d in sorted(class_dir.iterdir()) if d.is_dir()]
        frame_set_caches = [c for c in sorted(dest_class_dir.iterdir()) if c.name.startswith(f'.hoot.{class_dir.name}.')]
        for frame_set in tqdm(frame_sets, desc='parsing anno.json'):  # TODO: could be multi-processed
            #fetch result cache
            result_cache = None
            for c in frame_set_caches:
                if c.name.startswith(f'.hoot.{class_dir.name}.{frame_set.name}'):
                    result_cache = c
                    break
            assert result_cache is not None, f'no result exists for frame_set {frame_set}' + f'\n{frame_set_caches}'
            
            #parse result cache - read id, sha256, size, zip_size
            match_result = re.match(r'\.hoot\..+\.(\d+)\.([0-9a-f]{64})\.(\d+)', result_cache.name)
            assert match_result is not None
            zip_path = dest_class_dir.joinpath(f'{frame_set.name}.zip')
            f_id = match_result.group(1)
            f_sha256 = match_result.group(2)
            f_size = int(match_result.group(3))
            f_zip_size = os.path.getsize(zip_path)

            # read anno.json
            in_test = class_dir.name + "-" + frame_set.name in test_video_keys
            video_data = load_video_from_file(frame_set, in_test=in_test)

            target_class.videos.append(AnnotatedFrameSet(
                id=f_id,
                path=f'{class_dir.name}/{zip_path.name}',
                sha256=f_sha256,
                download_size=f_zip_size,
                install_size=f_size,
                test_split=in_test,
                occlusion_levels=OcclusionLevels(
                    video_data.frame_occlusion_level,
                    video_data.mean_target_occlusion_level,
                    video_data.median_target_occlusion_level
                ),
                tags=video_data.occlusion_tags
            ))
    

    # render dataclasses to json
    with open(dest.joinpath('metadata.json'), 'w') as f:
        json.dump(dataclasses.asdict(dataset), fp=f, default=str, indent=2)

    print('Archive completed!')
