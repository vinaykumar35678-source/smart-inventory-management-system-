"""
enrich_phone_and_negatives.py — Enrich Dataset with Real-World Cell Phone Variations & Hard Negatives
Generates:
1. Diverse real-world cell phone samples (portrait, landscape, illuminated screen, off screen,
   multi-camera lens back, hands holding phone, indoor lighting, various room backgrounds).
2. Hard negative background images (empty rooms, empty shelves, hand gestures without objects,
   bedsheets, walls) with EMPTY label files to suppress false positive hallucinations (e.g. Lays on bedroom background).
3. Hard negative validation test set for isolated testing.
"""
import os
import cv2
import random
import numpy as np

random.seed(42)
np.random.seed(42)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MERGED_DIR = os.path.join(WORKSPACE_ROOT, "ml", "datasets", "merged")
IMAGES_TRAIN = os.path.join(MERGED_DIR, "images", "train")
LABELS_TRAIN = os.path.join(MERGED_DIR, "labels", "train")
IMAGES_VAL = os.path.join(MERGED_DIR, "images", "val")
LABELS_VAL = os.path.join(MERGED_DIR, "labels", "val")
IMAGES_TEST = os.path.join(MERGED_DIR, "images", "test")
LABELS_TEST = os.path.join(MERGED_DIR, "labels", "test")

os.makedirs(IMAGES_TRAIN, exist_ok=True)
os.makedirs(LABELS_TRAIN, exist_ok=True)
os.makedirs(IMAGES_VAL, exist_ok=True)
os.makedirs(LABELS_VAL, exist_ok=True)
os.makedirs(IMAGES_TEST, exist_ok=True)
os.makedirs(LABELS_TEST, exist_ok=True)

CELL_PHONE_CLASS_ID = 12  # Canonical class ID for Mobile / Cell Phone


def generate_indoor_background(w=640, h=640, bg_type=0):
    """Generates realistic indoor background variations (room walls, shelves, desk, lighting)."""
    img = np.zeros((h, w, 3), dtype=np.uint8)

    if bg_type == 0:
        # Off-white / cream bedroom wall with gradient lighting
        base_color = np.array([210, 220, 225], dtype=np.float32)
        grad = np.linspace(0.85, 1.15, h)[:, None, None]
        img = np.clip(base_color * grad + np.random.normal(0, 4, (h, w, 3)), 0, 255).astype(np.uint8)
        # Window / door frame shadow
        cv2.rectangle(img, (int(w * 0.6), 0), (w, int(h * 0.7)), (180, 190, 195), -1)
        cv2.line(img, (int(w * 0.6), 0), (int(w * 0.6), int(h * 0.7)), (140, 150, 155), 3)

    elif bg_type == 1:
        # Wooden desk / retail shelf surface with grain
        base_color = np.array([80, 120, 160], dtype=np.float32)  # Wood brown in BGR
        x_grad = np.linspace(0.9, 1.1, w)[None, :, None]
        img = np.clip(base_color * x_grad, 0, 255).astype(np.uint8)
        # Wood stripes
        for y in range(0, h, 25):
            cv2.line(img, (0, y), (w, y), (70, 105, 140), 1)

    elif bg_type == 2:
        # Textured fabric / bedsheet pattern (like in user screenshot)
        base_color = np.array([190, 200, 210], dtype=np.float32)
        img[:] = base_color.astype(np.uint8)
        # Subtle texture noise
        noise = np.random.normal(0, 12, (h, w, 3)).astype(np.float32)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        # Some soft pattern spots
        for _ in range(15):
            cx, cy = random.randint(0, w), random.randint(0, h)
            rad = random.randint(15, 45)
            col = (random.randint(140, 180), random.randint(150, 190), random.randint(160, 200))
            cv2.circle(img, (cx, cy), rad, col, -1)

    elif bg_type == 3:
        # Dark retail shelf with ambient light
        base_color = np.array([45, 45, 48], dtype=np.float32)
        grad = np.linspace(0.8, 1.2, h)[:, None, None]
        img = np.clip(base_color * grad, 0, 255).astype(np.uint8)
        # Shelf divider lines
        cv2.line(img, (0, int(h * 0.5)), (w, int(h * 0.5)), (80, 80, 85), 4)

    return img


