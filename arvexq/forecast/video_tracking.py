"""Permissioned local race-video analysis; INTERNAL features only.

No network/video acquisition or visible video UI. Frame-track IDs are not horse
identities. Every horse ID and each camera-to-ground transform must be verified.
OpenCV is imported only when processing an authorized local video.
"""
from __future__ import annotations
from math import hypot
from pathlib import Path


def _iou(a,b):
    x0=max(a[0],b[0]);y0=max(a[1],b[1]);x1=min(a[2],b[2]);y1=min(a[3],b[3])
    inter=max(0,x1-x0)*max(0,y1-y0)
    aa=max(0,a[2]-a[0])*max(0,a[3]-a[1])
    bb=max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return inter/(aa+bb-inter) if aa+bb>inter else 0.


class ONNXHorseDetector:
    """External, legally obtained 80-class YOLOv8 ONNX model required.

    COCO's horse label is only a generic detector; no claim of validated
    racehorse detection, complete-field coverage or rider/horse identity.
    """
    def __init__(self,weights,confidence=.45,input_size=640):
        import cv2
        if not Path(weights).is_file():
            raise FileNotFoundError(weights)
        self.net=cv2.dnn.readNetFromONNX(str(weights))
        self.confidence=confidence
        self.input_size=input_size

    def __call__(self,frame):
        import cv2
        import numpy as np
        h,w=frame.shape[:2]
        n=self.input_size
        scale=min(n/w,n/h)
        nw,nh=round(w*scale),round(h*scale)
        xo,yo=(n-nw)//2,(n-nh)//2
        canvas=np.full((n,n,3),114,dtype=np.uint8)
        canvas[yo:yo+nh,xo:xo+nw]=cv2.resize(frame,(nw,nh))
        blob=cv2.dnn.blobFromImage(canvas,1/255.0,(n,n),swapRB=True,crop=False)
        self.net.setInput(blob)
        raw=np.squeeze(self.net.forward())
        if raw.ndim!=2:
            raise ValueError("unsupported YOLO output")
        if raw.shape[0]==84:
            raw=raw.T
        if raw.shape[1]!=84:
            raise ValueError("expected 80-class, 84-channel ONNX detector")
        boxes=[];rects=[];scores=[]
        for row in raw:
            confidence=float(row[4+17])
            if confidence<self.confidence:
                continue
            cx,cy,bw,bh=map(float,row[:4])
            box=[max(0.,(cx-bw/2-xo)/scale),max(0.,(cy-bh/2-yo)/scale),
                 min(float(w),(cx+bw/2-xo)/scale),min(float(h),(cy+bh/2-yo)/scale)]
            if box[2]<=box[0] or box[3]<=box[1]:
                continue
            boxes.append(box)
            rects.append([int(box[0]),int(box[1]),int(box[2]-box[0]),int(box[3]-box[1])])
            scores.append(confidence)
        indices=cv2.dnn.NMSBoxes(rects,scores,self.confidence,.45)
        return [boxes[int(i)] for i in np.asarray(indices).flatten()]


