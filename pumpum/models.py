import cv2
import numpy as np
from ultralytics import YOLO
from filterpy.kalman import KalmanFilter


class DroneTracker:
    def __init__(self, model_path, focal_length=430, drone_real_size=0.2, confidence_threshold=50):
        self.model = YOLO(model_path)
        self.focal_length = focal_length
        self.drone_real_size = drone_real_size
        self.confidence_threshold = confidence_threshold

        # Инициализация фильтра Калмана
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.kf.x = np.array([0, 0, 0, 0])
        self.kf.F = np.array([[1, 1, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, 1, 1],
                              [0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0],
                              [0, 0, 1, 0]])
        self.kf.P *= 1000
        self.kf.R *= 5

    def detect_drones(self, frame):
        results = self.model(frame)
        detections = []

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                label = self.model.names[cls]
                confidence = box.conf[0] * 100

                if label.lower() == "drone" and confidence >= self.confidence_threshold:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    width = x2 - x1

                    # Фильтрация позиции
                    self.kf.predict()
                    self.kf.update([(x1 + x2) / 2, (y1 + y2) / 2])
                    filtered_pos = self.kf.x[:2]

                    # Расчет расстояния
                    distance = (self.drone_real_size * self.focal_length) / width

                    detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                        'distance': distance,
                        'confidence': confidence,
                        'filtered_pos': filtered_pos
                    })

        return detections