from picamera2 import Picamera2
import cv2

# 初始化相機
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration(main={'size': (640,480)}))
picam2.start()

# 擷取影像 (此時 frame 為 RGB 格式)
frame = picam2.capture_array()

# 透過 OpenCV 旋轉 180 度 (0=垂直翻轉, 1=水平翻轉, -1=同時水平與垂直翻轉)
frame = cv2.flip(frame, -1)

# 安全釋放資源 (非常重要，避免下次執行報錯)
picam2.stop()
picam2.close()

# 將 RGB 轉換為灰階
gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

# 儲存影像
cv2.imwrite('gray_capture_0922.jpg', gray)
print('影像已存檔 gray_capture_0922.jpg')