## Annotation format for HOOT
## Loads anno.json files automatically into given annotation classes
## Provides tools to load binary masks from encoded COCO RLE format

import json
from dataclasses import dataclass, field
from dacite import from_dict
from typing import List, Union
from types import SimpleNamespace
from typing import List, Union, Optional, Tuple
from pycocotools import mask
import attrs
import numpy as np
from pathlib import Path

## Occlusion tags class, provides a mapping from attr to str
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

## Motion tags class, provides a mapping from attr to str
class MotionTags(SimpleNamespace):
    blur = "blur"
    moving_occluder = "moving_occluder"
    parallax = "parallax"
    dynamic = "dynamic"
    camera_motion = "camera_motion"

## Target tags class, provides a mapping from attr to str
class TargetTags(SimpleNamespace):
    deformable = "deformable"
    self_propelled = "self_propelled"
    animate = "animate"

## Mask class that holds a COCO RLE encoded mask
## Provides a property to return the decoded binary mask
@dataclass
class Mask:
    '''TODO: DOCUMENTATION'''
    size: List[int]
    counts: str

    @property
    def mask(self) -> np.ndarray:
        counts_bytes = bytes.fromhex(self.counts)
        mask_mat = mask.decode({"size": self.size, "counts":counts_bytes})
        return mask_mat

## Occlusion Masks class that holds all occlusion masks for a frame
## If a certain type of occluder does not exists for the frame, stores empty list
## Provides get_masks fn to return masks for a given list of occ. types
OptionalMask = Union[List, Mask]
@dataclass
class OcclusionMasks:
    '''TODO: DOCUMENTATION'''
    all: OptionalMask=field(default_factory=list)
    s: OptionalMask=field(default_factory=list)
    sp: OptionalMask=field(default_factory=list)
    st: OptionalMask=field(default_factory=list)
    t: OptionalMask=field(default_factory=list)

    def get_masks(self, occ_types: Optional[List[str]]=None):
        if occ_types is None:
            occ_types = ["all", "s", "sp", "st", "t"]
        for occ_type in occ_types:
            if occ_type == 'all':
                yield (occ_type, self.all)
            elif occ_type == 's':
                yield (occ_type, self.s)
            elif occ_type == 'sp':
                yield (occ_type, self.sp)
            elif occ_type == 'st':
                yield (occ_type, self.st)
            elif occ_type == 't':
                yield (occ_type, self.t)
            else:
                assert False, 'unrecognized occ_type'


## Frame Attributes class which holds frame-level occlusion attributes 
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
    frame_path: str ## "path/to/hoot/class/video/padded_frame_id.png"
    rot_bb: RotatedBoundingBox
    aa_bb: AxisAlignedBoundingBox
    occ_masks: OcclusionMasks
    attributes: FrameAttributes

@dataclass
class Video:
    '''TODO: DOCUMENTATION'''
    video_key: str
    video_path: str
    frames: List[Frame]
    frame_occlusion_level: float
    median_target_occlusion_level: float
    mean_target_occlusion_level: float
    #from metadata.info
    height: int
    width: int
    motion_tags: List[str]
    target_tags: List[str]
    
    def __post_init__(self):
        self.frames.sort(key=lambda f: f.frame_id)

    @property
    def occlusion_tags(self) -> List[str]:
        video_tags = set()
        for frame in self.frames:
            if type(frame.occ_masks.s) != list:
                video_tags.add(OcclusionTags.solid)
            if type(frame.occ_masks.sp) != list:
                video_tags.add(OcclusionTags.sparse)
            if type(frame.occ_masks.st) != list:
                video_tags.add(OcclusionTags.semi_transparent)
            if type(frame.occ_masks.t) != list:
                video_tags.add(OcclusionTags.transparent)

            if frame.attributes.absent:
                video_tags.add(OcclusionTags.absent)
            if frame.attributes.full_occlusion:
                video_tags.add(OcclusionTags.full_occlusion)
            if frame.attributes.similar_occluder:
                video_tags.add(OcclusionTags.similar_occluder)
            if frame.attributes.cut_by_frame:
                video_tags.add(OcclusionTags.cut_by_frame)
            if frame.attributes.partial_obj_occlusion:
                video_tags.add(OcclusionTags.partial_obj_occlusion)
        return list(video_tags)


def load_video_from_file(videopath: Path, in_test=None, annopath=None, metapath=None) -> Video:
    '''TODO: DOCUMENTATION'''
    if annopath is None:
        annopath = videopath.joinpath('anno.json')
        assert annopath.exists()
    if metapath is None:
        metapath = videopath.joinpath('meta.info')
        assert metapath.exists()
    print(annopath)
    # Edit annotation dict to add path and test video info
    with open(annopath, 'r') as f:
        anno_data = json.load(f)
    anno_data['video_path'] = str(videopath)
    anno_data['in_test'] = in_test
    for f in anno_data['frames']:
        frame_id = int(f['frame_id'])
        f['frame_path'] = str(videopath.joinpath(f'{frame_id:06}.png'))

    # Load metadata.info json
    with open(metapath, 'r') as f:
        meta_data = json.load(f)
    motion_tags, target_tags = load_tags_from_metadata(meta_data)
    anno_data['height'] = int(meta_data['height'])
    anno_data['width'] = int(meta_data['width'])
    anno_data['motion_tags'] = motion_tags
    anno_data['target_tags'] = target_tags

    # Load rest o the annotations from the anno.json file
    video = from_dict(data_class=Video, data=anno_data)
    return video

def load_tags_from_metadata(meta_data) -> Tuple[List[str], List[str]]:
    motion_tags = []
    target_tags = []

    if meta_data['video_tags'][MotionTags.blur]:
        motion_tags.append(MotionTags.blur)
    if meta_data['video_tags'][MotionTags.moving_occluder]:
        motion_tags.append(MotionTags.moving_occluder)
    if meta_data['video_tags'][MotionTags.parallax]:
        motion_tags.append(MotionTags.parallax)
    if meta_data['video_tags'][MotionTags.dynamic]:
        motion_tags.append(MotionTags.dynamic)
    if meta_data['video_tags'][MotionTags.camera_motion]:
        motion_tags.append(MotionTags.camera_motion)
    
    if meta_data['video_tags'][TargetTags.animate]:
        target_tags.append(TargetTags.animate)
    if meta_data['video_tags'][TargetTags.deformable]:
        target_tags.append(TargetTags.deformable)
    if meta_data['video_tags'][TargetTags.self_propelled]:
        target_tags.append(TargetTags.self_propelled)

    return (motion_tags, target_tags)