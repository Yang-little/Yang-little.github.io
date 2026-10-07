import time
import cv2
from flask import Flask, Response, render_template_string, request
from libcamera import Transform
from LOBOROBOT2 import LOBOROBOT
import numpy as np
from picamera2 import Picamera2

# 1. 初始化 Web 伺服器與小車硬體
app = Flask(__name__)
robot = LOBOROBOT()

# 2. 初始化相機 (單一實例，包含翻轉與 RGB 格式設定)
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={'size': (640, 480), 'format': 'RGB888'},
    transform=Transform(hflip=True, vflip=True),
)
picam2.configure(config)
picam2.start()


# 宣告全域變數
smoothed_cte = 0.0
prev_frame_time = time.time()
current_fps = 0.0

def make_coordinates(image, line_parameters):
    """根據斜率與截距，將線條延伸至畫面底部的輔助函式"""
    slope, intercept = line_parameters
    y1 = image.shape[0]          # 畫面最底部
    y2 = int(y1 * 0.6)           # ROI 頂端
    if abs(slope) < 1e-4:
        return None
    x1 = int((y1 - intercept) / slope)
    x2 = int((y2 - intercept) / slope)
    return [x1, y1, x2, y2]

from datetime import datetime

def process_lane(frame):
    global smoothed_cte, prev_frame_time, current_fps
    h, w = frame.shape[:2]
    screen_center_x = w // 2

    # 計算 FPS
    now = time.time()
    dt = now - prev_frame_time
    prev_frame_time = now
    if dt > 0:
        fps_val = 1.0 / dt
        current_fps = 0.9 * current_fps + 0.1 * fps_val if current_fps > 0 else fps_val

    # 1. ROI 遮罩：保留畫面下方 60% ~ 100%
    mask_roi = np.zeros((h, w), dtype=np.uint8)
    roi_polygon = np.array([
        [(0, h), (0, int(h * 0.6)), (w, int(h * 0.6)), (w, h)]
    ], dtype=np.int32)
    cv2.fillPoly(mask_roi, roi_polygon, 255)

    # 2. HSV 顏色過濾
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_yellow = np.array([15, 60, 70])
    upper_yellow = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    lower_white = np.array([0, 0, 160])
    upper_white = np.array([180, 50, 255])
    mask_white = cv2.inRange(hsv, lower_white, upper_white)

    color_mask = cv2.bitwise_or(mask_yellow, mask_white)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    clean_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
    masked_line = cv2.bitwise_and(clean_mask, mask_roi)

    # 3. 邊緣檢測
    blurred = cv2.GaussianBlur(masked_line, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 130)

    # 4. 霍夫直線變換
    lines = cv2.HoughLinesP(
        edges, 
        rho=1, 
        theta=np.pi / 180, 
        threshold=40,
        minLineLength=45,
        maxLineGap=40
    )

    output = frame.copy()
    left_fit = []
    right_fit = []

    # 5. 線段分組與斜率篩選
    if lines is not None:
        for line in lines:
            coords = line.flatten()
            if len(coords) == 4:
                x1, y1, x2, y2 = coords
                if x1 == x2:
                    continue
                parameters = np.polyfit((x1, x2), (y1, y2), 1)
                slope = parameters[0]
                intercept = parameters[1]

                if abs(slope) < 0.4:
                    continue

                if slope < 0 and x1 < screen_center_x + 50:
                    left_fit.append((slope, intercept))
                elif slope > 0 and x2 > screen_center_x - 50:
                    right_fit.append((slope, intercept))

    # 6. 擬合藍線
    left_x_bottom = None
    right_x_bottom = None

    if left_fit:
        left_avg = np.average(left_fit, axis=0)
        left_line = make_coordinates(frame, left_avg)
        if left_line is not None:
            cv2.line(output, (left_line[0], left_line[1]), (left_line[2], left_line[3]), (255, 0, 0), 6)
            left_x_bottom = left_line[0]

    if right_fit:
        right_avg = np.average(right_fit, axis=0)
        right_line = make_coordinates(frame, right_avg)
        if right_line is not None:
            cv2.line(output, (right_line[0], right_line[1]), (right_line[2], right_line[3]), (255, 0, 0), 6)
            right_x_bottom = right_line[0]

    # 7. 計算 CTE
    ESTIMATED_LANE_WIDTH = 420
    if left_x_bottom is not None and right_x_bottom is not None:
        lane_center_x = int((left_x_bottom + right_x_bottom) / 2)
    elif left_x_bottom is not None:
        lane_center_x = int(left_x_bottom + ESTIMATED_LANE_WIDTH / 2)
    elif right_x_bottom is not None:
        lane_center_x = int(right_x_bottom - ESTIMATED_LANE_WIDTH / 2)
    else:
        lane_center_x = screen_center_x

    # 8. 指數平滑與繪製引導線
    raw_cte = lane_center_x - screen_center_x
    smoothed_cte = 0.75 * smoothed_cte + 0.25 * raw_cte
    display_cte = int(smoothed_cte)

    cv2.line(output, (screen_center_x, h), (screen_center_x, int(h * 0.6)), (0, 255, 255), 2)
    target_x = screen_center_x + display_cte
    cv2.circle(output, (target_x, int(h * 0.8)), 8, (0, 0, 255), -1)

    lanes_count = (left_x_bottom is not None) + (right_x_bottom is not None)

    # --- 左上角：FPS 與 CTE ---
    fps_text = f"FPS: {current_fps:.1f}"
    cte_text = f"CTE: {display_cte:+d} px | Lanes: {lanes_count}"
    cv2.putText(output, fps_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(output, cte_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # --- 右上角：當前日期與時間 ---
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    (text_w, text_h), _ = cv2.getTextSize(date_str, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.putText(output, date_str, (w - text_w - 20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    return output

# 4. 影像串流產生器
def generate_frames():
  while True:
    try:
      frame = picam2.capture_array()
      # Picamera2 輸出為 RGB，轉為 OpenCV 慣用 BGR
      frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

      # 執行車道線辨識流水線
      processed_frame = process_lane(frame_bgr)

      # 編碼為 JPEG
      ret, buffer = cv2.imencode('.jpg', processed_frame)
      frame_bytes = buffer.tobytes()

      yield (
          b'--frame\r\n'
          b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
      )
    except Exception as e:
      print(f'Frame capture error: {e}')
      break


# 5. 前端 HTML 頁面 (保留 LoboRobot 介面與方向鍵控制)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>LoboRobot 即時控制台</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background: #222; color: #fff; margin: 0; padding: 20px; }
        h1 { margin-bottom: 10px; font-size: 24px; }
        .stream-box { max-width: 640px; margin: 0 auto; border: 3px solid #28a745; border-radius: 10px; overflow: hidden; }
        img { width: 100%; height: auto; display: block; }
        .control-panel { margin-top: 20px; display: inline-grid; grid-template-columns: repeat(3, 70px); grid-gap: 10px; }
        button {
            height: 60px; font-size: 18px; font-weight: bold; background: #444; color: white;
            border: none; border-radius: 8px; cursor: pointer; user-select: none;
        }
        button:active { background: #007bff; }
        .stop-btn { background: #dc3545; }
        .info { margin-top: 15px; color: #aaa; font-size: 14px; }
    </style>
</head>
<body>
    <h1>LoboRobot 即時控制台</h1>
    <div class="stream-box">
        <img src="/video_feed" alt="Video Stream">
    </div>
    
    <div class="control-panel">
        <div></div>
        <button onmousedown="sendCmd('forward')" onmouseup="sendCmd('stop')" ontouchstart="sendCmd('forward')" ontouchend="sendCmd('stop')">▲</button>
        <div></div>
        <button onmousedown="sendCmd('left')" onmouseup="sendCmd('stop')" ontouchstart="sendCmd('left')" ontouchend="sendCmd('stop')">◀</button>
        <button class="stop-btn" onclick="sendCmd('stop')">■</button>
        <button onmousedown="sendCmd('right')" onmouseup="sendCmd('stop')" ontouchstart="sendCmd('right')" ontouchend="sendCmd('stop')">▶</button>
        <div></div>
        <button onmousedown="sendCmd('backward')" onmouseup="sendCmd('stop')" ontouchstart="sendCmd('backward')" ontouchend="sendCmd('stop')">▼</button>
        <div></div>
    </div>
    <div class="info">支援鍵盤方向鍵或點擊按鈕操控 (放開自動煞車)</div>

    <script>
        function sendCmd(action) {
            console.log("發送指令:", action);
            // 加入時間戳記避免瀏覽器 HTTP 204 被快取忽略
            fetch('/control?action=' + action + '&t=' + new Date().getTime())
                .catch(err => console.error("Fetch error:", err));
        }

        window.addEventListener('keydown', (e) => {
            if (e.repeat) return;
            if (e.key === 'ArrowUp') { e.preventDefault(); sendCmd('forward'); }
            if (e.key === 'ArrowDown') { e.preventDefault(); sendCmd('backward'); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); sendCmd('left'); }
            if (e.key === 'ArrowRight') { e.preventDefault(); sendCmd('right'); }
            if (e.key === ' ') { e.preventDefault(); sendCmd('stop'); }
        });

        window.addEventListener('keyup', (e) => {
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
                sendCmd('stop');
            }
        });
    </script>
</body>
</html>
"""


# 6. Flask 路由設定
@app.route('/')
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed')
def video_feed():
  return Response(
      generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame'
  )


@app.route('/control')
def control():
    action = request.args.get('action')
    speed = 50  # 可依實際動力調整速度 (通常介於 30 ~ 80)
    print(f"[CAR CMD] 收到指令: {action}")

    try:
        if action == 'forward':
            robot.moveforward(speed)
        elif action == 'backward':
            robot.movebackward(speed)
        elif action == 'left':
            robot.turnLeft(speed)     # 若要麥輪橫向平移可改用 robot.moveLeft(speed)
        elif action == 'right':
            robot.turnRight(speed)    # 若要麥輪橫向平移可改用 robot.moveRight(speed)
        elif action == 'stop':
            robot.MotorStop()
    except Exception as e:
        print(f"[CAR ERROR] 馬達執行失敗: {e}")

    return ('', 204)


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        robot.MotorStop()
        picam2.stop()