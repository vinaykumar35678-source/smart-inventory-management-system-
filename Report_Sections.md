# Academic Project Report: Smart Inventory Vision System
**Designed by:** Student Developer
## 1. Introduction, Problem Statement, and Objectives

### Introduction
Inventory management is a critical component for the success and profitability of small to medium-sized retail shops and grocery stores. However, traditional inventory tracking methods are labor-intensive, error-prone, and often fail to provide real-time insights into stock levels. The "Smart Inventory Vision" system is designed to modernize this process by leveraging computer vision and real-time web technologies to automate shelf monitoring and stock tracking, ensuring seamless and non-intrusive inventory management.

### Problem Statement
Most local grocery shops and retail stores rely on manual stock counting or point-of-sale (POS) barcode scanning to track inventory. These methods only update inventory status at the time of checkout or during manual stock audits, leaving a significant "blind spot" regarding real-time shelf availability. Consequently, store owners often face stockouts (leading to lost sales and dissatisfied customers) or overstocking (leading to increased holding costs and waste). There is a pressing need for a proactive, automated, and real-time inventory monitoring solution that operates independently of manual checkout processes.

### Objectives
*   **Automate Object Detection:** To utilize a state-of-the-art computer vision model (YOLOv8) to continuously monitor shelves and identify products correctly.
*   **Real-Time Tracking:** To automatically detect when items are removed from the shelf and decrement the respective stock count in the centralized database in real-time.
*   **Proactive Alerting:** To generate immediate, automated alerts when a product's stock level falls below a predefined threshold, enabling timely restocking.
*   **Centralized Management Dashboard:** To provide an intuitive, responsive web-based user interface where store managers can view real-time analytics, manage the product catalog, and monitor staff activities.
*   **Reduce Human Error:** To minimize reliance on manual data entry and visual inspection, thereby increasing inventory accuracy.

---

## 2. Proposed Model

The proposed "Smart Inventory Vision" model operates by transforming standard camera feeds into intelligent inventory sensors. 

**How it works:**
1.  **Continuous Monitoring:** Cameras facing the store shelves capture continuous video feeds.
2.  **Detection and Classification:** A backend server running the YOLOv8 object detection model processes these video frames. The model is configured to detect and classify various grocery and retail items (e.g., fruits, dairy, electronics, stationery).
3.  **Differential Logic:** The system employs a "differential count" algorithm. It compares the objects detected in the current frame against the objects detected in the previous frame. If a previously detected item is no longer present, the system registers a "removal event."
4.  **Database Synchronization:** Upon detecting a removal, the system instantly updates the product's stock count in the relational database.
5.  **Threshold Logic & Real-Time Broadcasting:** If the new stock quantity drops below the product's assigned minimum threshold, a low-stock alert is created. Simultaneously, the backend broadcasts these updates (both the stock decrement and the alert) via a WebSocket connection.
6.  **Dynamic UI Feedback:** The frontend web application receives these WebSocket messages and instantly updates the visual dashboard—updating charts, decrementing stock tables, and displaying toast notifications—without requiring the user to refresh the page.

---

## 3. System Design and Architecture

The platform is designed using a modern decoupled client-server architecture, divided into three fundamental layers: the Frontend (Client App), the Backend (API & AI Processing), and the Database layer.

### High-Level Architecture
*   **Hardware Layer:** IP Cameras or Webcams monitoring the shelves.
*   **Application Server:** A monolithic Flask (Python) application handling routing, API endpoints, AI processing, and rendering templates.
*   **Frontend Client:** A browser-based interface rendered dynamically via Jinja2 templates, utilizing vanilla JavaScript and Socket.IO for real-time updates.

### Component Details

**1. Frontend Layer (User Interface)**
*   **Framework:** HTML5, CSS3 (Bootstrap/Tailwind), and Vanilla JavaScript.
*   **Routing & UI:** Server-side routing using Flask, dynamically rendering Jinja2 templates (`inventory.html`, `dashboard.html`).
*   **Data Visualization:** Chart.js or Recharts equivalent integrated via JS for rendering dynamic analytics and sales/stock graphs.
*   **Communication:** Standard form submissions, Fetch API for simple REST calls, and Socket.IO client for subscribing to real-time events.

**2. Backend Layer (Server, API & AI)**
*   **Framework:** Flask (Python), chosen for its simplicity, extensibility, and suitability for student projects.
*   **Computer Vision Module (`detection.py`):** Uses OpenCV for frame acquisition and Ultralytics YOLOv8 for inference. It maps standard COCO dataset classes to specific inventory categories.
*   **Inventory Logic Engine (`inventory_logic.py`):** Maintains the previous state of the shelf. It handles the extraction of removed quantities, commits event logs, calculates remaining stock, and evaluates threshold rules.
*   **WebSocket Manager:** Uses Flask-SocketIO to manage active connections with frontend clients, allowing the server to push real-time JSON payloads containing inventory updates and low-stock alerts.
*   **Security:** Flask-Session for authentication and role-based access control (Admin vs. User). Passwords are securely hashed using bcrypt (via passlib).

**3. Database Layer**
*   **Database Engine:** SQLite (managed via SQLAlchemy ORM for easy schema migrations and queries).
*   **Core Schemas (`models.py`):**
    *   `User`: Stores credentials, roles, and profiles.
    *   `Product`: Stores catalog details, current stock counts, pricing, and specific restock thresholds.
    *   `Event`: An audit log of every detected removal, including timestamps and confidence scores from the AI model.
    *   `Alert`: Tracks low-stock and out-of-stock warnings, including boolean flags for resolution status.

### Data Flow Diagram (Conceptual)
1.  **Capture:** Camera -> Raw Video Frame
2.  **Inference:** Frame -> OpenCV -> YOLOv8 Model -> Bounding Boxes & Class Labels
3.  **Logic:** Class Labels -> Differential Counter -> Stock Decrement 
4.  **Storage:** Database (Update `products` table, Insert into `events` and `alerts` tables)
5.  **Broadcast:** Flask-SocketIO -> Emits `{"type": "removal", "stock": N}` or `{"type": "alert"}`
6.  **Display:** Frontend HTML/JS App -> Receives UI state update -> Re-renders Dashboard and Tables dynamically.
