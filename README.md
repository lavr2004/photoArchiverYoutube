# PhotoArchiverYouTube

## Overview

`create_chronological_video.py` is a Python script that compiles all photos from a specified directory into a FullHD (1920x1080) video, ready for uploading to YouTube. Each image is displayed for 2 seconds, with overlaid text showing the photo's creation date and time (in `YYYY-MM-DD HH:MM:SS` format) and, if available, geographic coordinates (latitude and longitude). The video is split into parts of approximately 1 GB for easier handling and storage.

The script supports:

- File name formats: `IMG_YYYYMMDD_HHMMSSXXX[_HDR].jpg`, `FB_IMG_<UnixTimestamp>.jpg`.
- Time extraction from file names, JSON files (`creationTime.timestamp`), or file metadata (`os.path.getctime`).
- Text overlay using the Pillow library.
- Customizable settings via global variables (directories, font, date format, etc.).

## Requirements

- **Operating System**: Windows, Linux, or macOS.
- **Python**: 3.10 or higher.
- **FFmpeg**: Required for video encoding (install separately, e.g., via `ffmpeg.org` or package managers like `apt`, `brew`, or `choco`).

## Installation

1. **Clone or download the script**: Save `create_chronological_video.py` to your project directory, e.g., `D:\!DEV_APPS\026_PhotoArchiverYoutube\photoArchiverYoutube`.

2. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3. **Install FFmpeg**:

    - Windows: Download from `ffmpeg.org` or install via Chocolatey (`choco install ffmpeg`).
    - Linux: `sudo apt install ffmpeg` (Ubuntu/Debian) or equivalent.
    - macOS: `brew install ffmpeg`.
4. **Verify font availability**: Ensure `arial.ttf` (or another specified font) is available, e.g., in `C:\Windows\Fonts\arial.ttf`. Update `FONT_TYPE` in the script if needed.


## Usage

1. **Configure the script**: Edit global variables in `create_chronological_video.py`:

    - `ROOT_DIRECTORY`: Path to the photo directory (e.g., `E:\GOOGLE_DRIVE_BACKUP\20250114_GOOGLE_PHOTOS_BACKUP\2024`).
    - `RESULTS_FOLDER_PATH`: Output directory for videos (e.g., `data/results`).
    - `TEXT_DATE_FORMAT`: Date format (default: `%Y-%m-%d %H:%M:%S`).
    - `FONT_TYPE`, `FONT_SIZE`, `TEXT_POSITION`, etc., for text overlay.
2. **Prepare photos**: Ensure the source directory contains images (`.jpg`, `.png`, etc.) and optional JSON files with metadata (e.g., `IMG_20240113_130713744.jpg.json`).

3. **Run the script**:

    ```bash
    python create_chronological_video.py
    ```

4. **Check output**:

    - Videos are saved in `RESULTS_FOLDER_PATH` as `output_video_001.mp4`, `output_video_002.mp4`, etc. (~1 GB each).
    - Temporary files (`temp_batch_XXX_YYY.mp4`, `temp_XXX_YYY.png`) are deleted automatically.
    - Logs show processed files, timestamps, and video sizes.

## Output

- **Video format**: H.264, FullHD (1920x1080), 24 FPS, ~1 GB per part.
- **Text overlay**: Date/time (e.g., `2025-04-17 04:45:38`) and coordinates (e.g., `Lat: 40.7128, Lon: -74.0060`), if available.
- **Duration**: Each photo is shown for 2 seconds.

## Customization

Modify global variables in the script to adjust:

- `TEXT_DATE_FORMAT`: Change to `%d.%m.%Y %H:%M:%S` for `17.04.2025 04:45:38`, etc.
- `FONT_SIZE`: Increase to `36` for larger text.
- `TEXT_POSITION`: Adjust to `("center", "bottom-150")` for different placement.
- `MAX_CLIPS_PER_PART`: Reduce to `250` if videos are too small.
- `BITRATE`: Increase to `"15M"` for larger files.

## Troubleshooting

- **Text not visible**: Check `FONT_TYPE` and `FONT_SIZE`. Ensure the font file exists.
- **Small videos**: Adjust `MAX_CLIPS_PER_PART` or `BITRATE`.
- **Incorrect order**: Verify file names and JSON metadata.
- **Errors**: Check logs for details (e.g., missing JSON, invalid images). Provide logs, file examples, and `pip show` output for support.

## Dependencies

See `requirements.txt` for Python libraries. FFmpeg is required separately.

## License

MIT License. Feel free to modify and distribute.

### Explanation

- **README.md**:
   - Describes the script's purpose: compiling photos into YouTube-ready videos.
   - Includes sections for overview, requirements, installation, usage, output, customization, troubleshooting, dependencies, and license.
   - Provides clear instructions for setting up FFmpeg and configuring global variables.
   - Mentions text overlay (date/time, coordinates), video format (~1 GB, FullHD), and customization options.
- **requirements.txt**:
   - Lists all Python libraries used in the script:
      - `moviepy==1.0.3`: For video creation and editing.
      - `opencv-python>=4.5.5`: For image loading and resizing.
      - `numpy>=1.21.0`: For array operations.
      - `psutil>=5.9.0`: For memory usage logging.
      - `Pillow>=10.0.0`: For text overlay (compatible with textbbox).
   - Excludes FFmpeg, as it’s a system dependency, not a Python package.

### Instructions

1. **Save the files**:
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install FFmpeg**:
   - Windows: `choco install ffmpeg` or download from `ffmpeg.org`.
   - Linux: `sudo apt install ffmpeg`.
   - macOS: `brew install ffmpeg`.
4. **Verify setup**:
   - Check Python libraries:
     ```bash
     pip show moviepy opencv-python numpy psutil Pillow
     ```
   - Check FFmpeg:

     ```bash
     ffmpeg -version
     ```
5. **Use the README**:
   - Refer to README.md for setup, usage, and troubleshooting.
   - Share it with others if distributing the script.

### If issues arise

If you encounter problems with dependencies or need clarification in the README, provide:

1. Output of pip show moviepy opencv-python numpy psutil Pillow.
2. FFmpeg version (ffmpeg -version).
3. Any specific feedback on the README content.