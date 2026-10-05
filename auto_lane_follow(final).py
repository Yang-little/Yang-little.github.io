import cv2
import numpy as np
import time
import atexit
from flask import Flask, Response, render_template_string, request, jsonify
from LOBOROBOT2 import LOBOROBOT
from picamera2 import Picamera2
import libcamera

app = Flask(__name__)
robot = LOBOROBOT()

# --- 狀態設定 ---
auto_mode = False  
speed = 40         
# 更新為 140x140 區域的中心點 (180~320 的中點)
TARGET_X = 250     

# --- 相機設定 ---
picamera = Picamera2()
config = picamera.create_preview_configuration(main={"format": "RGB888", "size": (320, 240)})
config["transform"] = libcamera.Transform(hflip=True, vflip=True)
picamera.configure(config)
picamera.start()

def get_lane_cx(frame):
    # 1. 預處理：轉灰階並模糊化
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 2. Canny 邊緣偵測
    edges = cv2.Canny(blur, 50, 150)
    
    # 3. 關注區域裁切 (維持您的 140x140 設定)
    # y: 100~240, x: 180~320
    roi = edges[100:240, 180:320]
    
    # 4. 霍夫線條變換
    # threshold=30 (門檻), minLineLength=20 (最小長度), maxLineGap=10 (線段間隙)
    lines = cv2.HoughLinesP(roi, 1, np.pi/180, 30, minLineLength=20, maxLineGap=10)
    
    line_x = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 計算斜率：dy/dx
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                # 過濾：我們只要正斜率（右側線條通常在影像中是正斜率）
                # 且斜率要在 0.5 到 2.0 之間（約 30~60 度角）
                if 0.5 < slope < 2.0:
                    line_x.append(x1)
                    line_x.append(x2)
    
    if len(line_x) > 0:
        # 回傳所有符合線段的平均 X 座標，並加上偏移量 180
        return int(np.mean(line_x)) + 180
    return None

def gen_frames():
    global auto_mode
    while True:
        try:
            raw_frame = picamera.capture_array()
            frame = cv2.cvtColor(raw_frame, cv2.COLOR_RGB2BGR)
            cx = get_lane_cx(frame)
            
            status = "MANUAL" 

            if auto_mode:
                if cx is not None:
                    error = cx - TARGET_X
                    status = f"AUTO: ERR {error}"
                    
                    if abs(error) > 5:  # 死區設定
                        Kp = 0.8
                        steer_value = int(error * Kp)
                        steer_value = max(min(steer_value, 25), -25)
                        
                        # 根據需求決定是否需要對調 steer_value 的正負號以修正轉向方向
                        robot.move_with_offset(speed, steer_value, -steer_value, 0)
                    else:
                        robot.moveforward(speed, 0)
                else:
                    robot.t_stop(0)
                    status = "LINE LOST"

            # --- 視覺化繪製更新 ---
            # 畫出 140x140 綠色觀測框
            cv2.rectangle(frame, (180, 100), (320, 240), (0, 255, 0), 2)
            
            if cx is not None: 
                cv2.circle(frame, (cx, 170), 10, (0, 0, 255), -1)
            
            # 畫出黃色基準線 (對準 250)
            cv2.line(frame, (TARGET_X, 100), (TARGET_X, 240), (0, 255, 255), 2)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print(f"Error: {e}")
            break

@app.route('/')
def index():
    return render_template_string("""
        <body style="text-align:center; background:#222; color:white; font-family:sans-serif;">
            <h1>Pi 5 局部關注控制 (140x140)</h1>
            <img src="{{ url_for('video_feed') }}" width="480">
            <br><br>
            <button style="padding:15px; background:green; color:white;" onclick="fetch('/api/mode?set=auto')">啟動自動駕駛</button>
            <button style="padding:15px; background:red; color:white;" onclick="fetch('/api/mode?set=manual')">手動模式</button>
            <script>
                function ctrl(key) { fetch('/api/move?key=' + key); }
                window.onkeydown = (e) => {
                    let k = e.key.toLowerCase();
                    if(['w','a','s','d',' '].includes(k)) ctrl(k === ' ' ? 'q' : k);
                };
                window.onkeyup = (e) => { if(e.key !== ' ') ctrl('q'); };
            </script>
        </body>
    """)

@app.route('/video_feed')
def video_feed(): return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/mode')
def set_mode():
    global auto_mode
    auto_mode = (request.args.get('set') == 'auto')
    if not auto_mode: robot.t_stop(0)
    return jsonify({"mode": auto_mode})

@app.route('/api/move')
def move():
    global auto_mode
    key = request.args.get('key')
    if key in ['w','a','s','d']:
        auto_mode = False
        if key == 'w': robot.moveforward(speed, 0)
        elif key == 's': robot.movebackward(speed, 0)
        elif key == 'a': robot.turnLeft(speed, 0)
        elif key == 'd': robot.turnRight(speed, 0)
    else: robot.t_stop(0)
    return "ok"

atexit.register(lambda: (robot.t_stop(0), picamera.stop()))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, threaded=True)