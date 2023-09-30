import numpy as np
from colorama import Style, Fore
import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple, List
#import matplotlib
#import matplotlib.pyplot as plt
#import seaborn as sns
import random
import cv2
import csv
from collections import defaultdict
import os
from hoot.anno import *

PRECISION_TH = np.arange(0, 51, 1)
NORM_PRECISION_TH = np.arange(0, 51, 1)
DEBUG_VISUALIZE = False

LINE_STYLE = ['-', '--', ':', '-', '--', ':', '-', '--', ':', '-']
MARKER_STYLE = ['o', 'v', '<', '*', 'D', 'x', '.', 'x', '<', '.']

class OPE_Benchmark:
    """
    Adapted for HOOT using PySOT evaluation repository at:
    https://github.com/StrangerZhang/pysot-toolkit
    Args:
        annotations: loaded hoot annotations
        tracker_path: path to results of your tracker
                single tracker results in tracker_path/{tracker_name}/{video_key}.csv
                {video_key}.csv expects [frame, xmin, ymin, w, h, ...]
    """
    def __init__(self, annotations, tracker_path):
        self.video_keys = [v.video_key for v in annotations]
        self.annotations = {v.video_key : v for v in annotations} ## annotations for videos to evaluate
        self.predictions = {v.video_key : {} for v in annotations} ## tracker predictions for videos to evaluate
        self.tracker_path = tracker_path ## path to folder with tracker results

    ## Loads the predicted trajectory for a video in [x, y, w , h] x N format 
    def load_tracker(self, video_key, tracker_name):
        tracker_path = Path(self.tracker_path)

        #path_to_tracker_results = tracker_path.joinpath(tracker_name,video_key+".csv")
        ## TODO: fix this before official release
        path_to_tracker_results = tracker_path.joinpath(tracker_name,"stark_st",video_key+".csv")
        
        if not path_to_tracker_results.is_file():
            print(path_to_tracker_results)
            raise Exception("Cannot find tracker results for video!")

        pred_traj = []
        with open(str(path_to_tracker_results), newline='') as csvfile:
            reader = csv.reader(csvfile)
            csvfile.seek(0)

            ## TODO: fix this before official release to not assume a header
            ## Assume there's a header and remove it before processing
            next(reader)
            
            for row in reader:
                pred_bb = [row[1],row[2],row[3],row[4]]
                pred_bb = [float(x) for x in pred_bb]
                ## Append to trajectory in [x,y,w,h] format
                pred_traj.append([pred_bb[0],pred_bb[1],pred_bb[2]-pred_bb[0],pred_bb[3]-pred_bb[1]])

        self.predictions[video_key][tracker_name] = pred_traj
        
        return pred_traj
    
    ## Takes in [x,y,w,h] and returns [x_center,y_center]
    ## returns [x;y] X N ??
    def convert_bb_to_center(self, bboxes):
        return np.array([(bboxes[:, 0] + (bboxes[:, 2] - 1) / 2),
                         (bboxes[:, 1] + (bboxes[:, 3] - 1) / 2)]).T

    ## Takes in [x,y,w,h] and returns [x_center,y_center] normalized by image width and height
    ## gt_wh is an array of N x [w,h] ??
    def convert_bb_to_norm_center(self, bboxes, gt_wh):
        return self.convert_bb_to_center(bboxes) / (gt_wh+1e-16)

    ## Computes IoU from 2 rect arrays / rect: 2d array of N x [x,y,w,h]
    def overlap_ratio(self, rect1, rect2):

        left = np.maximum(rect1[:,0], rect2[:,0])
        right = np.minimum(rect1[:,0] + rect1[:,2], rect2[:,0] + rect2[:,2])
        top = np.maximum(rect1[:,1], rect2[:,1])
        bottom = np.minimum(rect1[:,1] + rect1[:,3], rect2[:,1] + rect2[:,3])

        intersect = np.maximum(0, right - left) * np.maximum(0, bottom - top)
        union = (rect1[:,2] * rect1[:,3]) + (rect2[:,2] * rect2[:,3]) - intersect
        iou = intersect / union.astype(float)
        iou = np.maximum(np.minimum(1, iou), 0)
        return iou

    ## N x [x,y,w,h] velues for both gt and result bbs
    def success_overlap(self, gt_bb, result_bb, n_frame):
        thresholds_overlap = np.arange(0, 1.05, 0.05)
        success = np.zeros(len(thresholds_overlap))
        iou = np.ones(len(gt_bb)) * (-1)
        mask = np.sum(gt_bb > 0, axis=1) > 1 ## checks not all values == 0, represents absent
        iou[mask] = self.overlap_ratio(gt_bb[mask], result_bb[mask])
        for i in range(len(thresholds_overlap)):
            success[i] = np.sum(iou > thresholds_overlap[i]) / float(n_frame)
        return success

    ## N x [x,y] velues for both gt and result box centers
    def success_error(self, gt_center, result_center, thresholds, n_frame):
        success = np.zeros(len(thresholds))
        dist = np.ones(len(gt_center)) * (-1)
        mask = np.sum(gt_center > 0, axis=1) > 0 
        dist[mask] = np.sqrt(np.sum(
            np.power(gt_center[mask] - result_center[mask], 2), axis=1))
        for i in range(len(thresholds)):
            success[i] = np.sum(dist <= thresholds[i]) / float(n_frame)
        return success

    ## Takes in a list of tracker keywords, returns a results dict
    def eval_success(self, eval_trackers=None):

        if eval_trackers is None:
            raise Exception("No trackers given to evaluate!")
        
        ## If only a single tracker given as a string, puts that in a list
        if isinstance(eval_trackers, str):
            eval_trackers = [eval_trackers]

        success_results = {}
        for tracker_name in eval_trackers:
            tracker_success = {}
            for video_key in self.video_keys:
                video = self.annotations[video_key]
                gt_bb, gt_absent, _ = video.get_evaluation_data 
                gt_traj = np.array(gt_bb)
                absent_labels = np.array(gt_absent)
                
                if tracker_name not in self.predictions[video_key]:
                    tracker_traj = self.load_tracker(video_key, tracker_name)
                    tracker_traj = np.array(tracker_traj)
                else:
                    tracker_traj = np.array(self.predictions[video_key][tracker_name])
                
                ## Get video length to compute average results
                ## we will use (n_frame - 1) since we won't evaluate first frame
                n_frame = len(gt_traj) 
                
                ## Make sure results and gt lengths match
                assert len(gt_traj) == len(tracker_traj) 
                assert len(gt_traj) == len(absent_labels)

                ## Filter frames to evaluate overlap only if target is in frame
                gt_traj = gt_traj[absent_labels == 0]
                tracker_traj = tracker_traj[absent_labels == 0]
                
                ## Compute average overlap
                tracker_success[video.video_key] = self.success_overlap(gt_traj[1:], tracker_traj[1:], n_frame-1)
            success_results[tracker_name] = tracker_success
        return success_results

    ## Takes in a list of tracker keywords, returns a results dict
    def eval_precision(self, eval_trackers=None):

        if eval_trackers is None:
            raise Exception("No trackers given to evaluate!")
        
        ## If only a single tracker given as a string, puts that in a list
        if isinstance(eval_trackers, str):
            eval_trackers = [eval_trackers]

        precision_results = {}
        for tracker_name in eval_trackers:
            tracker_precision = {}
            for video_key in self.video_keys:
                video = self.annotations[video_key]
                gt_bb, gt_absent, _ = video.get_evaluation_data 
                gt_traj = np.array(gt_bb)
                absent_labels = np.array(gt_absent)
                
                if tracker_name not in self.predictions[video_key]:
                    tracker_traj = self.load_tracker(video_key, tracker_name)
                    tracker_traj = np.array(tracker_traj)
                else:
                    tracker_traj = np.array(self.predictions[video_key][tracker_name])
                
                ## Get video length to compute average results
                ## we will use (n_frame - 1) since we won't evaluate first frame
                n_frame = len(gt_traj) 
                
                ## Make sure results and gt lengths match
                assert len(gt_traj) == len(tracker_traj) 
                assert len(gt_traj) == len(absent_labels)

                ## Filter frames to evaluate overlap only if target is in frame
                gt_traj = gt_traj[absent_labels == 0]
                tracker_traj = tracker_traj[absent_labels == 0]
                
                gt_center = self.convert_bb_to_center(gt_traj)
                tracker_center = self.convert_bb_to_center(tracker_traj)
                thresholds = PRECISION_TH
                tracker_precision[video.video_key] = self.success_error(gt_center[1:], tracker_center[1:],
                        thresholds, n_frame-1)
            precision_results[tracker_name] = tracker_precision
        return precision_results

    ## Takes in a list of tracker keywords, returns a results dict
    def eval_norm_precision(self, eval_trackers=None):

        if eval_trackers is None:
            raise Exception("No trackers given to evaluate!")
        
        ## If only a single tracker given as a string, puts that in a list
        if isinstance(eval_trackers, str):
            eval_trackers = [eval_trackers]

        norm_precision_results = {}
        for tracker_name in eval_trackers:
            tracker_norm_precision = {}
            for video_key in self.video_keys:
                video = self.annotations[video_key]
                gt_bb, gt_absent, _ = video.get_evaluation_data 
                gt_traj = np.array(gt_bb)
                absent_labels = np.array(gt_absent)
                
                if tracker_name not in self.predictions[video_key]:
                    tracker_traj = self.load_tracker(video_key, tracker_name)
                    tracker_traj = np.array(tracker_traj)
                else:
                    tracker_traj = np.array(self.predictions[video_key][tracker_name])
                
                ## Get video length to compute average results
                ## we will use (n_frame - 1) since we won't evaluate first frame
                n_frame = len(gt_traj) 
                
                ## Make sure results and gt lengths match
                assert len(gt_traj) == len(tracker_traj) 
                assert len(gt_traj) == len(absent_labels)

                ## Filter frames to evaluate overlap only if target is in frame
                gt_traj = gt_traj[absent_labels == 0]
                tracker_traj = tracker_traj[absent_labels == 0]
                
                gt_center_norm = self.convert_bb_to_norm_center(gt_traj, gt_traj[:, 2:4])
                tracker_center_norm = self.convert_bb_to_norm_center(tracker_traj, gt_traj[:, 2:4])
                thresholds = NORM_PRECISION_TH / 100
                tracker_norm_precision[video.video_key] = self.success_error(gt_center_norm[1:],
                        tracker_center_norm[1:], thresholds, n_frame-1)
            norm_precision_results[tracker_name] = tracker_norm_precision
        return norm_precision_results

    def show_result(self, success_ret, precision_ret=None, norm_precision_ret=None, 
            show_video_level=False, helight_threshold=0.6, filter_type="all"):

        if not filter_type:
            filter_type = "all"
        
        print("RESULTS FOR SUBSET TYPE: "+filter_type)
        
        ## Sort tracker results
        tracker_auc = {}
        for tracker_name in success_ret.keys():
            auc = np.mean(list(success_ret[tracker_name].values()))
            tracker_auc[tracker_name] = auc
        tracker_auc_ = sorted(tracker_auc.items(),
                             key=lambda x:x[1],
                             reverse=True)#[:20]
        tracker_names = [x[0] for x in tracker_auc_]

        tracker_name_len = max((max([len(x) for x in success_ret.keys()])+2), 12)
        header = ("|{:^"+str(tracker_name_len)+"}|{:^9}|{:^16}|{:^11}|").format(
                "Tracker name", "Success", "Norm Precision", "Precision")
        formatter = "|{:^"+str(tracker_name_len)+"}|{:^9.3f}|{:^16.3f}|{:^11.3f}|"
        print('-'*len(header))
        print(header)
        print('-'*len(header))
        breakpoint()
        for tracker_name in tracker_names:
            success = tracker_auc[tracker_name]
            if precision_ret is not None:
                precision = np.mean(list(precision_ret[tracker_name].values()), axis=0)[20]
            else:
                precision = 0
            if norm_precision_ret is not None:
                norm_precision = np.mean(list(norm_precision_ret[tracker_name].values()),
                        axis=0)[20]
            else:
                norm_precision = 0
            print(formatter.format(tracker_name, success, norm_precision, precision))
        print('-'*len(header))

    def draw_success_precision(self, out_path, success_ret, precision_ret=None,
                                    norm_precision_ret=None, bold_name=None, axis=[0, 1]):
        
        # success plot
        fig, ax = plt.subplots()
        ax.grid(visible=True)
        ax.set_aspect(1)
        plt.xlabel('Overlap Threshold')
        plt.ylabel('Success Rate')
        plt.axis([0, 1]+axis)
        success = {}
        thresholds = np.arange(0, 1.05, 0.05)
        for tracker_name in success_ret.keys():
            value = [v for k, v in success_ret[tracker_name].items()]
            success[tracker_name] = np.mean(value)
        colors = sns.color_palette("deep", len(success)).as_hex()
        for idx, (tracker_name, auc) in  \
                enumerate(sorted(success.items(), key=lambda x:x[1], reverse=True)):
            if tracker_name == bold_name:
                label = r"\textbf{[%.3f] %s}" % (auc, tracker_name)
            else:
                label = "[%.3f] " % (auc) + tracker_name
            value = [v for k, v in success_ret[tracker_name].items()]
            plt.plot(thresholds, np.mean(value, axis=0),
                    color=colors[idx], linestyle=LINE_STYLE[idx%len(LINE_STYLE)],label=label, linewidth=2)
        ax.legend(loc='upper right', labelspacing=0.2)
        ax.autoscale(enable=True, axis='both', tight=True)
        xmin, xmax, ymin, ymax = plt.axis()
        ax.autoscale(enable=False)
        ymax += 0.03
        ymin = 0
        plt.axis([xmin, xmax, ymin, ymax])
        plt.xticks(np.arange(xmin, xmax+0.01, 0.1))
        plt.yticks(np.arange(ymin, ymax, 0.1))
        ax.set_aspect((xmax - xmin)/(ymax-ymin))
        
        if DEBUG_VISUALIZE:
            plt.show()
        else:
            plt.savefig(out_path.joinpath("success.png"),dpi=800)
        
        if precision_ret:
            # precision plot
            fig, ax = plt.subplots()
            ax.grid(visible=True)
            ax.set_aspect(50)
            plt.xlabel('Location Error Threshold')
            plt.ylabel('Precision')
            plt.axis([0, 100]+axis)
            precision = {}
            thresholds = PRECISION_TH
            for tracker_name in precision_ret.keys():
                value = [v for k, v in precision_ret[tracker_name].items()]
                precision[tracker_name] = np.mean(value, axis=0)[20]
            colors = sns.color_palette("deep", len(success)).as_hex()
            for idx, (tracker_name, pre) in \
                    enumerate(sorted(precision.items(), key=lambda x:x[1], reverse=True)):
                if tracker_name == bold_name:
                    label = r"\textbf{[%.3f] %s}" % (pre, tracker_name)
                else:
                    label = "[%.3f] " % (pre) + tracker_name
                value = [v for k, v in precision_ret[tracker_name].items()]
                plt.plot(thresholds, np.mean(value, axis=0),
                        color=colors[idx], linestyle=LINE_STYLE[idx%len(LINE_STYLE)],label=label, linewidth=2)
            ax.legend(loc='upper left', labelspacing=0.2)
            ax.autoscale(enable=True, axis='both', tight=True)
            xmin, xmax, ymin, ymax = plt.axis()
            ax.autoscale(enable=False)
            ymax += 0.03
            ymin = 0
            plt.axis([xmin, xmax, ymin, ymax])
            plt.xticks(np.arange(xmin, xmax+0.01, 10))
            plt.yticks(np.arange(ymin, ymax, 0.1))
            ax.set_aspect((xmax - xmin)/(ymax-ymin))
            if DEBUG_VISUALIZE:
                plt.show()
            else:
                plt.savefig(out_path.joinpath("precision.png"),dpi=800)

        # norm precision plot
        if norm_precision_ret:
            fig, ax = plt.subplots()
            ax.grid(visible=True)
            plt.xlabel('Location Error Threshold')
            plt.ylabel('Normalized Precision')
            norm_precision = {}
            thresholds = NORM_PRECISION_TH / 100
            for tracker_name in precision_ret.keys():
                value = [v for k, v in norm_precision_ret[tracker_name].items()]
                norm_precision[tracker_name] = np.mean(value, axis=0)[20]
            colors = sns.color_palette("deep", len(success)).as_hex()
            for idx, (tracker_name, pre) in \
                    enumerate(sorted(norm_precision.items(), key=lambda x:x[1], reverse=True)):
                if tracker_name == bold_name:
                    label = r"\textbf{[%.3f] %s}" % (pre, tracker_name)
                else:
                    label = "[%.3f] " % (pre) + tracker_name
                value = [v for k, v in norm_precision_ret[tracker_name].items()]
                plt.plot(thresholds, np.mean(value, axis=0),
                        color=colors[idx], linestyle=LINE_STYLE[idx%len(LINE_STYLE)],label=label, linewidth=2)
            ax.legend(loc='upper left', labelspacing=0.2)
            ax.autoscale(enable=True, axis='both', tight=True)
            xmin, xmax, ymin, ymax = plt.axis()
            ax.autoscale(enable=False)
            ymax += 0.03
            ymin = 0
            plt.axis([xmin, xmax, ymin, ymax])
            plt.xticks(np.arange(xmin, xmax+0.01, 0.1))
            plt.yticks(np.arange(ymin, ymax, 0.1))
            ax.set_aspect((xmax - xmin)/(ymax-ymin))
            if DEBUG_VISUALIZE:
                plt.show()
            else:
                plt.savefig(out_path.joinpath("norm_precision.png"),dpi=800)
            
    def visualize_tracker_results(self, out_dir, tracker_list, success_res=None, results_info=["med_scoring", 10, 200,300]):
        
        ## If success results are given, we can use mean success across trackers to visualize
        ## videos that perform low/high
        if success_res:
            video_scores = defaultdict(list)
            for tracker in tracker_list:
                for k,v in success_res[tracker].items():
                    video_scores[k].append(v)
            video_keys = list(video_scores.keys())
            video_keys.sort(key=lambda k: np.mean(video_scores[k]))
            score_level_vids = random.choices(video_keys[results_info[2]:results_info[3]],k=results_info[1])
            #print(np.median([video_scores[v] for v in video_keys][500:]))
            #print(np.median([video_scores[v] for v in video_keys][200:300]))
            #print(np.median([video_scores[v] for v in video_keys][:50]))
            vids = [v for k,v in self.annotations.items() if k in score_level_vids]
        else:
            vids = random.choices(self.annotations.values(), k=results_info[1])
        
        colors = sns.color_palette("deep", len(tracker_list))

        for v in vids:
            out_path = out_dir.joinpath(results_info[0],v.video_key)
            os.makedirs(out_path, exist_ok=True)
            
            idx = 0
            for frame_anno in v.frames:
                frame = cv2.imread(frame_anno.frame_path)
                bbox = list(map(int, v.gt_traj[idx]))
                cv2.rectangle(frame, (bbox[0], bbox[1]),
                                (bbox[0]+bbox[2], bbox[1]+bbox[3]),
                                (0, 255, 0), 7)
                
                pred_trajectories = [self.predictions[v.video_key][t] for t in tracker_list]
                for idy,ttraj in enumerate(pred_trajectories):
                    bbox = list(map(int, ttraj[idx]))
                    cv2.rectangle(frame, (bbox[0], bbox[1]),
                                (bbox[0]+bbox[2], bbox[1]+bbox[3]),
                                (255*colors[idy][2], 255*colors[idy][1], 255*colors[idy][0]), 7)
                cv2.imwrite(out_path+"/"+str(idx).zfill(6)+".png",frame)
                idx += 1