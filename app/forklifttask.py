#forklidttask.py
import math
import time
import cv2
from ultralytics import YOLO

from app.database import SessionLocal
from app.models import Incident
from .celery import celery_app
from . import crud
from datetime import datetime, timezone
from app.celery import celery_app
from app.commontasks import initialize_camera, process_frame, should_skip_detection, detection_cache


def compute_center(box):
    """Compute the center (x, y) of a bounding box."""
    center_x = (box[0] + box[2]) / 2
    center_y = (box[1] + box[3]) / 2
    return (center_x, center_y)

def compute_euclidean_distance(box_a, box_b):
    """Compute the Euclidean distance between the centers of two bounding boxes."""
    center_a = compute_center(box_a)
    center_b= compute_center(box_b)
    
    distance = math.sqrt((center_a[0] - center_b[0]) ** 2 + (center_a[1] - center_b[1]) ** 2)
    return distance

def check_proximity(person_box, forklift_box, threshold_distance=50):
    """Check if the Euclidean distance between the centers of a person and a forklift is less than a threshold."""
    distance = compute_euclidean_distance(person_box, forklift_box)
    return distance < threshold_distance


def handle_proximity_detections(model, frame, confidence, proximity_threshold=350):
    results = model(frame)
    detections = results[0].boxes
    person_boxes = []
    forklift_boxes = []
    detected_classes = {}

    for det in detections:
        try:
            box = det.xyxy[0].tolist() 
            conf = det.conf[0].item()
            cls = int(det.cls[0].item())
            class_name = model.names[cls]

            if conf >= confidence:
                detected_classes[class_name] = conf

                pt1 = (int(box[0]), int(box[1]))
                pt2 = (int(box[2]), int(box[3]))
                cv2.rectangle(frame, pt1, pt2, (255, 0, 0), 2)
                label = f'{class_name} {conf:.2f}'
                cv2.putText(frame, label, (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)  # Draw label

                if class_name == 'person':
                    person_boxes.append(box)
                elif class_name == 'forklift':
                    forklift_boxes.append(box)

        except Exception as e:
            print(f"Error processing detection: {e}")
            continue

    # Check for proximity between persons and forklifts
    for person_box in person_boxes:
        for forklift_box in forklift_boxes:
            if check_proximity(person_box, forklift_box, proximity_threshold):
                print("Person detected near a forklift!")
                return frame, True, detected_classes

    return frame, False, detected_classes

def save_proximity_detection(db, buffer, record_id):
    current_timestamp = datetime.now(timezone.utc)
    class_name = 'person_forklift_proximity'
    cache_key = f"{record_id}_{class_name}"

    if should_skip_detection(cache_key, db, record_id, class_name, current_timestamp, debounce_time_seconds=1*60):
        return

    detection_cache[cache_key] = current_timestamp

    db_detection = Incident(
        recording_id=record_id,
        class_name=class_name,
        confidence=0.0,
        bbox='',
        frame=buffer.tobytes(),
        timestamp=current_timestamp
    )

    try:
        db.add(db_detection)
        db.commit()
        print(f"Proximity incident saved to DB: {db_detection}")
    except Exception as e:
        print(f"Error saving to DB: {e}")
        db.rollback()


@celery_app.task(bind=True)
def run_proximity_detection(self, camera_id, model_path, record_id):
    db = SessionLocal()

    try:
        model = YOLO(model_path)
        cap = initialize_camera(crud.get_camera_by_id(db, camera_id).ipaddress, "./yolomodels/Forklift_move.mp4")
        confidence = (crud.get_recording(db=db, recording_id=record_id).confidence / 100) or crud.get_zone_confidence_level(db, camera_id)
        
        while True:
            start_time = time.time()

            frame = process_frame(cap)
            frame, proximity_detected, detected_classes = handle_proximity_detections(model, frame, confidence)

            if proximity_detected:
                buffer = cv2.imencode('.jpg', frame)[1]
                save_proximity_detection(db, buffer, record_id)

            elapsed_time = time.time() - start_time
            time.sleep(max(0, 0.1 - elapsed_time))

    except Exception as e:
        cap.release()
        raise self.retry(exc=e, countdown=10)

    finally:
        db.close()


# Register tasks in globals()
globals()['run_proximity_detection'] = run_proximity_detection