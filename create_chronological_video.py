import os
import glob
import shutil
import re
import json
from datetime import datetime
import cv2
import numpy as np
from moviepy.editor import ImageClip, concatenate_videoclips, VideoFileClip
from PIL import Image, ImageDraw, ImageFont
import logging
import psutil
import gc

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Глобальные переменные
ROOT_DIRECTORY = r"E:\GOOGLE_DRIVE_BACKUP\20250114_GOOGLE_PHOTOS_BACKUP\takeout_photos_2022"
RESULTS_FOLDER_PATH = os.path.join(os.getcwd(), "data/results")
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'}
FONT_TYPE = "arial.ttf"  # Убедитесь, что шрифт доступен (например, C:\Windows\Fonts\arial.ttf)
FONT_SIZE = 48
TEXT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # Формат даты и времени
TEXT_POSITION = ("right", "bottom-10")  # Формат: (x, y), где y="bottom-N" — отступ от низа
TEXT_COLOR = (255, 255, 255)  # Белый (RGB)
TEXT_STROKE_COLOR = (0, 0, 0)  # Чёрный (RGB)
TEXT_STROKE_WIDTH = 1
MAX_FILE_SIZE_MB = 1000  # Лимит размера видео (~1 ГБ)
MAX_CLIPS_PER_PART = 3000  # Максимум клипов на часть (300 ~ 10 минут)
TARGET_RESOLUTION = (1920, 1080)  # FullHD
PHOTO_DURATION = 2.0  # Длительность изображения
BATCH_SIZE = 10  # Размер батча
FPS = 1  # Частота кадров
BITRATE = "12M"  # Битрейт (~12 Мбит/с)
OUTPUT_FILENAME_TEMPLATE = "{first_date}_{last_date}_{num_photos}-photos_{part_number:03d}.mp4"


def parse_filename_timestamp(file_path):
    """Извлечь дату и время из имени файла."""
    filename = os.path.basename(file_path)

    # Формат FB_IMG_1720975722339.jpg
    fb_pattern = r'FB_IMG_(\d+)\.jpg'
    fb_match = re.match(fb_pattern, filename, re.IGNORECASE)
    if fb_match:
        timestamp_ms = fb_match.group(1)
        try:
            return int(int(timestamp_ms) / 1000)  # Миллисекунды в секунды
        except ValueError as e:
            logging.warning(f"Некорректный timestamp в имени {filename}: {e}")
            return None

    # Формат IMG_YYYYMMDD_HHMMSSXXX[_HDR].jpg
    img_pattern = r'IMG_(\d{8})_(\d{6})\d{0,3}(?:_HDR)?\.jpg'
    img_match = re.match(img_pattern, filename, re.IGNORECASE)
    if img_match:
        date_str, time_str = img_match.groups()
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
            return int(dt.timestamp())
        except ValueError as e:
            logging.warning(f"Некорректный формат даты/времени в имени {filename}: {e}")
            return None

    name_lst = filename.split('_')
    if len(name_lst) > 2:
        date_str = name_lst[1]
        time_str = name_lst[2]
        try:
            if len(time_str) > 6:
                time_str = time_str[0:6]
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
            return int(dt.timestamp())
        except ValueError as e:
            logging.warning(f"Некорректный формат даты/времени в имени {filename}: {e}")
            return None

    return None

def get_text_timestamp_from_filename(file_path):
    timestamp_int = parse_filename_timestamp(file_path)
    if timestamp_int:
        return str(datetime.fromtimestamp(timestamp_int))
    return ""

def get_json_timestamp(file_path):
    """Извлечь timestamp из JSON-файла."""
    json_path = f"{file_path}.json"
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        timestamp = data.get('creationTime', {}).get('timestamp')
        if timestamp:
            return int(timestamp)
        logging.warning(f"Поле creationTime.timestamp не найдено в {json_path}")
        return None
    except Exception as e:
        logging.error(f"Ошибка чтения JSON {json_path}: {e}")
        return None

