from pathlib import Path
from typing import Optional, Tuple, List
import multiprocessing
import tqdm
import pickle
import os
from hoot.anno import *
from hoot.ope_benchmark import OPE_Benchmark
  
def evaluate_results(hoot_dir, results_dir, output_dir, trackers, clear_cache, attributes, test_only) -> None:

    hoot_dir, results_dir = Path(hoot_dir), Path(results_dir)
    if output_dir:
        output_dir = Path(output_dir)

    ## Get tracker list if given
    if trackers:
        tracker_list = trackers.strip().split(",")
    else:
        tracker_list = [f.name for f in results_dir.iterdir() if f.is_dir()]
    
    ## Check if we have any attributes filter
    attribute_filters = [None] ## Evaluate all
    if attributes:
        attribute_filters = attributes.strip().split(",")

    ## If only evaluating on test videos, set test file path
    test_file = None
    if test_only:
        test_file = hoot_dir.joinpath("test.txt")

    ## Check if annotations are saved in a pickle already
    ## Avoids re-loading all of them
    pkl_file = hoot_dir.joinpath("annotations_for_eval.pkl")

    if not clear_cache and pkl_file.exists():
        print("Loading annotations from file...")
        with open(str(pkl_file),"rb") as f:
            videos_all = pickle.load(f)
    else:
        ## Collect paths to all video folders we want to process & their annotations
        videos2load = [] # List of Tuple(path_to_video, path_to_anno, path_to_meta)
        for class_name in filter(Path.is_dir, hoot_dir.iterdir()):
            class_folder = hoot_dir.joinpath(class_name.name)
            for video_name in filter(Path.is_dir, class_folder.iterdir()):
                video_path = hoot_dir.joinpath(class_name.name, video_name.name)
                load_job = LoadVideo(video_path, video_path.joinpath("anno.json"), video_path.joinpath("meta.info"))
                videos2load.append(load_job)

        pool = multiprocessing.Pool()
        loaded_videos = tqdm.tqdm(pool.imap(LoadVideo.run, videos2load),total=len(videos2load))
        pool.close()

        videos_all = [vid.video_obj for vid in loaded_videos]
        with open(str(pkl_file),"wb") as f:
            pickle.dump(videos_all,f)
    
    ## Evaluate for each filter type given and write to output
    for t in attribute_filters:
        
        videos = filter_videos(videos_all, test_file, filter_type=t)
        
        ## OPE Benchmark Results
        eval_benchmark = OPE_Benchmark(videos, results_dir)
        print("computing precision...")
        precision_results = eval_benchmark.eval_precision(tracker_list)
        print("computing normalized precision...")
        norm_precision_results = eval_benchmark.eval_norm_precision(tracker_list)
        print("computing success...")
        success_results = eval_benchmark.eval_success(tracker_list)
        eval_benchmark.show_result(success_results,precision_results,norm_precision_results,filter_type=t)
        
        if output_dir:
            output_dir_attr = output_dir.joinpath("all") if t is None else output_dir.joinpath(t)
            os.makedirs(output_dir_attr, exist_ok=True)
            eval_benchmark.draw_success_precision(output_dir_attr, success_results, precision_results, norm_precision_results)
            #eval_benchmark.visualize_tracker_results(videos,tracker_list,success_results)

## Load video class for parallel processing
class LoadVideo:
    def __init__(self, video_path: Path, anno_path: Path, meta_path: Path) -> None:
        self.video_path = video_path
        self.anno_path = anno_path
        self.meta_path = meta_path
        self.video_obj = None

    def run(self) -> None:
        self.video_obj = load_video_from_file(self.video_path, None, self.anno_path, self.meta_path)
        ## TODO:
        for frame in self.video_obj.frames:
            frame.get_occ_percentages()
        return self

def filter_videos(videos_all, test_file=None, filter_type=None):
    if not test_file and not filter_type:
        return videos_all

    if test_file:
        with open(str(test_file)) as fr:
            test_video_keys = [f.strip() for f in fr.readlines()]
            test_videos = set(test_video_keys)
    
    filtered_videos = []
    for video in videos_all:
        if not test_file:
            if filter_type == "s":
                if video.occlusion_tags.solid:
                    filtered_videos.append(video)
            elif filter_type == "sp":
                if video.occlusion_tags.sparse:
                    filtered_videos.append(video)
            elif filter_type == "st":
                if video.occlusion_tags.semiTransparent:
                    filtered_videos.append(video)
            elif filter_type == "t":
                if video.occlusion_tags.transparent:
                    filtered_videos.append(video)
            elif filter_type == "oof":
                if video.occlusion_tags.out_of_frame:
                    filtered_videos.append(video)
            elif filter_type == "oov":
                if video.occlusion_tags.out_of_view:
                    filtered_videos.append(video)
            elif filter_type == "cbf":
                if video.occlusion_tags.cut_by_frame:
                    filtered_videos.append(video)
            elif filter_type == "multiple":
                if video.occ_tags["mult_occ"]:
                    filtered_videos.append(video)   
            elif filter_type == "similar":
                if video.occ_tags["similar_occ"]:
                    filtered_videos.append(video)       
            elif filter_type == "dynamic":
                if video.motion_tags.dynamic:
                    filtered_videos.append(video)
            elif filter_type == "camera":
                if video.motion_tags.camera_motion:
                    filtered_videos.append(video)   
            elif filter_type == "noncamera":
                if not video.motion_tags.camera_motion:
                    filtered_videos.append(video)   
            elif filter_type == "parallax":
                if video.motion_tags.parallax:
                    filtered_videos.append(video)   
            elif filter_type == "moving_occ":
                if video.motion_tags.moving_occluder:
                    filtered_videos.append(video)  
            elif filter_type == "deformable":
                if video.target_tags.deformable:
                    filtered_videos.append(video)   
            elif filter_type == "animate":
                if video.target_tags.animate:
                    filtered_videos.append(video)   
            elif filter_type == "self_propelled":
                if video.target_tags.self_propelled:
                    filtered_videos.append(video)  
            elif filter_type == "nondeformable":
                if not video.target_tags.deformable:
                    filtered_videos.append(video)   
            elif filter_type == "nonanimate":
                if not video.target_tags.animate:
                    filtered_videos.append(video)   
            elif filter_type == "nonself_propelled":
                if not video.target_tags.self_propelled:
                    filtered_videos.append(video)  
            else:
                filtered_videos.append(video)
        else:
            if video.video_key in test_videos:
                if filter_type == "s":
                    if video.occlusion_tags.solid:
                        filtered_videos.append(video)
                elif filter_type == "sp":
                    if video.occlusion_tags.sparse:
                        filtered_videos.append(video)
                elif filter_type == "st":
                    if video.occlusion_tags.semiTransparent:
                        filtered_videos.append(video)
                elif filter_type == "t":
                    if video.occlusion_tags.transparent:
                        filtered_videos.append(video)
                elif filter_type == "oof":
                    if video.occlusion_tags.out_of_frame:
                        filtered_videos.append(video)
                elif filter_type == "oov":
                    if video.occlusion_tags.out_of_view:
                        filtered_videos.append(video)
                elif filter_type == "cbf":
                    if video.occlusion_tags.cut_by_frame:
                        filtered_videos.append(video)
                elif filter_type == "multiple":
                    if video.occ_tags["mult_occ"]:
                        filtered_videos.append(video)   
                elif filter_type == "similar":
                    if video.occ_tags["similar_occ"]:
                        filtered_videos.append(video) 
                else:
                    filtered_videos.append(video)
    return filtered_videos

    