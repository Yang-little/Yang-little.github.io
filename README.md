# 樹莓派影像處理與自駕車、人臉辨識綜合實作

## 📝 基本資訊
* 標題：樹莓派影像處理與自駕車實作
* 學號：411306139
* 姓名：楊致欣
* 分組繳交：[蕭佑亦411306158 龔正媛611506009]
* Neocities 網頁報告連結：[貼上你的 Neocities 網址]
* AI 互動鏈結 (AI Sharing Link)：(https://share.gemini.google/joga3HxsREbt)

## 📂 專案資訊架構 (Project Structure)
├── collect_faces.py           # 人臉資料收集 (Webcam截圖)
├── train_lbph.py              # LBPH 模型訓練
├── recognize_lbph.py          # 即時人臉辨識
├── haarcascade_frontalface_alt.xml # Haar特徵分類器
├── photo.py                   # 影像色彩處理 (RGB/灰階/黑白/16色)
├── auto_lane_follow(final).py # 車道線邊緣偵測與 PID 控制
├── LOBOROBOT2.py              # 馬達驅動函式庫
├── index.html                 # Neocities 報告網頁原始碼
└── models/                    # 模型儲存區 (yml 與 json)

## 🔄 資訊處理流程 (Workflow)
1. **影像基礎處理**：透過 OpenCV 讀取圖片，進行 RGB、灰階、二值化(Binary)與 256/16色調分離處理。
2. **人臉辨識流程**：
   - 使用 `VideoCapture` 啟動攝影機。
   - 透過 `Haar Cascade` 進行人臉特徵位置抓取，裁切並轉為灰階。
   - 將 30 張樣本送入 `LBPHFaceRecognizer` 進行紋理特徵訓練。
   - 即時比對特徵距離 (Confidence)，小於設定閾值即顯示姓名。
3. **車道偵測與自駕控制**：
   - 啟動 Picamera2 擷取路面影像。
   - 建立 ROI (興趣區域) 遮罩過濾背景雜訊。
   - 經過 GaussianBlur 與 Canny 邊緣運算後，執行 HoughLinesP 霍夫變換找出車道線。
   - 計算中心偏移量 (CTE)，將數值傳遞給 LOBOROBOT 模組控制左右輪速差進行修正。

## 🛠️ Trouble-Shooting (異常排除)
* **問題**：`Can't open file: '...\haarcascade_frontalface_alt.xml' in read mode`
* **解決**：OpenCV 讀取模型時不支援中文路徑，將專案移至純英文目錄下執行即解決。
* **問題**：`ModuleNotFoundError: No module named 'cv2'`
* **解決**：虛擬環境 (.venv) 內缺少套件，需先啟動虛擬環境後，執行 `pip install opencv-python` 安裝。# Yang-little.github.io
