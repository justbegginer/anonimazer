import os
import requests

UPLOAD_DIR = "../uploads"
OUTPUT_DIR = "../blured"
SERVICE_URL = "http://localhost:5000/blur-faces"

style = "pixel"  # можно менять на 'box' или 'eyes'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Получаем список файлов
for filename in os.listdir(UPLOAD_DIR):
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Пропускаем папки и не-изображения
    if not os.path.isfile(filepath):
        continue
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
        continue

    print(f"[+] Отправка: {filename} (style={style})")

    with open(filepath, 'rb') as f:
        response = requests.post(
            f"{SERVICE_URL}?style={style}",
            files={'file': f}
        )

    if response.status_code == 200:
        output_path = os.path.join(OUTPUT_DIR, f"{style}_{filename}")
        with open(output_path, 'wb') as out:
            out.write(response.content)
        print(f"[✓] Сохранено: {output_path}")
    else:
        print(f"[✗] Ошибка обработки: {filename} — {response.status_code}")
