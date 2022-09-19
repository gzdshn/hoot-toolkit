import json
from dataclasses import dataclass, field
from dacite import from_dict
from typing import List, Union
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


@dataclass
class Mask:
    '''TODO: DOCUMENTATION'''
    size: List[int]
    counts: str
    #TODO: convert the counts string to actual data
    # consider using attrs.attr
    # eg: counts: List[int] = attrs.attr.field(converter=my_counts_converter)

OptionalMask = Union[List, Mask]
@dataclass
class OcclusionMasks:
    '''TODO: DOCUMENTATION'''
    all: OptionalMask=field(default_factory=list)
    s: OptionalMask=field(default_factory=list)
    sp: OptionalMask=field(default_factory=list)
    st: OptionalMask=field(default_factory=list)
    t: OptionalMask=field(default_factory=list)

@dataclass
class FrameAttributes:
    '''TODO: DOCUMENTATION'''
    absent: bool
    full_occlusion: bool
    similar_occluder: bool
    cut_by_frame: bool
    partial_obj_occlusion: bool

RotatedBoundingBox = List[List[float]]
AxisAlignedBoundingBox = List[List[float]]
@dataclass
class Frame:
    '''TODO: DOCUMENTATION'''
    frame_id: int
    rot_bb: RotatedBoundingBox
    aa_bb: AxisAlignedBoundingBox
    occ_masks: OcclusionMasks
    attributes: FrameAttributes

@dataclass
class Video:
    '''TODO: DOCUMENTATION'''
    video_key: str
    frames: List[Frame]
    frame_occlusion_level: float
    median_target_occlusion_level: float
    mean_target_occlusion_level: float

def load_video_from_file(filepath) -> Video:
    '''TODO: DOCUMENTATION'''
    with open(filepath, 'r') as f:
        video_data = json.load(f)
    video = from_dict(data_class=Video, data=video_data)
    return video
