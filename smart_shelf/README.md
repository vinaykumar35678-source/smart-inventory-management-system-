# Academic Student Project: Smart Inventory Vision System

This project is a complete, pure Python implementation of the Smart Shelf Inventory System using Flask.

## Objectives Achieved
1. **Automate Product Detection**: Uses OpenCV and YOLO11n to identify products.
2. **Real-Time Inventory Tracking**: Flask-SocketIO pushes real-time inventory updates and stock drops to the dashboard.
3. **Detect Product Removal**: Implements a differential detection mechanism that compares sequential frames to identify when items are taken.
4. **User-Friendly Dashboard**: Built with HTML, CSS, and Jinja2 templates for an intuitive interface.
5. **Reduce Human Effort**: Features automated low-stock alerts, an event log, and Excel export functionality.

## Setup Instructions
1. Ensure Python 3.9+ is installed.
2. Activate the virtual environment (`venv`).
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`

*Designed and implemented entirely in Python by a student developer.*