def render_realistic_phone(canvas, box_params, phone_style="screen_on", with_hand=True):
    """
    Renders a realistic smartphone inside canvas at box_params: (xc, yc, bw, bh).
    Returns exact clamped (xc, yc, bw, bh).
    """
    h, w = canvas.shape[:2]
    xc, yc, bw, bh = box_params
    px = int(xc * w)
    py = int(yc * h)
    pw = int(bw * w)
    ph = int(bh * h)

    x1 = max(0, px - pw // 2)
    y1 = max(0, py - ph // 2)
    x2 = min(w, x1 + pw)
    y2 = min(h, y1 + ph)
    pw = x2 - x1
    ph = y2 - y1

    if pw < 10 or ph < 10:
        return None

    # Outer phone body (black, space gray, silver, or dark blue)
    body_colors = [
        (25, 25, 25),      # Matte Black
        (50, 50, 55),      # Space Gray
        (180, 180, 185),   # Silver
        (85, 55, 30),      # Navy Blue
        (40, 45, 40)       # Midnight Green
    ]
    body_color = random.choice(body_colors)
    corner_radius = max(4, min(pw, ph) // 10)

    # Draw rounded phone chassis
    cv2.rectangle(canvas, (x1, y1), (x2, y2), body_color, -1)
    # Metallic border rim
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (body_color[0] + 30, body_color[1] + 30, body_color[2] + 30), 2)

    # Phone screen or back case
    bezel = max(2, min(pw, ph) // 16)
    sx1, sy1 = x1 + bezel, y1 + bezel
    sx2, sy2 = x2 - bezel, y2 - bezel

    if sx2 > sx1 and sy2 > sy1:
        if phone_style == "screen_on":
            # Screen ON: wallpaper with clock and app icons
            screen_bg = np.array([random.randint(120, 240), random.randint(80, 200), random.randint(40, 180)], dtype=np.uint8)
            canvas[sy1:sy2, sx1:sx2] = screen_bg
            # Screen top status / camera punch hole
            notch_x = (sx1 + sx2) // 2
            notch_y = sy1 + max(3, bezel)
            cv2.circle(canvas, (notch_x, notch_y), max(2, bezel // 2), (10, 10, 10), -1)
            # Clock representation
            if sy2 - sy1 > 40 and sx2 - sx1 > 30:
                cv2.line(canvas, (sx1 + 8, sy1 + 20), (sx2 - 8, sy1 + 20), (250, 250, 250), 2)
            # App icon representation
            for row in range(sy1 + 35, sy2 - 15, 18):
                for col in range(sx1 + 8, sx2 - 8, 16):
                    cv2.rectangle(canvas, (col, row), (min(sx2 - 2, col + 10), min(sy2 - 2, row + 10)),
                                  (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)), -1)

        elif phone_style == "screen_off":
            # Screen OFF: deep black reflective glass
            glass_color = (15, 15, 18)
            canvas[sy1:sy2, sx1:sx2] = glass_color
            # Glare reflection diagonal streak
            cv2.line(canvas, (sx1, sy1 + 10), (min(sx2, sx1 + 30), sy1), (60, 60, 65), 2)

        elif phone_style == "back_camera":
            # Back of phone: Camera bump with multiple lenses
            canvas[sy1:sy2, sx1:sx2] = body_color
            bump_w = max(10, pw // 3)
            bump_h = max(10, ph // 4)
            bx1, by1 = sx1 + 3, sy1 + 3
            bx2, by2 = bx1 + bump_w, by1 + bump_h
            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (20, 20, 20), -1)
            # Lenses
            cv2.circle(canvas, (bx1 + bump_w // 2, by1 + bump_h // 3), max(2, bump_w // 6), (5, 5, 5), -1)
            cv2.circle(canvas, (bx1 + bump_w // 2, by1 + 2 * bump_h // 3), max(2, bump_w // 6), (5, 5, 5), -1)
            # Flash
            cv2.circle(canvas, (bx2 - 4, by1 + bump_h // 2), 2, (200, 200, 180), -1)

    # Optional hand holding phone (simulating thumb and fingers at side)
    if with_hand:
        skin_tones = [
            (145, 175, 215),  # Medium skin in BGR
            (110, 140, 190),  # Olive
            (80, 110, 160),   # Deeper brown
            (170, 200, 240)   # Fair
        ]
        skin = random.choice(skin_tones)
        # Thumb gripping left or right side
        side = random.choice(["left", "right"])
        if side == "left" and x1 > 15:
            thumb_y = (y1 + y2) // 2
            cv2.ellipse(canvas, (x1 + 6, thumb_y), (14, 22), 20, 0, 360, skin, -1)
            cv2.ellipse(canvas, (x1 + 6, thumb_y), (14, 22), 20, 0, 360, (skin[0] - 25, skin[1] - 25, skin[2] - 25), 1)
        elif side == "right" and x2 < w - 15:
            thumb_y = (y1 + y2) // 2
            cv2.ellipse(canvas, (x2 - 6, thumb_y), (14, 22), -20, 0, 360, skin, -1)
            cv2.ellipse(canvas, (x2 - 6, thumb_y), (14, 22), -20, 0, 360, (skin[0] - 25, skin[1] - 25, skin[2] - 25), 1)

    # Calculate exact bounding box in YOLO format
    actual_xc = (x1 + x2) / 2.0 / w
    actual_yc = (y1 + y2) / 2.0 / h
    actual_bw = (x2 - x1) / float(w)
    actual_bh = (y2 - y1) / float(h)
    return actual_xc, actual_yc, actual_bw, actual_bh


def generate_cell_phone_dataset(num_train=90, num_val=25, num_test=15):
    """Generates enriched cell phone samples across train, val, and test splits."""
    splits = [
        ("train", num_train, IMAGES_TRAIN, LABELS_TRAIN),
        ("val", num_val, IMAGES_VAL, LABELS_VAL),
        ("test", num_test, IMAGES_TEST, LABELS_TEST)
    ]

    print("\n--- Generating Enriched Cell Phone Dataset ---")
    for split_name, count, img_dir, lbl_dir in splits:
        created = 0
        for i in range(count):
            w, h = 640, 640
            bg_type = random.choice([0, 1, 2, 3])
            canvas = generate_indoor_background(w, h, bg_type)

            # Phone variation: portrait (e.g. 0.18 x 0.35) or landscape (0.35 x 0.18)
            is_portrait = random.random() < 0.75
            if is_portrait:
                bw = random.uniform(0.14, 0.28)
                bh = bw * random.uniform(1.8, 2.2)
            else:
                bh = random.uniform(0.14, 0.28)
                bw = bh * random.uniform(1.8, 2.2)

            xc = random.uniform(0.25, 0.75)
            yc = random.uniform(0.30, 0.75)

            style = random.choice(["screen_on", "screen_off", "back_camera"])
            with_hand = random.random() < 0.65

            res = render_realistic_phone(canvas, (xc, yc, bw, bh), phone_style=style, with_hand=with_hand)
            if res is None:
                continue

            r_xc, r_yc, r_bw, r_bh = res
            fname = f"real_cellphone_{split_name}_{i:03d}"
            img_path = os.path.join(img_dir, f"{fname}.jpg")
            lbl_path = os.path.join(lbl_dir, f"{fname}.txt")

            cv2.imwrite(img_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
            with open(lbl_path, "w", encoding="utf-8") as f:
                f.write(f"{CELL_PHONE_CLASS_ID} {r_xc:.6f} {r_yc:.6f} {r_bw:.6f} {r_bh:.6f}\n")
            created += 1

        print(f"  [OK] Generated {created} rich Cell Phone samples in {split_name} split.")


def generate_hard_negatives(num_train=40, num_val=15, num_test=10):
    """
    Generates hard negative background images (empty room, empty shelf, hands without products).
    Crucially, these have EMPTY label files (.txt with 0 lines).
    This tells YOLO that empty rooms, background shadows, and empty hands MUST NOT be classified as Lays or any item!
    """
    splits = [
        ("train", num_train, IMAGES_TRAIN, LABELS_TRAIN),
        ("val", num_val, IMAGES_VAL, LABELS_VAL),
        ("test", num_test, IMAGES_TEST, LABELS_TEST)
    ]

    print("\n--- Generating Hard Negative Backgrounds (0-object scenes) ---")
    for split_name, count, img_dir, lbl_dir in splits:
        created = 0
        for i in range(count):
            w, h = 640, 640
            bg_type = random.choice([0, 1, 2, 3])
            canvas = generate_indoor_background(w, h, bg_type)

            # Sometimes add empty hand gesture or empty shelf divider
            if random.random() < 0.5:
                # Empty hand reaching into frame (no product!)
                hx = random.randint(int(w * 0.4), int(w * 0.7))
                hy = random.randint(int(h * 0.5), int(h * 0.8))
                skin = (130, 160, 210)
                cv2.ellipse(canvas, (hx, hy), (25, 45), random.randint(-30, 30), 0, 360, skin, -1)
                for f_off in [-18, -6, 6, 18]:
                    cv2.ellipse(canvas, (hx + f_off, hy - 25), (7, 18), 0, 0, 360, skin, -1)

            fname = f"hard_negative_{split_name}_{i:03d}"
            img_path = os.path.join(img_dir, f"{fname}.jpg")
            lbl_path = os.path.join(lbl_dir, f"{fname}.txt")

            cv2.imwrite(img_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])
            # Empty file: 0 bounding boxes!
            with open(lbl_path, "w", encoding="utf-8") as f:
                f.write("")
            created += 1

        print(f"  [OK] Generated {created} Hard Negative background samples in {split_name} split.")


if __name__ == "__main__":
    generate_cell_phone_dataset()
    generate_hard_negatives()
    print("\n[SUCCESS] Dataset successfully enriched with rich Cell Phone samples and Hard Negatives.")
