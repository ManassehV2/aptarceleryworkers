#ppetask.py
import datetime
import time
import cv2
from ultralytics import YOLO
from app import crud
from app.database import SessionLocal
from app.models import Incident
from .celery import celery_app
from app.celery import celery_app
from app.commontasks import initialize_camera, process_frame, should_skip_detection, detection_cache



def is_within_person_box(ppe_box, person_box):
    """Check if the PPE box is inside the person box."""
    ppe_x1, ppe_y1, ppe_x2, ppe_y2 = ppe_box
    person_x1, person_y1, person_x2, person_y2 = person_box

    return (ppe_x1 >= person_x1 and ppe_y1 >= person_y1 and
            ppe_x2 <= person_x2 and ppe_y2 <= person_y2)


def handle_detections_with_multiple_persons(model, frame, zoneconf, zonescenarios):
    results = model(frame)
    detections = results[0].boxes
    detected_classes = {}
    person_boxes = []

    # Step 1: Detect all persons and store their bounding boxes
    for det in detections:
        try:
            box = det.xyxy[0].tolist()
            conf = det.conf[0].item()
            cls = int(det.cls[0].item())
            class_name = model.names[cls]

            if conf >= zoneconf:
                detected_classes[class_name] = conf
                
                if class_name == 'person':
                    person_boxes.append({
                        'box': box,  
                        'missing_ppe': set(zonescenarios), 
                        'detected_ppe': [] 
                    })
                    pt1 = (int(box[0]), int(box[1]))
                    pt2 = (int(box[2]), int(box[3]))
                    cv2.rectangle(frame, pt1, pt2, (255, 0, 0), 2)
                    label = f'Person {conf:.2f}'
                    cv2.putText(frame, label, (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        except Exception as e:
            print(f"Error processing person detection: {e}")
            continue

    if not person_boxes:
        print("No persons detected in the frame. Skipping PPE detection.")
        return frame, [], detected_classes

    # Step 2: Detect PPE and associate with corresponding person bounding boxes
    for det in detections:
        try:
            box = det.xyxy[0].tolist() 
            conf = det.conf[0].item()
            cls = int(det.cls[0].item())
            class_name = model.names[cls]

            if conf >= zoneconf and class_name in zonescenarios:
                for person in person_boxes:
                    person_box = person['box']
                    if is_within_person_box(box, person_box):
                        pt1 = (int(box[0]), int(box[1]))
                        pt2 = (int(box[2]), int(box[3]))
                        cv2.rectangle(frame, pt1, pt2, (0, 255, 0), 2)  
                        label = f'{class_name} {conf:.2f}'
                        cv2.putText(frame, label, (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
        
                        person['detected_ppe'].append(class_name)
                        if class_name in person['missing_ppe']:
                            person['missing_ppe'].remove(class_name)

        except Exception as e:
            print(f"Error processing PPE detection: {e}")
            continue

    missing_classes = []
    for person in person_boxes:
        if person['missing_ppe']:
            missing_classes.append({
                'person_box': person['box'],
                'missing_ppe': list(person['missing_ppe'])
            })

    return frame, missing_classes, detected_classes

def save_detections(db, missing_classes, buffer, record_id, detected_classes):
    debounce_time_seconds = 1 * 60  
    current_timestamp = datetime.datetime.now(datetime.timezone.utc)

    if missing_classes:
        missing_ppe_list = [','.join(person['missing_ppe']) for person in missing_classes if person['missing_ppe']]
        
        if not missing_ppe_list:
            return  
        
        
        cache_key = f"{record_id}_{','.join(missing_ppe_list)}"  

        if should_skip_detection(cache_key, db, record_id, cache_key, current_timestamp, debounce_time_seconds):
            return

        save_detection(db, buffer, record_id, missing_ppe_list, current_timestamp, cache_key, detected_classes)


def save_detection(db, buffer, record_id, missing_classes, current_timestamp, cache_key, detected_classes):
    detection_cache[cache_key] = current_timestamp

    missing_classes_str = ','.join(missing_classes)
    
    db_detection = Incident(
        recording_id=record_id,
        class_name=missing_classes_str,  
        confidence=0.0,  
        bbox='', 
        frame=buffer.tobytes(),
        timestamp=current_timestamp
    )

    try:
        db.add(db_detection)
        db.commit()
        print(f"Missing detection saved to DB: {db_detection}")
    except Exception as e:
        print(f"Error saving to DB: {e}")
        db.rollback()

@celery_app.task(bind=True)
def run_ppe_detection(self, camera_id, model_path, record_id):
    db = SessionLocal()
    
    frame_skip_interval = 20
    frame_count = 0

    try:
        model = YOLO(model_path)
        cap = initialize_camera(crud.get_camera_by_id(db, camera_id).ipaddress, "./yolomodels/testvideo.mp4")
        confidence = crud.get_recording(db=db, recording_id=record_id).confidence / 100 or crud.get_zone_confidence_level(db, camera_id)
        recordingscenarios = crud.get_zone_scenario(db=db, recording_id=record_id)
        
        while True:
            start_time = time.time()

            ret, frame = cap.read()  
            if not ret:
                break 

            frame_count += 1

            if frame_count % frame_skip_interval != 0:
                continue

            frame = process_frame(cap)
            frame, missing_classes, detected_classes = handle_detections_with_multiple_persons(model, frame, confidence, recordingscenarios)

            buffer = cv2.imencode('.jpg', frame)[1]
            save_detections(db, missing_classes, buffer, record_id, detected_classes)

            elapsed_time = time.time() - start_time
            time.sleep(max(0, 0.1 - elapsed_time))

    except Exception as e:
        cap.release()
        raise self.retry(exc=e, countdown=10)  

    finally:
        db.close()



globals()['run_ppe_detection'] = run_ppe_detection
