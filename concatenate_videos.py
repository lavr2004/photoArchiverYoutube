import os
import glob
import re
import logging
import psutil
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Глобальные переменные
RESULTS_FOLDER_PATH = os.path.join(os.getcwd(), "data/results")
OUTPUT_FILENAME_TEMPLATE = "{year}_{total_photos}-photos.mp4"
BITRATE = "12M"  # Соответствует основному скрипту
FPS = 1  # Соответствует основному скрипту

def log_memory_usage():
    """Логировать использование памяти."""
    process = psutil.Process()
    mem_info = process.memory_info()
    logging.info(f"Использование памяти: {mem_info.rss / 1024 / 1024:.2f} MiB")

def get_video_info(file_path):
    """Извлечь год и количество фотографий из имени файла."""
    filename = os.path.basename(file_path)
    pattern = r'(\d{4})-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}_(\d+)-photos_(\d{3})\.mp4'
    match = re.match(pattern, filename)
    if match:
        year = match.group(1)  # Год из первой даты
        num_photos = int(match.group(2))  # Количество фотографий
        part_number = int(match.group(3))  # Номер части
        return year, num_photos, part_number
    logging.warning(f"Некорректное имя файла: {filename}")
    return None, 0, 0

def concatenate_videos():
    """Конкатенировать все видео в один файл."""
    # Поиск всех видео
    video_files = glob.glob(os.path.join(RESULTS_FOLDER_PATH, "*_*-photos_*.mp4"))
    if not video_files:
        logging.error("Видео файлы не найдены в папке: {RESULTS_FOLDER_PATH}")
        return

    # Сортировка по номеру части
    videos = []
    total_photos = 0
    first_year = None
    for file_path in video_files:
        year, num_photos, part_number = get_video_info(file_path)
        if year:
            videos.append((file_path, part_number))
            total_photos += num_photos
            if first_year is None:
                first_year = year
        else:
            logging.warning(f"Пропущен файл: {file_path}")

    videos.sort(key=lambda x: x[1])  # Сортировка по part_number
    logging.info(f"Найдено {len(videos)} видео, общее количество фотографий: {total_photos}")

    if not videos:
        logging.error("Нет подходящих видео для конкатенации.")
        return

    # Загрузка и конкатенация
    clips = []
    try:
        for file_path, _ in videos:
            logging.info(f"Загрузка видео: {file_path}")
            clip = VideoFileClip(file_path)
            clips.append(clip)
            log_memory_usage()

        logging.info("Конкатенация видео...")
        final_clip = concatenate_videoclips(clips, method="compose")

        # Формирование имени выходного файла
        output_filename = OUTPUT_FILENAME_TEMPLATE.format(
            year=first_year or "unknown",
            total_photos=total_photos
        )
        output_path = os.path.join(RESULTS_FOLDER_PATH, output_filename)

        # Сохранение результата
        logging.info(f"Сохранение объединённого видео: {output_path}")
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            fps=FPS,
            audio=False,
            ffmpeg_params=["-an", "-b:v", BITRATE],
            preset="medium"
        )
        final_clip.close()
        logging.info(f"Объединённое видео сохранено: {output_path}")

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logging.info(f"Размер видео: {file_size_mb:.2f} MiB")

    except Exception as e:
        logging.error(f"Ошибка при конкатенации: {e}")
    finally:
        for clip in clips:
            clip.close()
        log_memory_usage()

if __name__ == "__main__":
    # Установка необходимых библиотек:
    # pip install moviepy==1.0.3 psutil
    concatenate_videos()