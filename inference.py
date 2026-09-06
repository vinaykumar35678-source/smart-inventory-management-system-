"""
inference.py — Standalone YOLO Inference & Testing Utility
Tests YOLO model detection on images, webcam, or video files with bounding box visualization.
"""
import cv2
import os
import sys

def run_inference(source=0, weights="yolov8n.pt", conf=0.45):
    from ultralytics import YOLO

    print(f"Loading weights from {weights}...")
    model = YOLO(weights)

    # Convert source to int if numeric (e.g. "0" -> 0 for webcam)
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source: {source}")
        return

    print("Running inference. Press 'q' in the window to exit.")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=conf, verbose=False)
        annotated_frame = results[0].plot()

        cv2.imshow("Smart Shelf - Standalone Inference", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run YOLO Inference")
    parser.add_argument("--source", default=0, help="Webcam index (0) or path to video/image")
    parser.add_argument("--weights", default="yolov8n.pt", help="Path to model weights")
    parser.add_argument("--conf", type=float, default=0.45, help="Confidence threshold")
    args = parser.parse_args()

    run_inference(source=args.source, weights=args.weights, conf=args.conf)
