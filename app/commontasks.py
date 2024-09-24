from collections import defaultdict
from sqlalchemy import desc
import cv2
from app.models import Incident
from datetime import timezone

# Initialize a cache to store the last detection timestamp for each class and recording
detection_cache = defaultdict(lambda: None)

import cv2
import time

def initialize_camera(ip_cam_url=None, video_file_path=None, retries=3, delay=2):
    cap = None
    
    def try_open_source(source, source_type):
        for attempt in range(retries):
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                print(f"Connected to {source_type} at {source} after {attempt + 1} attempt(s).")
                return cap
            else:
                print(f"Failed to connect to {source_type} at {source}. Retrying... ({attempt + 1}/{retries})")
                time.sleep(delay)
        return None
    
    if ip_cam_url is not None:
        cap = try_open_source(ip_cam_url, "IP camera")
        if cap is not None:
            return cap
    
    if video_file_path is not None:
        cap = try_open_source(video_file_path, "video file")
        if cap is not None:
            return cap
    
    raise RuntimeError("Could not open IP camera or video file after retrying.")




def process_frame(cap):
    ret, frame = cap.read()
    if not ret:
        raise OSError("Failed to capture frame from webcam")
    frame = cv2.resize(frame, (640, 480))
    return frame


def get_last_detection_timestamp(cache_key, db, record_id, class_name):
    # Check cache first
    last_timestamp = detection_cache.get(cache_key)

    if not last_timestamp:
        # If not in cache, check the database
        last_detection = db.query(Incident).filter_by(
            recording_id=record_id,
            class_name=class_name
        ).order_by(desc(Incident.timestamp)).first()

        if last_detection:
            last_timestamp = last_detection.timestamp
            detection_cache[cache_key] = last_timestamp  # Update cache with DB timestamp

    return last_timestamp


def should_skip_detection(cache_key, db, record_id, class_name, current_timestamp, debounce_time_seconds):
    last_timestamp = get_last_detection_timestamp(cache_key, db, record_id, class_name)

    if last_timestamp:
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        
        if (current_timestamp - last_timestamp).total_seconds() < debounce_time_seconds:
            print(f"Skipping detection for {class_name} as it occurred within the debounce time.")
            return True

    return False
