"""
train.py — Custom YOLO Training Pipeline for Smart Shelf Inventory
Trains YOLOv8 / YOLO11 on the custom product dataset.
Supports auto hardware detection (CUDA GPU / CPU), configurable epochs, and ONNX export.
"""
import os
import torch

def train_model(
    data_yaml="data.yaml",
    base_model="yolov8n.pt",
    epochs=50,
    imgsz=640,
    batch=8,
    project="runs/detect",
    name="smart_shelf_model"
):
    from ultralytics import YOLO

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"=== Starting YOLO Training on Device: {device.upper()} ===")
    print(f"Dataset Config: {data_yaml}")
    print(f"Base Model:     {base_model}")
    print(f"Epochs:         {epochs}")

    # Load model
    model = YOLO(base_model)

    # Train
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=project,
        name=name,
        verbose=True,
        save=True
    )

    print("\n=== Training Completed Successfully! ===")
    best_weights = os.path.join(project, name, "weights", "best.pt")
    if os.path.exists(best_weights):
        print(f"Best weights saved at: {best_weights}")
        # Export to ONNX for lightweight inference
        try:
            model = YOLO(best_weights)
            model.export(format="onnx")
            print("Exported best model to ONNX format.")
        except Exception as e:
            print(f"ONNX export note: {e}")

    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train YOLO on Smart Shelf Dataset")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--data", type=str, default="data.yaml", help="Path to data.yaml")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model weights")
    args = parser.parse_args()

    train_model(
        data_yaml=args.data,
        base_model=args.model,
        epochs=args.epochs,
        batch=args.batch
    )
