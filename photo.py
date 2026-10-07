import cv2
import numpy as np

# 1. 讀取原始圖片 (改為 monkey.jpg)
img = cv2.imread('monkey.jpg')

# 確保有讀取到圖片
if img is None:
    print("找不到 monkey.jpg，請確認圖片是否放在同一個資料夾，並且終端機路徑正確！")
else:
    # ==========================================
    # [1] 產生並儲存：RGB 全彩影像
    # ==========================================
    cv2.imwrite('rgb_monkey.jpg', img)
    print("✅ 成功產生全彩影像：rgb_monkey.jpg")

    # ==========================================
    # [2] 產生並儲存：灰階影像 (Grayscale)
    # ==========================================
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('gray_monkey.jpg', gray)
    print("✅ 成功產生灰階影像：gray_monkey.jpg")

    # ==========================================
    # [3] 產生並儲存：純黑白影像 (Binary)
    # ==========================================
    # 利用剛才產生的灰階圖，再以 127 為門檻值將影像二值化 (純黑與純白)
    ret, bw_img = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    cv2.imwrite('bw_monkey.jpg', bw_img)
    print("✅ 成功產生純黑白影像：bw_monkey.jpg")

    # ==========================================
    # [4] 產生並儲存：16色 / 256色處理 (色調分離 Posterization)
    # ==========================================
    # 透過整數除法壓縮色彩漸層，產生類似復古降色階的效果
    color_reduced = (img // 32) * 32
    cv2.imwrite('color256_monkey.jpg', color_reduced)
    print("✅ 成功產生降色階影像：color256_monkey.jpg")

    print("\n🎉 全部處理完成！請去資料夾查看這四張新的圖片。")