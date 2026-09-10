"""
inference.py — Test YOLO11 model on images, videos, webcam, and IP/mobile cameras
Usage:
  python inference.py webcam 0
  python inference.py mobile http://192.168.1.5:8080/video
  python inference.py video sample.mp4
  python inference.py image sample.jpg
"""
import os
import sys
import cv2
from ultralytics import YOLO

def _get_best_model_path():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(curr_dir)
    candidates = [
        os.path.join(root_dir, "ml", "models", "yolo11_smartshelf_pen_lays_bisc", "best.pt"),
        os.path.join(root_dir, "runs", "train", "yolo11_smartshelf_pen_lays_bisc", "weights", "best.pt"),
        os.path.join(curr_dir, "runs", "detect", "smart_shelf_model", "weights", "best.pt"),
        os.path.join(curr_dir, "yolo11n.onnx"),
        os.path.join(curr_dir, "yolo11n.pt"),
        "yolo11n.pt"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "yolo11n.pt"

def run_inference(source_type="webcam", source_path="0", model_path=None):
    if model_path is None or not os.path.exists(model_path):
        model_path = _get_best_model_path()

    print(f"[INFO] Loading model from: {model_path}")
    model = YOLO(model_path)
    
    # 1. Single Image Inference
    if source_type == "image":
        results = model(source_path, conf=0.5)
        for r in results:
            r.show()
            r.save(filename="output_result.jpg")
        print("[INFO] Inference complete. Result saved to output_result.jpg")

    # 2. Video / Webcam / Mobile IP Camera Stream
    else:
        src = int(source_path) if source_path.isdigit() else source_path
        cap = cv2.VideoCapture(src)

        if not cap.isOpened():
            print(f"[ERROR] Could not open video source: {source_path}")
            return

        print(f"[INFO] Streaming from source: {source_path}. Press 'q' to quit.")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Perform detection & ByteTrack tracking
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
            annotated_frame = results[0].plot()  # Render bounding boxes, conf scores, and class labels

            cv2.imshow("Smart Shelf Inference Stream", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    stype = sys.argv[1] if len(sys.argv) > 1 else "webcam"
    spath = sys.argv[2] if len(sys.argv) > 2 else "0"
    run_inference(stype, spath)
