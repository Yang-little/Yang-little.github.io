import cv2                    # 匯入 OpenCV 函式庫
img = cv2.imread('test.jpg')  # 讀取圖片
cv2.imshow('oxxostudio',img)        # 賦予開啟的視窗名稱，開啟圖片
cv2.waitKey(0)                