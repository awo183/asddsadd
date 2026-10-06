"""Run real object/face detection over the footage and cache the results.

Objects: YOLOX-S (COCO, 80 classes) from the OpenCV model zoo.
Faces:   YuNet from the OpenCV model zoo.
Output:  one JSON per clip and detector (<clip>.obj.json / <clip>.face.json): {"fps": f, "frames": [[[x, y, w, h, score, cls], ...], ...]}
"""
import json
import os
import sys
import time

import cv2
import numpy as np

COCO = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
        "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
        "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
        "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
        "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
        "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
        "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush"]


class YoloX:
    def __init__(self, path, conf=0.35, nms=0.5):
        self.net = cv2.dnn.readNet(path)
        self.conf, self.nms = conf, nms
        grids, strides = [], []
        for s in (8, 16, 32):
            n = 640 // s
            xv, yv = np.meshgrid(np.arange(n), np.arange(n))
            grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
            strides.append(np.full((n * n, 1), s))
        self.grids = np.concatenate(grids).astype(np.float32)
        self.strides = np.concatenate(strides).astype(np.float32)

    def __call__(self, bgr):
        h, w = bgr.shape[:2]
        r = min(640 / h, 640 / w)
        pad = np.full((640, 640, 3), 114.0, np.float32)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pad[: int(h * r), : int(w * r)] = cv2.resize(rgb, (int(w * r), int(h * r)))
        self.net.setInput(np.transpose(pad, (2, 0, 1))[None])
        d = self.net.forward(self.net.getUnconnectedOutLayersNames())[0][0]
        d[:, :2] = (d[:, :2] + self.grids) * self.strides
        d[:, 2:4] = np.exp(d[:, 2:4]) * self.strides
        xywh = np.stack([d[:, 0] - d[:, 2] / 2, d[:, 1] - d[:, 3] / 2, d[:, 2], d[:, 3]], 1) / r
        scores = d[:, 4:5] * d[:, 5:]
        best, cls = scores.max(1), scores.argmax(1)
        keep = cv2.dnn.NMSBoxesBatched(xywh.tolist(), best.tolist(), cls.tolist(), self.conf, self.nms)
        return [[*map(float, xywh[i]), float(best[i]), int(cls[i])] for i in np.array(keep).flatten()]


class Faces:
    def __init__(self, path):
        self.det = cv2.FaceDetectorYN.create(path, "", (320, 320), 0.7, 0.3, 50)

    def __call__(self, bgr):
        h, w = bgr.shape[:2]
        self.det.setInputSize((w, h))
        _, faces = self.det.detect(bgr)
        if faces is None:
            return []
        # x, y, w, h, score, cls(-1 = face), then 5 landmarks
        return [[*map(float, f[:4]), float(f[14]), -1, *map(float, f[4:14])] for f in faces]


def run(model, clip, out, step=1, t0=0.0, t1=None):
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
    frames, i, start = [], 0, time.time()
    while True:
        ok, img = cap.read()
        if not ok or (t1 is not None and t0 + i / fps > t1):
            break
        frames.append(model(img) if i % step == 0 else frames[-1])
        i += 1
    with open(out, "w") as f:
        json.dump({"fps": fps, "t0": t0, "frames": frames}, f)
    print(f"{os.path.basename(clip)}: {len(frames)} frames in {time.time() - start:.0f}s")


if __name__ == "__main__":
    models, footage, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    yolo = YoloX(os.path.join(models, "object_detection_yolox_2022nov.onnx"))
    faces = Faces(os.path.join(models, "face_detection_yunet_2023mar.onnx"))
    # (detector, clip, frame step, from second, to second)
    jobs = [
        ("face", "classroom", 1, 0, 33),
        ("face", "face-demographics-walking", 1, 0, 61),
        ("face", "head-pose-face-detection-female-and-male", 1, 0, 40),
        ("face", "face-demographics-walking-and-pause", 1, 0, 25),
        ("obj", "person-bicycle-car-detection", 1, 0, 54),
        ("obj", "car-detection", 1, 0, 31),
        ("obj", "store-aisle-detection", 2, 0, 66),
        ("obj", "worker-zone-detection", 2, 0, 76),
        ("obj", "fruit-and-vegetable-detection", 2, 0, 61),
        ("obj", "people-detection", 1, 0, 50),
        ("obj", "one-by-one-person-detection", 1, 0, 60),
        ("obj", "face-demographics-walking-and-pause", 1, 0, 25),
        ("obj", "bottle-detection", 1, 0, 40),
        ("obj", "driver-action-recognition", 2, 0, 45),
    ]
    only = sys.argv[4:]
    for kind, name, step, t0, t1 in jobs:
        dst = os.path.join(out, f"{name}.{kind}.json")
        if (only and name not in only) or os.path.exists(dst):
            continue
        run(yolo if kind == "obj" else faces, os.path.join(footage, name + ".mp4"), dst, step, t0, t1)
