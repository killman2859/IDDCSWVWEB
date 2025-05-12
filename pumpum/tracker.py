from datetime import datetime
from database import Database

class DroneDetectionLogger:
    def __init__(self):
        self.db = Database()
        self.detected_drones = {}
        self.last_drone_id = self.db.get_last_drone_id()

    def log_drone(self, drone_id, begin_time, end_time, begin_distance, end_distance):
        #логирует данные в бд
        time_diff = (end_time - begin_time).total_seconds()
        if time_diff > 1.8:
            v_ave = (begin_distance - end_distance) / time_diff
            self.db.insert_log(
                drone_id,
                begin_time.isoformat(),
                end_time.isoformat(),
                begin_distance,
                end_distance,
                v_ave
            )

    def update_detection(self, detections):
        #oбновляет данные и логирует
        current_time = datetime.now()
        detected_ids = set()

        for detection in detections:
            drone_id = self.last_drone_id + 1
            detected_ids.add(drone_id)

            if drone_id not in self.detected_drones:
                self.detected_drones[drone_id] = {
                    'begin_time': current_time,
                    'begin_distance': detection['distance']
                }
            else:
                self.detected_drones[drone_id]['end_time'] = current_time
                self.detected_drones[drone_id]['end_distance'] = detection['distance']

        for drone_id in list(self.detected_drones.keys()):
            if drone_id not in detected_ids:
                if (current_time - self.detected_drones[drone_id].get('end_time', current_time)).total_seconds() > 7:
                    self.log_drone(
                        drone_id,
                        self.detected_drones[drone_id]['begin_time'],
                        self.detected_drones[drone_id]['end_time'],
                        self.detected_drones[drone_id]['begin_distance'],
                        self.detected_drones[drone_id]['end_distance']
                    )
                    del self.detected_drones[drone_id]
                    self.last_drone_id = drone_id