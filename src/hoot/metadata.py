import dataclasses
from typing import List, MutableSet, Dict
import datetime
from types import SimpleNamespace


class OcclusionTags(SimpleNamespace):
    solid = "solid"
    sparse = "sparse"
    semi_transparent = "semi_transparent"
    transparent = "transparent"
    absent = "absent"
    full_occlusion = "full_occlusion"
    similar_occluder = "similar_occluder"
    cut_by_frame = "cut_by_frame"
    partial_obj_occlusion = "partial_obj_occlusion"

class MotionTags(SimpleNamespace):
    blur = "blur"
    moving_occluder = "moving_occluder"
    parallax = "parallax"
    dynamic_camera_motion = "dynamic_camera_motion"

class TargetTags(SimpleNamespace):
    deformable = "deformable"
    self_propelled = "self_propelled"
    animate = "animate"


@dataclasses.dataclass
class OcclusionLevels:
    '''TODO: DOCUMENTATION'''
    frame_occlusion_level: float
    mean_target_occlusion_level: float
    median_target_occlusion_level: float
    

@dataclasses.dataclass
class AnnotatedFrameSet:
    '''Represents a video broken down into frames along with annotation-data and metadata'''
    id: int
    url: str
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
    classes: List[TargetClass]=dataclasses.field(default_factory=list)
