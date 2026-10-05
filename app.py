from flask import Flask, render_template_string, Response
from LOBOROBOT2 import LOBOROBOT
from picamera2 import Picamera2
from libcamera import Transform
import cv2
import time

# 初始化 Web 伺服器與小車
app = Flask(__name__)
robot = LOBOROBOT()

# 初始化相機 (使用 video_configuration 確保串流順暢)
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={'size': (640, 480)},
    transform=Transform(hflip=True, vflip=True)
)
picam2.configure(config)
picam2.start()

# 影像串流產生器
def generate_frames():
    while True:
        # 擷取影像並將 RGB 轉為 BGR 供 OpenCV 編碼
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # 壓縮成 JPEG 格式
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        frame_bytes = buffer.tobytes()
        
        # 使用 multipart 協定不斷推播影像給網頁
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# 網頁前端 HTML 與 JavaScript (內嵌)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>智慧小車控制台</title>
    <style>
        body { text-align: center; font-family: sans-serif; background: #222; color: #fff; margin-top: 20px;}
        img { max-width: 100%; border: 3px solid #4CAF50; border-radius: 10px; }
        .controls { margin-top: 20px; user-select: none; }
        .key { display: inline-block; padding: 15px 25px; margin: 5px; background: #555; border-radius: 8px; font-weight: bold; font-size: 20px;}
        .active { background: #4CAF50; box-shadow: 0 0 10px #4CAF50;}
    </style>
</head>
<body>
    <h1>LoboRobot 即時控制台</h1>
    <div>
        <img src="/video_feed" width="640" height="480" />
    </div>
    <div class="controls">
        <p>請使用鍵盤【方向鍵】控制，放開按鍵自動停止。</p>
        <div><span id="key-up" class="key">↑</span></div>
        <div>
            <span id="key-left" class="key">←</span>
            <span id="key-down" class="key">↓</span>
            <span id="key-right" class="key">→</span>
        </div>
    </div>

    <script>
        let currentAction = 'stop';

        // 發送 API 請求給樹莓派
        function sendCommand(cmd) {
            if (currentAction !== cmd) {
                currentAction = cmd;
                fetch('/action/' + cmd);
            }
        }

        // 偵測按鍵按下 (前進、後退、左轉、右轉)
        document.addEventListener('keydown', function(event) {
            if (event.repeat) return; // 防止長按時重複觸發
            switch(event.key) {
                case 'ArrowUp': sendCommand('forward'); document.getElementById('key-up').classList.add('active'); break;
                case 'ArrowDown': sendCommand('backward'); document.getElementById('key-down').classList.add('active'); break;
                case 'ArrowLeft': sendCommand('left'); document.getElementById('key-left').classList.add('active'); break;
                case 'ArrowRight': sendCommand('right'); document.getElementById('key-right').classList.add('active'); break;
            }
        });

        // 偵測按鍵放開 (停止)
        document.addEventListener('keyup', function(event) {
            switch(event.key) {
                case 'ArrowUp': document.getElementById('key-up').classList.remove('active'); break;
                case 'ArrowDown': document.getElementById('key-down').classList.remove('active'); break;
                case 'ArrowLeft': document.getElementById('key-left').classList.remove('active'); break;
                case 'ArrowRight': document.getElementById('key-right').classList.remove('active'); break;
            }
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
                sendCommand('stop');
            }
        });
    </script>
</body>
</html>
"""

# 網頁首頁路由
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# 影像串流路由
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 控制指令路由
@app.route('/action/<cmd>')
def action(cmd):
    speed = 60  # 你可以調整預設速度 (0-100)
    # 注意：這裡的 t_time 都設為 0，代表「執行後立刻返回不等待」，馬達會持續轉動直到收到 stop 指令
    if cmd == 'forward':
        robot.moveforward(speed, 0)
    elif cmd == 'backward':
        robot.movebackward(speed, 0)
    elif cmd == 'left':
        robot.turnLeft(speed, 0)
    elif cmd == 'right':
        robot.turnRight(speed, 0)
    elif cmd == 'stop':
        robot.t_stop(0)
    
    return "OK"

if __name__ == '__main__':
    # 啟動伺服器，監聽所有 IP，Port 設為 5000
    try:
        print("伺服器啟動！請在瀏覽器輸入 http://<你的樹莓派IP>:5000")
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        # 關閉伺服器時安全釋放資源
        robot.t_stop(0)
        picam2.stop()
        picam2.close()