from picamera2 import Picamera2
import cv2
import time
from datetime import datetime

# ================= 1. 初始化相機 =================
picam2 = Picamera2()
# 設定解析度為 640x480
config = picam2.create_video_configuration(main={'size': (640, 480)})
picam2.configure(config)
picam2.start()

print("等待相機預熱 2 秒 (避免超時當機)...")
time.sleep(2)

# ================= 2. 設定 MP4 錄影 =================
width, height = 640, 480
# 使用 mp4v 編碼器來輸出 .mp4 檔案
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# 建立 VideoWriter 物件，檔名設為 record.mp4，預設幀率抓 20 FPS
out = cv2.VideoWriter('record.mp4', fourcc, 20.0, (width, height))

# 用來計算 FPS 的時間變數
prev_time = time.time()

print("開始錄影！按下預覽視窗上的 'q' 鍵，或在終端機按 Ctrl+C 結束錄影。")

try:
    while True:
        # 擷取影像 (此時為 RGB 格式)
        frame = picam2.capture_array()
        
        # 1. 將 RGB 轉換為灰階 (黑白畫面)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # 2. 將灰階畫面轉回 BGR 格式 (畫面看起來依然是黑白，但符合影片存檔格式)
        frame = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)
        
        # 轉換為 OpenCV 專用的 BGR 格式
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        frame = cv2.flip(frame, -1)
        
        # ================= 3. 計算與準備文字 =================
        # 計算即時 FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        fps_text = f"fps={int(fps)}"
        
        # 取得當前時間，格式化為 YYYY/MM/DD HH:MM:SS
        time_text = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        
        # ================= 4. 將文字貼到畫面上 =================
        # cv2.putText 參數說明：(圖片, 文字, (X座標, Y座標), 字體, 字體大小, (B,G,R顏色), 粗細)
        
        # (1) 左上角貼上 FPS (座標 x=10, y=30)
        cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # (2) 右上角貼上時間 (座標 x=340, y=30)
        cv2.putText(frame, time_text, (340, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # ================= 5. 儲存與顯示 =================
        # 寫入這張加上文字的圖片到 MP4 檔案中
        out.write(frame)
        
        # 顯示預覽畫面 (如果不想在電腦上跳出視窗，可以把下面這兩行註解掉)
        #cv2.imshow("Camera Live", frame)
        
        # 等待 1 毫秒，如果有按下 'q' 就跳出迴圈
        #if cv2.waitKey(1) & 0xFF == ord('q'):
        #    break

except KeyboardInterrupt:
    # 捕捉終端機的 Ctrl+C 中斷指令
    print("\n收到中斷指令，準備存檔...")

finally:
    # ================= 6. 安全釋放硬體資源 =================
    out.release()      # 儲存並關閉影片檔
    picam2.stop()      # 停止相機
    picam2.close()     # 釋放相機資源
    cv2.destroyAllWindows() # 關閉所有 OpenCV 視窗
    print("錄影已結束，影片成功儲存為 record.mp4！")