def get_creation_time(file_path):
    """Получить время создания файла (в последнюю очередь)."""
    try:
        return int(os.path.getctime(file_path))
    except Exception as e:
        logging.error(f"Ошибка при получении времени создания {file_path}: {e}")
        return 0

def get_file_timestamp(file_path):
    """Получить timestamp файла с приоритетом: имя > JSON > getctime."""
    timestamp = parse_filename_timestamp(file_path)
    if timestamp:
        logging.info(f"Timestamp из имени {file_path}: {datetime.fromtimestamp(timestamp)}")
        return timestamp

    timestamp = get_json_timestamp(file_path)
    if timestamp:
        logging.info(f"Timestamp из JSON {file_path}: {datetime.fromtimestamp(timestamp)}")
        return timestamp

    timestamp = get_creation_time(file_path)
    logging.info(f"Timestamp из getctime {file_path}: {datetime.fromtimestamp(timestamp)}")
    return timestamp

def get_json_text_data(file_path):
    """Извлечь данные для текста из JSON-файла."""
    json_path = f"{file_path}.json"
    if not os.path.exists(json_path):
        logging.warning(f"JSON-файл не найден для {file_path}")
        return ""

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Предпочитаем photoTakenTime, иначе creationTime
        timestamp = (data.get('photoTakenTime', {}).get('timestamp') or
                     data.get('creationTime', {}).get('timestamp'))
        latitude = data.get('geoData', {}).get('latitude', 0.0)
        longitude = data.get('geoData', {}).get('longitude', 0.0)

        if timestamp:
            date_time = datetime.fromtimestamp(int(timestamp)).strftime(TEXT_DATE_FORMAT)
        else:
            date_time = ""

        text = date_time
        if latitude != 0.0 or longitude != 0.0:
            text += f" | Lat: {latitude:.6f}, Lon: {longitude:.6f}"
        return text
    except Exception as e:
        logging.error(f"Ошибка чтения JSON {json_path}: {e}")
        return ""

def add_text_to_image(image, text, font_type=FONT_TYPE, font_size=FONT_SIZE,
                      text_position=TEXT_POSITION, text_color=TEXT_COLOR,
                      stroke_color=TEXT_STROKE_COLOR, stroke_width=TEXT_STROKE_WIDTH):
    """Добавить текст на изображение с помощью Pillow."""
    try:
        # Конвертация в PIL Image
        pil_image = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_image)

        # Загрузка шрифта
        try:
            font = ImageFont.truetype(font_type, font_size)
        except Exception as e:
            logging.warning(f"Шрифт {font_type} недоступен, используется стандартный: {e}")
            font = ImageFont.load_default()

        # Расчёт размеров текста с помощью textbbox
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Расчёт позиции текста
        img_width, img_height = pil_image.size

        if text_position[0] == "center":
            x = (img_width - text_width) // 2
        elif text_position[0] == "right":
            x = img_width - text_width
        else:
            x = text_position[0]

        if isinstance(text_position[1], str) and text_position[1].startswith("bottom-"):
            offset = int(text_position[1].split("-")[1])
            y = img_height - text_height - offset
        else:
            y = text_position[1]

        # Рисование текста с обводкой
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((x + offset_x, y + offset_y), text, font=font, fill=stroke_color)
        draw.text((x, y), text, font=font, fill=text_color)

        # Конвертация обратно в numpy массив
        return np.array(pil_image)
    except Exception as e:
        logging.error(f"Ошибка добавления текста на изображение: {e}")
        return image

