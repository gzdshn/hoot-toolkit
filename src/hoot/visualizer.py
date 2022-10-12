import multiprocessing
from tqdm import tqdm
from typing import Optional
from pathlib import Path
import json
import pickle
import os
from hoot.anno import load_video_from_file, Video
import cv2
import numpy as np
import sys

COLORS = {"tgt_poly": (0, 255, 0), 
          "tgt_aa_bb": (0, 153, 0),
          "tgt_rot_bb": (102, 255, 178),
          "occ" : (192, 192, 192),
          "s": (0, 0, 204), 
          "sp": (0, 128, 255),
          "st": (255 ,102, 178),
          "t": (255 ,178, 102)
         }

## Main driver code to visualize all videos, if a specific video is given, it skips all the rest
def visualize_videos(data_directory: str, output_directory: Optional[str], video_key: Optional[str]) -> None:

    # Handle directories
    datapath = Path(data_directory)
    outpath = Path(output_directory) if output_directory else None
    if outpath:
        outpath.mkdir(exist_ok=True)

    # Assemble all class directories
    class_directories = [d for d in sorted(datapath.iterdir()) if d.is_dir()]

    videos = []
    for class_dir in tqdm(class_directories, desc='loading annotations per obj class'):
        video_dirs = [d for d in sorted(class_dir.iterdir()) if d.is_dir()]
        
        for video_path in video_dirs:
            if video_key and video_key != class_dir.name + "-" + video_path.name:
                continue
            video_anno_json = video_path.joinpath('anno.json')
            video_meta_json = video_path.joinpath('meta.info')
            video_data = load_video_from_file(video_path, None, video_anno_json, video_meta_json)
            videos.append(video_data)

    # Visualize boxes and masks on either given video or all videos
    for video_data in videos:
        if video_key:
            if video_data.video_key == video_key:
                ## Visualize given video
                visualize_video(video_data, outpath)
                break
        else:
            ## Visualize all
            visualize_video(video_data, outpath)
        
## Function to visualize a single video
def visualize_video(video_data: Video, output_folder: Optional[Path]=None, with_mask: Optional[str]="multi") -> None:

    for idx, frame in enumerate(video_data.frames):
        img_data = cv2.imread(str(frame.frame_path))

        ## If object out of frame, no annotations to plot
        if frame.attributes.absent:
            vid_data = img_data
        else:
            ## Plot the rotated bb
            cv2.polylines(img_data, [np.array(frame.rot_bb, np.int32)], True, COLORS["tgt_rot_bb"], thickness=5)

            ## Plot the binary occlusion masks
            if with_mask == "binary":
                if frame.occ_masks.all:       
                    occ_mask_mat = frame.occ_masks.all.mask
                    occ_mask = cv2.cvtColor(occ_mask_mat,cv2.COLOR_GRAY2BGR)
                    occ_idxs = (occ_mask == [1,1,1]).all(-1)
                    img_data[occ_idxs] = COLORS["occ"]
                vis_data = img_data
            elif with_mask == "multi": 
                ## This order is of some importance
                ## Why? Cause a solid occluder in fact trumps all the rest
                occ_types_list = ["t","st","sp","s"]
                
                for occ_type, occ_mask_obj in frame.occ_masks.get_masks(occ_types_list):
                    if occ_mask_obj:
                        occ_mask = cv2.cvtColor(occ_mask_obj.mask,cv2.COLOR_GRAY2BGR)
                        occ_idxs = (occ_mask == [1,1,1]).all(-1)
                        img_data[occ_idxs] = COLORS[occ_type]
                vis_data = img_data
            else:
                vis_data = img_data
    
        ## Resize cause original images are BIG
        h,w = img_data.shape[:2]
        if h>1000:
            vis_data = cv2.resize(vis_data,(int(w*0.5),int(h*0.5)), interpolation = cv2.INTER_AREA)
        
        if output_folder:
            video_key = video_data.video_key
            output_video_folder = output_folder.joinpath(video_key)
            file_name = os.path.basename(frame.frame_path)
            output_path = output_video_folder.joinpath(file_name)
            output_video_folder.mkdir(exist_ok=True)
            cv2.imwrite(str(output_path),vis_data)
        
        cv2.imshow("video",vis_data)
        cv2.waitKey(2)
    cv2.destroyAllWindows()
            