def track_local_video(path,detector,*,frame_stride=2,max_frames=None):
    """Decode actual local video and collect unverified pixel trajectories.

    Crossing horses, occlusion and camera panning can cause false associations.
    No metric speed or rider identity is claimed here.
    """
    import cv2
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"video unreadable: {path}")
    fps=cap.get(cv2.CAP_PROP_FPS)
    if fps<=0 or frame_stride<1:
        cap.release()
        raise ValueError("invalid frame rate or stride")
    tracks={};last={};next_id=1;frame_index=0
    try:
        while True:
            ok,frame=cap.read()
            if not ok or (max_frames is not None and frame_index>=max_frames):
                break
            if frame_index%frame_stride==0:
                boxes=detector(frame)
                options=[]
                for tid,(old_frame,old_box) in last.items():
                    if frame_index-old_frame>frame_stride*3:
                        continue
                    for i,box in enumerate(boxes):
                        val=_iou(old_box,box)
                        a=((old_box[0]+old_box[2])/2,(old_box[1]+old_box[3])/2)
                        b=((box[0]+box[2])/2,(box[1]+box[3])/2)
                        distance=hypot(a[0]-b[0],a[1]-b[1])
                        if val>=.05 or distance<=60*frame_stride:
                            options.append((1-val+distance/1000,tid,i))
                assigned_i=set();assigned_t=set()
                for _,tid,i in sorted(options):
                    if i in assigned_i or tid in assigned_t:
                        continue
                    assigned_i.add(i);assigned_t.add(tid)
                    box=boxes[i]
                    tracks[tid].append({"frame":frame_index,"time":frame_index/fps,
                                        "pixelFoot":[(box[0]+box[2])/2,box[3]]})
                    last[tid]=(frame_index,box)
                for i,box in enumerate(boxes):
                    if i in assigned_i:
                        continue
                    tid=next_id;next_id+=1
                    tracks[tid]=[{"frame":frame_index,"time":frame_index/fps,
                                   "pixelFoot":[(box[0]+box[2])/2,box[3]]}]
                    last[tid]=(frame_index,box)
            frame_index+=1
    finally:
        cap.release()
    return {"frames":frame_index,"fps":fps,"tracks":tracks,
            "identityVerified":False,"geometryCalibrated":False}


def _project(H,x,y):
    if not isinstance(H,(list,tuple)) or len(H)!=3 or any(len(row)!=3 for row in H):
        raise ValueError("ground homography must be 3x3")
    z=H[2][0]*x+H[2][1]*y+H[2][2]
    if abs(z)<1e-9:
        raise ValueError("invalid ground transform")
    return ((H[0][0]*x+H[0][1]*y+H[0][2])/z,
            (H[1][0]*x+H[1][1]*y+H[1][2])/z)


def features_from_verified_tracks(tracking,*,identities,homographies,
                                  race_date,source,ideal_paths=None,expected_horse_ids=None):
    """Produce the privately consumable input shape of new_method.extract.

    Returns stable permanent horse IDs, never race numbers. Incomplete field
    remains incomplete rather than silently fabricating track observations.
    """
    result={};used=set()
    if not source or not race_date:
        raise ValueError("source and historical race date required")
    for tid,samples in (tracking.get("tracks") or {}).items():
        record=identities.get(tid,identities.get(str(tid)))
        if not isinstance(record,dict) or record.get("verified") is not True:
            continue
        sid=str(record.get("horseId") or "")
        if not sid or sid in used:
            raise ValueError("missing/duplicated stable horse identity")
        used.add(sid)
        if len(samples)<3:
            continue
        coords=[]
        for item in samples:
            H=homographies.get(item["frame"],homographies.get(str(item["frame"])))
            if H is None:
                raise ValueError("missing frame-specific metric homography")
            x,y=_project(H,*item["pixelFoot"])
            coords.append((float(item["time"]),x,y))
        if any(coords[i+1][0]<=coords[i][0] for i in range(len(coords)-1)):
            raise ValueError("non-monotonic video timestamps")
        steps=[hypot(b[1]-a[1],b[2]-a[2])/(b[0]-a[0]) for a,b in zip(coords,coords[1:])]
        traveled=sum(hypot(b[1]-a[1],b[2]-a[2]) for a,b in zip(coords,coords[1:]))
        ideal=(ideal_paths or {}).get(sid)
        decelerations=sum(1 for i in range(1,len(steps))
                         if (steps[i]-steps[i-1]) /
                         ((coords[i+1][0]-coords[i-1][0])/2) < -3)
        result[sid]={
            "identityVerified":True,"geometryCalibrated":True,
            "coordinateUnit":"meter","sourceDates":[race_date],"source":source,
            "meanSpeedMps":traveled/(coords[-1][0]-coords[0][0]),
            "initialSpeedMps":steps[0],
            "idealPathExcessMeters":max(0.,traveled-ideal) if ideal is not None else None,
            "slowdownCount":decelerations,
        }
    if expected_horse_ids is not None and set(result)!=set(map(str,expected_horse_ids)):
        raise ValueError("all runners' permanent identities need coverage")
    return result
