"""
capture_dataset.py
------------------
A utility script to quickly capture training images for YOLO using your webcam.

Usage:
1. Run `python capture_dataset.py`
2. Hold your object (e.g., Student ID Card) in front of the camera.
3. Press SPACEBAR to capture an image. Try to capture it from various angles, distances, and lighting.
4. Press ESC to quit.

The images will be saved in `dataset/raw_captures`.
"""

import cv2
import os
import time

def main():
    save_dir = os.path.join("dataset", "raw_captures")
    os.makedirs(save_dir, exist_ok=True)
    
    # Open default webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("========================================")
    print("      DATASET CAPTURE UTILITY           ")
    print("========================================")
    print(f"Saving images to: {save_dir}")
    print("Press SPACEBAR to capture an image.")
    print("Press ESC to exit.")
    print("========================================")

    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        # Draw instructions on frame
        display_frame = frame.copy()
        cv2.putText(display_frame, f"Captured: {count} images", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, "SPACE: Capture | ESC: Quit", (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow("Capture Dataset", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            break
        elif key == 32:  # SPACEBAR
            timestamp = int(time.time() * 1000)
            filename = os.path.join(save_dir, f"capture_{timestamp}.jpg")
            cv2.imwrite(filename, frame)
            count += 1
            print(f"Captured: {filename}")
            
            # Flash effect
            flash = display_frame.copy()
            flash[:] = (255, 255, 255)
            cv2.imshow("Capture Dataset", flash)
            cv2.waitKey(50)

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[INFO] Finished capturing {count} images.")
    print(f"[INFO] Next Step: Upload these images to MakeSense.ai for labeling!")

if __name__ == "__main__":
    main()
