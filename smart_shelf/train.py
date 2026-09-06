"""
train.py — Train YOLO11 on custom retail shelf dataset
Usage:  python train.py
"""
import os
import torch
from ultralytics import YOLO

def train_model():
    # 1. Detect hardware acceleration
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"[INFO] Using acceleration device: {device.upper()}")
    if device == 'cuda':
        print(f"[INFO] GPU Name: {torch.cuda.get_device_name(0)}")

    # 2. Load pre-trained model checkpoint (YOLO11n default)
    model = YOLO("yolo11n.pt")

    # 3. Verify dataset exists
    dataset_config = "data.yaml"
    if not os.path.exists("dataset"):
        print("[WARNING] Custom dataset not found at 'dataset'.")
        print("[INFO] Please run gather_dataset.py first to generate the dataset.")
        return

    # 4. Train model with Advanced ML configurations (AMP, Cosine LR, improved augmentations)
    results = model.train(
        data=dataset_config,
        epochs=1,
        imgsz=640,
        batch=16 if device == 'cuda' else 4,
        device=0 if device == 'cuda' else 'cpu',
        workers=4,
        patience=15,             # Stop training if no improvement after 15 epochs (prevents overfitting)
        save=True,
        project="runs/detect",
        name="smart_shelf_model",

        # --- Data Augmentation Parameters ---
        hsv_h=0.015,             # Hue variation
        hsv_s=0.7,               # Saturation variation
        hsv_v=0.4,               # Value/brightness variation
        degrees=10.0,            # Rotation
        translate=0.1,           # Translation
        scale=0.5,               # Scale gain
        shear=2.0,               # Shear angle
        perspective=0.0005,      # Perspective transform
        flipud=0.0,              # No vertical flips (upright shelves)
        fliplr=0.5,              # Horizontal flips (50% probability)
        mosaic=1.0,              # Mosaic augmentation
        mixup=0.15,              # Mixup augmentation
        copy_paste=0.1,          # Copy-paste objects

        # --- Optimizer & Regularization ---
        optimizer="auto",        # Let Ultralytics choose the best optimizer (usually AdamW)
        lr0=0.002,               # Initial learning rate
        lrf=0.01,                # Final learning rate fraction
        weight_decay=0.0005,     # L2 Regularization penalty
        cos_lr=True,             # Cosine learning rate scheduler for smoother convergence
        amp=True,                # Automatic Mixed Precision for faster, memory-efficient training
        close_mosaic=10,         # Disable mosaic for the final 10 epochs (improves fine details)
        dropout=0.1              # Dropout for regularization
    )

    print("[SUCCESS] Training completed! Model saved to runs/detect/smart_shelf_model/weights/best.pt")

if __name__ == "__main__":
    train_model()
