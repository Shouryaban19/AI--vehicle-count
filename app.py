from flask import Flask, render_template, Response, request, jsonify, send_file
import cv2
import numpy as np
from ultralytics import YOLO
from sort import *
import os
import time
import csv

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

model = YOLO('yolov8n.pt')

with open('classes.txt', 'r') as f:
    classnames = f.read().splitlines()

tracker = Sort(max_age=30)

vehicle_ids = set()

car_count = 0
bus_count = 0
truck_count = 0
bike_count = 0

video_path = None
csv_file = 'logs.csv'


# ============== RESET COUNTS =================
def reset_counts():
    global vehicle_ids, car_count, bus_count, truck_count, bike_count
    vehicle_ids = set()
    car_count = 0
    bus_count = 0
    truck_count = 0
    bike_count = 0

    # Clear CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Type', 'Timestamp'])


# ============== VIDEO PROCESSING =================
def generate_frames():
    global car_count, bus_count, truck_count, bike_count

    cap = cv2.VideoCapture(video_path)

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.resize(frame, (640, 360))

        detections = np.empty((0, 5))
        results = model(frame, stream=True)

        detected_vehicles = {}

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = classnames[cls]

                if label in ['car', 'bus', 'truck', 'motorcycle'] and conf > 0.6:
                    detections = np.vstack((detections, [x1, y1, x2, y2, conf]))
                    detected_vehicles[(x1, y1, x2, y2)] = label

        results_tracker = tracker.update(detections)

        for res in results_tracker:
            x1, y1, x2, y2, obj_id = map(int, res)

            vehicle_type = None
            for box, vtype in detected_vehicles.items():
                if x1 >= box[0] and y1 >= box[1] and x2 <= box[2] and y2 <= box[3]:
                    vehicle_type = vtype
                    break

            if vehicle_type and obj_id not in vehicle_ids:
                vehicle_ids.add(obj_id)
                log_vehicle(obj_id, vehicle_type)

                if vehicle_type == 'car':
                    car_count += 1
                elif vehicle_type == 'bus':
                    bus_count += 1
                elif vehicle_type == 'truck':
                    truck_count += 1
                elif vehicle_type == 'motorcycle':
                    bike_count += 1

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(frame, f'{vehicle_type} ID:{obj_id}', (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ================= ROUTES =================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    global video_path
    file = request.files['video']

    reset_counts()

    path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(path)
    video_path = path

    return jsonify({"status": "uploaded"})


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stats')
def stats():
    return jsonify({
        "total": len(vehicle_ids),
        "cars": car_count,
        "buses": bus_count,
        "trucks": truck_count,
        "bikes": bike_count
    })


@app.route('/download_csv')
def download_csv():
    return send_file(csv_file, as_attachment=True)


def log_vehicle(obj_id, vtype):
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([obj_id, vtype, time.strftime('%Y-%m-%d %H:%M:%S')])


if __name__ == '__main__':
    app.run(debug=True)