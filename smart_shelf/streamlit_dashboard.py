"""
streamlit_dashboard.py — Streamlit Interactive Smart Shelf Dashboard
Usage:  streamlit run streamlit_dashboard.py
"""
import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import cv2
from ultralytics import YOLO
from inventory_logic import process_addition, process_removal
from detection import detect_from_frame, compare_frames

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

st.set_page_config(
    page_title="Smart Shelf Inventory Dashboard",
    page_icon="📦",
    layout="wide"
)

def get_db_connection():
    return sqlite3.connect(DB_PATH)

# --- HEADER & REFRESH ---
st.title("📦 Smart Shelf Real-Time Vision & Inventory Dashboard")
st.markdown("Automated retail shelf monitoring powered by **YOLO11** & **ByteTrack**.")

col_btn1, col_btn2 = st.columns([1, 6])
with col_btn1:
    if st.button("🔄 Refresh Data"):
        st.rerun()

# --- METRIC CARDS ---
conn = get_db_connection()
products_df = pd.read_sql_query("SELECT * FROM products", conn)
events_df = pd.read_sql_query("SELECT * FROM events ORDER BY timestamp DESC", conn)
alerts_df = pd.read_sql_query("SELECT * FROM alerts ORDER BY timestamp DESC", conn)
conn.close()

total_items = products_df['stock'].sum() if not products_df.empty else 0
total_products = len(products_df) if not products_df.empty else 0

total_added = events_df[events_df['event_type'] == 'ADDITION']['quantity_removed'].abs().sum() if ('event_type' in events_df.columns and not events_df.empty) else 0
total_removed = events_df[events_df['event_type'] == 'REMOVAL']['quantity_removed'].sum() if ('event_type' in events_df.columns and not events_df.empty) else 0
low_stock_count = len(products_df[products_df['stock'] <= products_df['threshold']]) if not products_df.empty else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Items on Shelf", int(total_items))
m2.metric("Product Types", total_products)
m3.metric("Total Added", int(total_added))
m4.metric("Total Removed", int(total_removed))
m5.metric("Low Stock Alerts", low_stock_count, delta_color="inverse")

st.divider()

# --- MAIN CONTENT LAYOUT ---
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader("📊 Live Inventory Stock Level")
    if not products_df.empty:
        fig_stock = px.bar(
            products_df,
            x='name',
            y='stock',
            color='stock',
            color_continuous_scale='bluered',
            labels={'name': 'Product Name', 'stock': 'Current Units'},
            text='stock'
        )
        fig_stock.update_layout(xaxis_title=None, template="plotly_dark")
        st.plotly_chart(fig_stock, use_container_width=True)
    else:
        st.info("No product data recorded yet.")

    st.subheader("📈 Movement History")
    if not events_df.empty:
        events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
        fig_events = px.histogram(
            events_df,
            x='timestamp',
            y='quantity_removed',
            color='product_name',
            barmode='group',
            labels={'timestamp': 'Time', 'quantity_removed': 'Quantity'},
            template="plotly_dark"
        )
        st.plotly_chart(fig_events, use_container_width=True)

with right_col:
    st.subheader("⚠️ Active Low-Stock Alerts")
    if not alerts_df.empty:
        for idx, row in alerts_df.head(5).iterrows():
            st.warning(f"**{row['timestamp']}**: {row['message']}")
    else:
        st.success("All stock levels normal.")

    st.subheader("📋 Recent Detection Log")
    if not events_df.empty:
        st.dataframe(
            events_df[['timestamp', 'product_name', 'quantity_removed', 'confidence']].head(10),
            use_container_width=True
        )

# --- LIVE CAMERA FEED SECTION ---
st.divider()
st.subheader("📹 Live Camera Feed & Vision Engine")

run_webcam = st.checkbox("Activate Webcam Feed")
FRAME_WINDOW = st.image([])

if run_webcam:
    cap = cv2.VideoCapture(0)

    while run_webcam:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to read webcam stream.")
            break

        detected = detect_from_frame(frame)
        current_labels = [item['label'] for item in detected if item.get('category') == 'item']
        
        added, removed = compare_frames(current_labels)
        for prod_name, qty in added.items():
            process_addition(prod_name, qty, 0.85)
        for prod_name, qty in removed.items():
            process_removal(prod_name, qty, 0.85)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame_rgb)
    cap.release()
