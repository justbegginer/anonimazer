import io
import tempfile
import zipfile

import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Query


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # или ["*"] для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Инициализация ===
mp_face_detection = mp.solutions.face_detection
haar_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True)

# === Функции блюра ===

def pixelate(image, blocks=10):
    h, w = image.shape[:2]
    temp = cv2.resize(image, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)

def draw_black_box(image):
    h, w = image.shape[:2]
    return np.zeros((h, w, 3), dtype=np.uint8)


def draw_eye_strip(img):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return img

    h, w = img.shape[:2]
    for face_landmarks in results.multi_face_landmarks:
        try:
            left_eye = [face_landmarks.landmark[i] for i in range(362, 383)]
            right_eye = [face_landmarks.landmark[i] for i in range(33, 54)]

            all_eye_points = left_eye + right_eye
            x_coords = [int(p.x * w) for p in all_eye_points]
            y_coords = [int(p.y * h) for p in all_eye_points]

            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)

            bar_height = max(10, int((y_max - y_min) * 1.5))
            bar_y = int((y_min + y_max) / 2 - bar_height / 2)

            cv2.rectangle(img, (x_min, bar_y), (x_max, bar_y + bar_height), (0, 0, 0), -1)
        except Exception as e:
            continue

    return img

# === Детекция лиц ===

def detect_faces_mediapipe(image):
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        results = face_detection.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        faces = []
        if results.detections:
            h, w = image.shape[:2]
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                x = int(bboxC.xmin * w)
                y = int(bboxC.ymin * h)
                bw = int(bboxC.width * w)
                bh = int(bboxC.height * h)
                faces.append((x, y, bw, bh))
        return faces

def detect_faces_haar(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

# === Основной эндпоинт ===

@app.post("/create-zip")
async def create_zip(files: list[UploadFile] = File(...)):
    zip_io = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(zip_io.name, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            content = await file.read()
            zipf.writestr(file.filename, content)

    zip_io.seek(0)
    return StreamingResponse(open(zip_io.name, "rb"), media_type="application/zip")

@app.post("/blur-faces")
async def blur_faces(
        file: UploadFile = File(...),
        style: str = Query("pixel")
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    all_faces = detect_faces_mediapipe(img)
    if not all_faces:
        all_faces = detect_faces_haar(img)

    if style == "eyes":
        img = draw_eye_strip(img)
    else:
        for (x, y, bw, bh) in all_faces:
            roi = img[y:y+bh, x:x+bw]

            if style == "pixel":
                roi_filtered = pixelate(roi, blocks=10)
                img[y:y+bh, x:x+bw] = roi_filtered
            elif style == "box":
                roi_filtered = draw_black_box(roi)
                img[y:y+bh, x:x+bw] = roi_filtered
            else:
                roi_filtered = pixelate(roi, blocks=10)
                img[y:y+bh, x:x+bw] = roi_filtered

    _, img_encoded = cv2.imencode(".jpg", img)
    return StreamingResponse(io.BytesIO(img_encoded.tobytes()), media_type="image/jpeg")
