import cv2
import os
import json

with open(os.path.join("models", "labels.json"), "r") as f:
    label_map = {int(k): v for k, v in json.load(f).items()}

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(os.path.join("models", "lbph_model.yml"))
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret: break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

    for (x, y, w, h) in faces:
        face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        label_id, confidence = recognizer.predict(face_roi)
        
        # LBPH 演算法中，Confidence 代表特徵距離，越低表示越相似
        if confidence <= 75 and label_id in label_map:
            text, color = f"{label_map[label_id]} ({confidence:.1f})", (0, 255, 0)
        else:
            text, color = f"Unknown ({confidence:.1f})", (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    cv2.imshow('LBPH Recognition', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

cap.release()
cv2.destroyAllWindows()