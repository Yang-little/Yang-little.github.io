import cv2
import os
import numpy as np
import json

data_dir, models_dir = "data", "models"
os.makedirs(models_dir, exist_ok=True)

face_recognizer = cv2.face.LBPHFaceRecognizer_create()
current_id = 0
label_map, x_train, y_labels = {}, [], []

for root, dirs, files in os.walk(data_dir):
    for dir_name in dirs:
        if dir_name not in label_map.values():
            label_map[current_id] = dir_name
            person_dir = os.path.join(data_dir, dir_name)
            for file_name in os.listdir(person_dir):
                if file_name.lower().endswith(('jpg', 'jpeg', 'png')):
                    img = cv2.imread(os.path.join(person_dir, file_name), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        x_train.append(img)
                        y_labels.append(current_id)
            current_id += 1

if x_train:
    face_recognizer.train(x_train, np.array(y_labels))
    face_recognizer.save(os.path.join(models_dir, "lbph_model.yml"))
    with open(os.path.join(models_dir, "labels.json"), "w") as f:
        json.dump(label_map, f)