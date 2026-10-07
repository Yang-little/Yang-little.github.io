import cv2
import os

student_id = input("請輸入學生編號/姓名 (例如 student01): ").strip()
save_dir = os.path.join("data", student_id)
os.makedirs(save_dir, exist_ok=True) 

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')
cap = cv2.VideoCapture(0)
count = 0
max_samples = 30

while True:
    ret, frame = cap.read()
    if not ret: break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

    for (x, y, w, h) in faces:
        count += 1
        face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        cv2.imwrite(os.path.join(save_dir, f"{count:02d}.jpg"), face_roi)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
    cv2.imshow('Collect Faces', frame)
    # 加入換行確保邏輯清晰
    if cv2.waitKey(1) & 0xFF == ord('q') or count >= max_samples: 
        break

cap.release()
cv2.destroyAllWindows()