def resize_to_fullhd(image, max_width=1920, max_height=1080):
    """Масштабировать изображение до FullHD."""
    if image is None:
        return None
    h, w = image.shape[:2]
    if w > max_width or h > max_height:
        scale = min(max_width / w, max_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image

def log_memory_usage():
    """Логировать использование памяти."""
    process = psutil.Process()
    mem_info = process.memory_info()
    logging.info(f"Использование памяти: {mem_info.rss / 1024 / 1024:.2f} MiB")

def collect_image_files(root_dir):
    """Собрать все изображения в хронологическом порядке."""
    image_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                file_path = os.path.join(root, file)
                timestamp = get_file_timestamp(file_path)
                image_files.append((file_path, timestamp))

    # Сортировка по timestamp
    image_files.sort(key=lambda x: x[1])
    logging.info(f"Найдено {len(image_files)} изображений")
    # Логирование первых 10 файлов
    for i, (file_path, timestamp) in enumerate(image_files[:10]):
        logging.info(f"Файл {i+1}: {file_path}, время: {datetime.fromtimestamp(timestamp)}")
    if len(image_files) > 10:
        logging.info(f"... и ещё {len(image_files) - 10} файлов")
    return [f[0] for f in image_files]

def create_video_part(image_files, part_number, output_dir, photo_duration=2.0,
                      target_resolution=(1920, 1080), batch_size=10):
    """Создать одну часть видео из изображений."""
    clips = []  # Текущий батч клипов
    batch_clips = []  # Все батчи для части
    clip_count = 0
    temp_image_dir = os.path.join(output_dir, "temp_images")
    os.makedirs(temp_image_dir, exist_ok=True)
    first_timestamp = None
    last_timestamp = None

    for i, file_path in enumerate(image_files):
        if clip_count >= MAX_CLIPS_PER_PART:
            logging.info(f"Достигнут лимит клипов ({MAX_CLIPS_PER_PART}) для части {part_number}")
            break

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        try:
            # Обработка изображения
            img = cv2.imread(file_path)
            if img is None:
                logging.warning(f"Не удалось загрузить изображение: {file_path}")
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = resize_to_fullhd(img, max_width=target_resolution[0], max_height=target_resolution[1])
            if img is None:
                logging.warning(f"Некорректное изображение после масштабирования: {file_path}")
                continue

            # Обновление временных меток
            timestamp = get_file_timestamp(file_path)
            if first_timestamp is None:
                first_timestamp = timestamp
            last_timestamp = timestamp

            # Добавление текста
            text = get_json_text_data(file_path)
            if not text:
                text = get_text_timestamp_from_filename(file_path)
            img_with_text = add_text_to_image(img, text)

            # Сохранение временного изображения
            temp_image_path = os.path.join(temp_image_dir, f"temp_{part_number:03d}_{clip_count:03d}.png")
            cv2.imwrite(temp_image_path, cv2.cvtColor(img_with_text, cv2.COLOR_RGB2BGR))
            if not os.path.exists(temp_image_path):
                logging.error(f"Временное изображение {temp_image_path} не создано")
                continue

            # Создание клипа
            clip = ImageClip(temp_image_path, duration=photo_duration)
            clips.append(clip)
            clip_count += 1
            logging.info(f"Добавлено изображение {clip_count}: {file_path} с текстом: {text}")

            # Логирование памяти
            log_memory_usage()

            # Обработка батча
            if len(clips) >= batch_size or i == len(image_files) - 1 or clip_count >= MAX_CLIPS_PER_PART:
                if clips:
                    try:
                        batch_clip = concatenate_videoclips(clips, method="compose")
                        temp_output = os.path.join(output_dir, f"temp_batch_{part_number:03d}_{clip_count:03d}.mp4")
                        batch_clip.write_videofile(
                            temp_output,
                            codec="libx264",
                            fps=FPS,
                            audio=False,
                            ffmpeg_params=["-an", "-b:v", BITRATE],
                            preset="medium"
                        )
                        batch_clip.close()
                        if not os.path.exists(temp_output):
                            logging.error(f"Временный батч {temp_output} не создан")
                            clips = []
                            continue
                        batch_clips.append(VideoFileClip(temp_output))
                        logging.info(f"Сохранён временный батч: {temp_output} (изображений: {len(clips)})")
                    except Exception as e:
                        logging.error(f"Ошибка при создании батча {temp_output}: {e}")
                        continue
                    finally:
                        for clip in clips:
                            clip.close()
                        clips = []
                        # Удаление временных изображений
                        for temp_img in glob.glob(os.path.join(temp_image_dir, f"temp_{part_number:03d}_*.png")):
                            try:
                                os.remove(temp_img)
                            except Exception as e:
                                logging.error(f"Ошибка удаления {temp_img}: {e}")
                        gc.collect()
                        log_memory_usage()

        except Exception as e:
            logging.error(f"Ошибка при обработке файла {file_path}: {e}")
            continue

    if not batch_clips:
        logging.error(f"Нет подходящих батчей для части {part_number}.")
        shutil.rmtree(temp_image_dir, ignore_errors=True)
        return None, image_files

    # Формирование имени файла
    try:
        first_date = datetime.fromtimestamp(first_timestamp).strftime("%Y-%m-%d") if first_timestamp else "unknown"
        last_date = datetime.fromtimestamp(last_timestamp).strftime("%Y-%m-%d") if last_timestamp else "unknown"
        num_photos = clip_count
        output_filename = OUTPUT_FILENAME_TEMPLATE.format(
            first_date=first_date,
            last_date=last_date,
            num_photos=num_photos,
            part_number=part_number
        )
        output_path = os.path.join(output_dir, output_filename)
    except Exception as e:
        logging.error(f"Ошибка формирования имени файла: {e}")
        output_filename = f"output_video_{part_number:03d}.mp4"
        output_path = os.path.join(output_dir, output_filename)

    # Финальная сборка
    try:
        logging.info(f"Сборка финального видео для части {part_number} ({clip_count} клипов)")
        final_clip = concatenate_videoclips(batch_clips, method="compose")
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            fps=FPS,
            audio=False,
            ffmpeg_params=["-an", "-b:v", BITRATE],
            preset="medium"
        )
        final_clip.close()
        logging.info(f"Часть {part_number} сохранена: {output_path}")

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logging.info(f"Размер части {part_number}: {file_size_mb:.2f} MiB")

        remaining_files = image_files[clip_count:] if clip_count < len(image_files) else []
        return output_path, remaining_files
    except Exception as e:
        logging.error(f"Ошибка при создании части {part_number}: {e}")
        return None, image_files
    finally:
        for clip in batch_clips:
            clip.close()
        for temp_file in glob.glob(os.path.join(output_dir, f"temp_batch_{part_number:03d}_*.mp4")):
            try:
                os.remove(temp_file)
                logging.info(f"Удалён временный файл: {temp_file}")
            except Exception as e:
                logging.error(f"Ошибка удаления {temp_file}: {e}")
        shutil.rmtree(temp_image_dir, ignore_errors=True)
        gc.collect()
        log_memory_usage()

