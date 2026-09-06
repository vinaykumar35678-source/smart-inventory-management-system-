"""
optimize_model.py — Export YOLO11 model to ONNX for Edge Inference
Run this script to convert PyTorch weights (.pt) to optimized ONNX format.
"""
import argparse
import os
from ultralytics import YOLO

def export_model(model_path="yolo11n.pt", format="onnx", half=True):
    print(f"[INFO] Loading PyTorch model from {model_path}...")
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"[ERROR] Failed to load {model_path}. Error: {e}")
        return

    print(f"[INFO] Exporting model to {format.upper()} format (half-precision: {half})...")
    # Exporting with dynamic=True allows variable image sizes, half=True uses FP16 for faster inference on supported hardware
    exported_path = model.export(format=format, half=half, dynamic=False, simplify=True)
    
    print(f"[SUCCESS] Model optimized and saved to: {exported_path}")
    print("[NEXT STEP] detection.py will now automatically load the optimized ONNX model.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLO11 for Edge Inference")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Path to PyTorch weights")
    parser.add_argument("--format", type=str, default="onnx", choices=["onnx", "engine", "openvino"], help="Export format")
    parser.add_argument("--no-half", action="store_true", help="Disable FP16 half-precision")
    
    args = parser.parse_args()
    
    # We only use half precision if not explicitly disabled
    use_half = not args.no_half
    export_model(args.model, args.format, use_half)
