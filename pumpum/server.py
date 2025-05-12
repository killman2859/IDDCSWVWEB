import threading
from flask import Flask, render_template, request, redirect, Response, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from data import db_session
from data.Forms.login_form import LoginForm
from data.Forms.registration_form import RegistrationForm
from data.users import User
from models import DroneTracker
import cv2
import time
from datetime import datetime
import json
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

# Глобальное состояние системы
system_state = {
    'processing': False,
    'settings': {
        'drone_size': 0.2,
        'confidence': 50,
        'focal_length': 430
    },
    'start_time': None,
    'detection_log': [],
    'log_file': 'detections.log',
    'camera_coords': {
        'lat': 55.76,
        'lon': 37.64
    }
}

drone_tracker = DroneTracker(
    'best~0.979.pt',
    drone_real_size=system_state['settings']['drone_size'],
    confidence_threshold=system_state['settings']['confidence'],
    focal_length=system_state['settings']['focal_length']
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


def estimate_drone_gps(distance_m):
    """Грубая оценка позиции дрона в GPS на основании расстояния и позиции камеры."""
    lat = system_state['camera_coords']['lat']
    lon = system_state['camera_coords']['lon']

    # Смещение на север на distance_m метров (1 градус ~ 111 км)
    delta_deg = distance_m / 111000.0
    return {'latitude': lat + delta_deg, 'longitude': lon}


def log_detection(detection):
    """Логирование обнаружения дрона"""
    gps_position = estimate_drone_gps(detection['distance'])

    log_entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'distance': float(detection['distance']),
        'confidence': float(detection['confidence']),
        'position': gps_position
    }
    system_state['detection_log'].append(log_entry)

    with open(system_state['log_file'], 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

    if len(system_state['detection_log']) > 50:
        system_state['detection_log'] = system_state['detection_log'][-50:]


def generate_frames():
    cap = cv2.VideoCapture(0)
    while system_state['processing']:
        success, frame = cap.read()
        if not success:
            break

        detections = drone_tracker.detect_drones(frame)
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{detection['distance']:.2f}m",
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            log_detection(detection)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/control', methods=['POST'])
@login_required
def control():
    data = request.get_json()
    if data['action'] == 'start':
        system_state['processing'] = True
        system_state['start_time'] = time.time()
        return jsonify({
            'status': 'started',
            'settings': system_state['settings']
        })
    elif data['action'] == 'stop':
        system_state['processing'] = False
        return jsonify({'status': 'stopped'})
    return jsonify({'error': 'invalid action'}), 400


@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    if 'drone_size' in data:
        system_state['settings']['drone_size'] = float(data['drone_size'])
        drone_tracker.drone_real_size = float(data['drone_size'])
    if 'confidence' in data:
        system_state['settings']['confidence'] = int(data['confidence'])
        drone_tracker.confidence_threshold = int(data['confidence'])
    return jsonify(system_state['settings'])


@app.route('/get_stats')
@login_required
def get_stats():
    uptime = time.time() - system_state['start_time'] if system_state['start_time'] else 0
    last = system_state['detection_log'][-1] if system_state['detection_log'] else None
    return jsonify({
        'uptime': uptime,
        'status': 'active' if system_state['processing'] else 'inactive',
        'detections_count': len(system_state['detection_log']),
        'last_detection': last,
        'position': last['position'] if last else None
    })


@app.route('/drone_coordinates', methods=['POST'])
def drone_coordinates():
    data = request.get_json()
    latitude = float(data.get('latitude'))
    longitude = float(data.get('longitude'))
    system_state['camera_coords']['lat'] = latitude
    system_state['camera_coords']['lon'] = longitude

    # Можно сразу вернуть позицию дрона как проверку
    simulated_position = estimate_drone_gps(100)
    return jsonify({'status': 'success', 'drone_position': simulated_position})


@app.route('/features')
def features():
    return render_template("features.html")


@app.route('/get_log')
@login_required
def get_log():
    return jsonify({
        'log': system_state['detection_log'][-10:],
        'total': len(system_state['detection_log'])
    })


@app.route('/drone_detection')
@login_required
def drone_detection():
    return render_template("main_drones.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.login == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=False)
            return redirect("/")
        return render_template('login_form.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login_form.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    form = RegistrationForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first() or session.query(User).filter(
                User.login == form.username.data).first():
            return render_template("registration_form.html", form=form, message="Такой пользователь уже существует!")
        user = User(login=form.username.data, email=form.email.data, fullname=form.full_name.data)
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect("/login")
    return render_template('registration_form.html', form=form)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


if __name__ == '__main__':
    db_session.global_init("pumpum/db/Drones.db")
    app.run(host='127.0.0.1', port=8080, debug=True)
