import dataclasses
from typing import List, MutableSet, Dict
import datetime
from dacite import from_dict

@dataclasses.dataclass
class OcclusionLevels:
    '''TODO: DOCUMENTATION'''
    frame_occlusion_level: float
    mean_target_occlusion_level: float
    median_target_occlusion_level: float
    

@dataclasses.dataclass
class AnnotatedFrameSet:
    '''Represents a video broken down into frames along with annotation-data and metadata'''
    id: str
    path: str
    sha256: str
    download_size: int   #bytes (64-bit minimum)
    install_size: int    #bytes (64-bit minimum)
    test_split: bool
    occlusion_levels: OcclusionLevels
    tags: List[str]=dataclasses.field(default_factory=list)
    

@dataclasses.dataclass
class TargetClass:
    '''Represents a set of videos featuring a single type of tracked object (eg: banana, keyboard, animal)'''
    name: str
    videos: List[AnnotatedFrameSet]=dataclasses.field(default_factory=list)

@dataclasses.dataclass
class HootDataset:
    '''TODO: DOCUMENTATION'''
    version: str
    change_log: str
    date_created: datetime.date=dataclasses.field(default_factory=lambda: datetime.date.today())
    additional_files: List[str]=dataclasses.field(default_factory=list)
    classes: List[TargetClass]=dataclasses.field(default_factory=list)

import json
import datetime
def load_from_json(metadata_dict: dict) -> HootDataset:
    metadata_dict['date_created'] = datetime.datetime.strptime(metadata_dict['date_created'], '%Y-%m-%d').date()
    metadata = from_dict(data_class=HootDataset, data=metadata_dict)
    return metadata