def main(root_dir=ROOT_DIRECTORY, output_base="output_video"):
    """Основная функция для создания видео."""
    if os.path.exists(RESULTS_FOLDER_PATH):
        shutil.rmtree(RESULTS_FOLDER_PATH)
        logging.info(f"Очищена папка: {RESULTS_FOLDER_PATH}")
    os.makedirs(RESULTS_FOLDER_PATH, exist_ok=True)
    logging.info(f"Создана папка: {RESULTS_FOLDER_PATH}")

    image_files = collect_image_files(root_dir)
    if not image_files:
        logging.error("Изображения не найдены.")
        return

    part_number = 1
    current_files = image_files

    while current_files:
        logging.info(f"Обработка части {part_number}...")
        output_path, remaining_files = create_video_part(
            current_files,
            part_number,
            RESULTS_FOLDER_PATH,
            photo_duration=PHOTO_DURATION,
            target_resolution=TARGET_RESOLUTION,
            batch_size=BATCH_SIZE
        )
        if output_path:
            logging.info(f"Завершена часть {part_number}")
        else:
            logging.error(f"Не удалось создать часть {part_number}")
            break
        current_files = remaining_files
        part_number += 1

if __name__ == "__main__":
    # Установка необходимых библиотек:
    # pip install moviepy==1.0.3 opencv-python numpy psutil Pillow
    main()