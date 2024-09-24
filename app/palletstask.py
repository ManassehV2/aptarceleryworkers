#palletstask.py
from collections import defaultdict
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


def save_pallet_detection(db, buffer, record_id, class_name, confidence, current_timestamp):
    cache_key = f"{record_id}_{class_name}"
    if should_skip_detection(cache_key, db, record_id, class_name, current_timestamp, debounce_time_seconds=60):
        print(f"Skipping pallet detection for {class_name} due to debounce.")
        return

    detection_cache[cache_key] = current_timestamp

    db_detection = Incident(
        recording_id=record_id,
        class_name=class_name,  
        confidence=confidence, 
        bbox='',
        frame=buffer.tobytes(),
        timestamp=current_timestamp
    )

    try:
        db.add(db_detection)
        db.commit()
        print(f"{class_name} detection saved to DB with confidence {confidence:.2f}: {db_detection}")
    except Exception as e:
        print(f"Error saving to DB: {e}")
        db.rollback()


@celery_app.task(bind=True)
def run_pallet_detection(self, camera_id, model_path, record_id):
    db = SessionLocal() 

    try:
        model = YOLO(model_path)
        cap = initialize_camera(crud.get_camera_by_id(db, camera_id).ipaddress, "./yolomodels/IMG_0454.MOV")
        confidence_threshold = (crud.get_recording(db=db, recording_id=record_id).confidence / 100) or crud.get_zone_confidence_level(db, camera_id)

        while True:
            start_time = time.time()

            frame = process_frame(cap) 
            results = model(frame)
            detections = results[0].boxes
            bad_pallet_detected = False
            detected_confidence = 0.0

            for det in detections:
                box = det.xyxy[0].tolist()  
                conf = det.conf[0].item()
                cls = int(det.cls[0].item())
                class_name = model.names[cls]

                if conf >= confidence_threshold and class_name == 'Pallets_bad':
                    bad_pallet_detected = True
                    detected_confidence = conf 

                    current_timestamp = datetime.now(timezone.utc)
                    cache_key = f"{record_id}_{class_name}"

                    if should_skip_detection(cache_key, db, record_id, class_name, current_timestamp, debounce_time_seconds=60):
                        print(f"Skipping detection for {class_name} due to debounce.")
                        continue  

                    pt1 = (int(box[0]), int(box[1]))
                    pt2 = (int(box[2]), int(box[3]))  
                    cv2.rectangle(frame, pt1, pt2, (0, 0, 255), 2)
                    label = f'{class_name} {conf:.2f}'
                    cv2.putText(frame, label, (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)  # Label in red

                    # Save to DB if a bad pallet is detected
                    buffer = cv2.imencode('.jpg', frame)[1]
                    save_pallet_detection(db, buffer, record_id, class_name, detected_confidence, current_timestamp)

            elapsed_time = time.time() - start_time
            time.sleep(max(0, 0.1 - elapsed_time))

    except Exception as e:
        cap.release()
        raise self.retry(exc=e, countdown=10)

    finally:
        db.close()


globals()['run_pallet_detection'] = run_pallet_detection