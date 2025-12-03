import json
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, ttk
import cv2
from contextlib import redirect_stdout, redirect_stderr
from moviepy import VideoFileClip

# Global paths and defaults relative to this script
image_folder = ""
video_folder = ""
output_folder = ""
submit_button = None
fetch_status_label = None
send_status_label = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTO_IMAGE_DIR = os.path.join(BASE_DIR, "IMAGES")
AUTO_VIDEO_DIR = os.path.join(BASE_DIR, "VIDEOS")
AUTO_OUTPUT_DIR = os.path.join(BASE_DIR, "OP")
GROUPS_SCRIPT_PATH = os.path.join(BASE_DIR, "getgroupdata.py")
SCHOOLS_FILE = os.path.join(BASE_DIR, "schools.json")


def open_win_diag_folder():
    """Select image folder."""
    global image_folder
    folder = filedialog.askdirectory(initialdir="")
    if folder:
        image_folder = folder
        image_label.config(text="Image Folder: " + os.path.basename(folder))
    else:
        image_folder = ""
        image_label.config(text="No Image Folder Selected")
    refresh_submit_state()


def open_video_folder():
    """Select folder containing source videos."""
    global video_folder
    folder = filedialog.askdirectory(initialdir="")
    if folder:
        video_folder = folder
        video_label.config(text="Video Folder: " + os.path.basename(folder))
    else:
        video_folder = ""
        video_label.config(text="No Video Folder Selected")
    refresh_submit_state()


def open_output_folder():
    """Select output folder for final video."""
    global output_folder
    folder = filedialog.askdirectory(initialdir="")
    if folder:
        output_folder = folder
        output_label.config(text="Output Folder: " + os.path.basename(folder))
    else:
        output_folder = ""
        output_label.config(text="No Output Folder Selected")
    refresh_submit_state()


def upload_file():
    """
    (Unused helper from original code – kept for completeness.)
    Lets user choose either an image or video file and inserts
    the folder path into a text field (e1/e2) – you can wire this
    back if you add those widgets.
    """
    file_type = file_type_var.get()
    file_path = filedialog.askopenfilename(
        title="Select a file",
        filetypes=[
            ("Image Files", "*.jpg *.png *.jpeg"),
            ("Video Files", "*.mp4 *.avi *.mov"),
        ],
    )

    if not file_path:
        return

    if file_type == "Image":
        e1.insert(0, os.path.dirname(file_path))
    elif file_type == "Video":
        e2.insert(0, os.path.dirname(file_path))


def initialize_default_dirs():
    """Auto-select the IMAGES/VIDEO folders only if both exist."""
    global image_folder, video_folder, output_folder
    has_images = os.path.isdir(AUTO_IMAGE_DIR)
    has_videos = os.path.isdir(AUTO_VIDEO_DIR)
    os.makedirs(AUTO_OUTPUT_DIR, exist_ok=True)

    if has_images:
        image_folder = AUTO_IMAGE_DIR
        image_label.config(text="Image Folder: IMAGES (auto)")
    else:
        image_folder = ""
        image_label.config(text="Image Folder missing – select above")

    if has_videos:
        video_folder = AUTO_VIDEO_DIR
        video_label.config(text="Video Folder: VIDEO (auto)")
    else:
        video_folder = ""
        video_label.config(text="Video Folder missing – select above")

    output_folder = AUTO_OUTPUT_DIR
    output_label.config(text="Output Folder: OP (auto)")
    refresh_submit_state()


def set_status_message(text, color="red"):
    """Update the generation status line."""
    status_label.config(text=text, fg=color)


def set_fetch_status_message(text, color="black"):
    """Update the fetch section status line."""
    if fetch_status_label:
        fetch_status_label.config(text=text, fg=color)


def set_send_status_message(text, color="blue"):
    """Update the send section status line."""
    if send_status_label:
        send_status_label.config(text=text, fg=color)


def refresh_submit_state():
    """Toggle the submit button state and status text based on folder readiness."""
    global submit_button
    ready_images = bool(image_folder) and os.path.isdir(image_folder)
    ready_videos = bool(video_folder) and os.path.isdir(video_folder)
    ready_output = bool(output_folder)
    ready = ready_images and ready_videos and ready_output

    if submit_button:
        submit_button.config(
            state=tk.NORMAL if ready else tk.DISABLED,
            bg="light green" if ready else "SystemButtonFace"
        )

    if ready:
        set_status_message("All folders ready. Submit enabled.", "green")
        return

    missing = []
    if not ready_images:
        missing.append("images")
    if not ready_videos:
        missing.append("videos")
    if not ready_output:
        missing.append("output")
    note = "Missing: " + ", ".join(missing) if missing else "Select folders before submitting."
    set_status_message(note, "red")


def submit_action():
    """Core logic: overlay PNG/JPG sequence on top of videos and export final MP4s with audio."""
    global image_folder, video_folder, output_folder

    # Basic validations and UI feedback
    if not os.path.isdir(image_folder):
        image_label.config(text="No Image Folder Found")
        print("Error: Image folder not found:", image_folder)
        return

    if not os.path.isdir(video_folder):
        video_label.config(text="No Video Folder Found")
        print("Error: Video folder not found:", video_folder)
        return

    if not output_folder:
        output_label.config(text="No Output Folder Found")
        print("Error: Output folder not selected")
        return

    os.makedirs(output_folder, exist_ok=True)

    # Collect image files
    image_files = [
        f for f in os.listdir(image_folder)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]
    print(f"Found {len(image_files)} image file(s) to process.")

    if not image_files:
        print("Error: No image files found in folder:", image_folder)
        return

    video_files = [
        os.path.join(video_folder, f)
        for f in sorted(os.listdir(video_folder))
        if f.lower().endswith((".mp4", ".avi", ".mov"))
    ]
    if not video_files:
        print("Error: No video files found in folder:", video_folder)
        return

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    for image_file in image_files:
        image_path = os.path.join(image_folder, image_file)
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print("Error: Unable to read the image file", image_path)
            continue

        img_height, img_width = img.shape[:2]

        for video_file in video_files:
            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                print("Error: Could not open video:", video_file)
                continue

            frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)
            frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"Video properties for {video_file}: {frame_width}x{frame_height}, {fps} fps, {frames} frames")

            base_video_name = os.path.splitext(os.path.basename(video_file))[0]
            video_output_dir = os.path.join(output_folder, base_video_name)
            os.makedirs(video_output_dir, exist_ok=True)

            scale_width = frame_width / img_width
            scale_height = frame_height / img_height
            scale = min(scale_width, scale_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

            x_offset = max((frame_width - new_width) // 2, 0)
            y_offset = 0

            has_alpha = img_resized.shape[2] == 4
            if has_alpha:
                img_bgr_float = img_resized[:, :, :3].astype("float32")
                alpha_mask = img_resized[:, :, 3].astype("float32") / 255.0
                alpha_mask = alpha_mask[:, :, None]
                mask_inv = 1.0 - alpha_mask
            else:
                img_bgr = img_resized[:, :, :3]

            tmp_path = os.path.join(
                video_output_dir,
                f"tmp_{os.path.splitext(image_file)[0]}_{base_video_name}.mp4"
            )
            op_video = cv2.VideoWriter(tmp_path, fourcc, fps, (frame_width, frame_height))

            try:
                while True:
                    ret, frame = video.read()
                    if not ret:
                        break

                    if has_alpha:
                        roi = frame[y_offset:y_offset + new_height, x_offset:x_offset + new_width]
                        if roi.shape[:2] == img_bgr_float.shape[:2]:
                            roi_float = roi.astype("float32")
                            blended = roi_float * mask_inv + img_bgr_float * alpha_mask
                            frame[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = blended.astype("uint8")
                    else:
                        roi = frame[y_offset:y_offset + new_height, x_offset:x_offset + new_width]
                        if roi.shape[:2] == img_bgr.shape[:2]:
                            frame[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = img_bgr

                    op_video.write(frame)
            finally:
                video.release()
                op_video.release()

            audio_clip = None
            try:
                with VideoFileClip(tmp_path) as video_clip:
                    audio_clip = VideoFileClip(video_file).audio
                    video_clip.audio = audio_clip
                    final_output_path = os.path.join(
                        video_output_dir,
                        f"{os.path.splitext(image_file)[0]}.mp4"
                    )
                    with open(os.devnull, "w") as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
                        video_clip.write_videofile(
                            final_output_path,
                            codec="libx264",
                            audio_codec="aac"
                        )
                    print(f"Video file generation completed for {final_output_path}.")
            finally:
                if audio_clip:
                    audio_clip.close()
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    cv2.destroyAllWindows()

    print("Videos Uploaded Successfully")


def fetch_group_data():
    """Run the helper script that fetches and caches groups.json."""
    try:
        result = subprocess.run(
            [sys.executable, GROUPS_SCRIPT_PATH],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            check=False,
        )
    except Exception as exc:
        message = f"Unable to launch fetch script: {exc}"
        print(message)
        set_fetch_status_message(message, "red")
        return

    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip() or "Fetch script failed."
        message = f"Fetch failed: {error_text}"
        print(message)
        set_fetch_status_message(message, "red")
        return

    if result.stdout.strip():
        print(result.stdout.strip())
    set_fetch_status_message("Groups data fetched and saved via script.", "green")


def _collect_local_image_names():
    if not os.path.isdir(AUTO_IMAGE_DIR):
        return set()
    names = set()
    for entry in os.listdir(AUTO_IMAGE_DIR):
        base_name, _ = os.path.splitext(entry)
        names.add(base_name)
    return names


def check_images():
    """Update schools.json image_status by checking available images."""
    if not os.path.exists(SCHOOLS_FILE):
        message = "schools.json missing; run Fetch Data first."
        print(message)
        set_fetch_status_message(message, "red")
        return

    try:
        with open(SCHOOLS_FILE, "r", encoding="utf-8") as fp:
            schools_payload = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        message = f"Unable to read schools.json: {exc}"
        print(message)
        set_fetch_status_message(message, "red")
        return

    schools = schools_payload.get("schools")
    if not isinstance(schools, list):
        message = "schools.json has unexpected format."
        print(message)
        set_fetch_status_message(message, "red")
        return

    image_names = _collect_local_image_names()
    no_schools = [
        school for school in schools
        if isinstance(school, dict) and school.get("image_status", "no").lower() == "no"
    ]

    if not no_schools:
        message = "All schools already have images."
        print(message)
        set_fetch_status_message(message, "green")
        return

    updated = 0
    for school in no_schools:
        normalized_id = school.get("id", "").replace("@g.us", "")
        if normalized_id in image_names:
            school["image_status"] = "yes"
            updated += 1

    if updated:
        try:
            with open(SCHOOLS_FILE, "w", encoding="utf-8") as fp:
                json.dump(schools_payload, fp, ensure_ascii=False, indent=2)
        except OSError as exc:
            message = f"Failed to write schools.json: {exc}"
            print(message)
            set_fetch_status_message(message, "red")
            return
        status = f"Updated {updated} schools from 'no' to 'yes'."
        print(status)
        set_fetch_status_message(status, "green")
    else:
        status = f"Checked {len(no_schools)} schools; still no local images."
        print(status)
        set_fetch_status_message(status)




# ---------------- GUI SETUP ----------------

m = tk.Tk()
m.geometry("800x420")
m.title("Edplore Video Maker")

# Layout frames for the three areas with separators between them.
m.columnconfigure(0, weight=1)
m.columnconfigure(1, weight=0)
m.columnconfigure(2, weight=2)
m.columnconfigure(3, weight=0)
m.columnconfigure(4, weight=1)
m.rowconfigure(0, weight=1)

fetch_frame = tk.Frame(m, bd=2, relief="groove", padx=10, pady=10)
fetch_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

sep_left = ttk.Separator(m, orient="vertical")
sep_left.grid(row=0, column=1, sticky="ns", padx=5, pady=10)

generation_frame = tk.Frame(m, bd=2, relief="groove", padx=15, pady=15)
generation_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=10)

sep_right = ttk.Separator(m, orient="vertical")
sep_right.grid(row=0, column=3, sticky="ns", padx=5, pady=10)

send_frame = tk.Frame(m, bd=2, relief="groove", padx=10, pady=10)
send_frame.grid(row=0, column=4, sticky="nsew", padx=(5, 10), pady=10)

fetch_button = tk.Button(fetch_frame, text="Fetch Data", width=25, command=fetch_group_data)
fetch_button.pack(expand=True)

check_button = tk.Button(fetch_frame, text="Check Images", width=25, command=check_images)
check_button.pack(expand=True, pady=(10, 0))

fetch_status_label = tk.Label(fetch_frame, text="Messages appear here", fg="green")
fetch_status_label.pack(side="bottom", pady=(10, 0))

image_label = tk.Label(generation_frame, text="")
image_label.grid(row=0, column=0, padx=5, pady=(0, 5))

video_label = tk.Label(generation_frame, text="")
video_label.grid(row=1, column=0, padx=5, pady=5)

output_label = tk.Label(generation_frame, text="")
output_label.grid(row=2, column=0, padx=5, pady=5)

status_label = tk.Label(generation_frame, text="Folder status will appear here", fg="red")
status_label.grid(row=3, column=0, padx=5, pady=(0, 15))

image_button = tk.Button(generation_frame, text="Select Image Folder", width=25, command=open_win_diag_folder)
image_button.grid(row=4, column=0, padx=5, pady=5)

video_button = tk.Button(generation_frame, text="Select Video Folder", width=25, command=open_video_folder)
video_button.grid(row=5, column=0, padx=5, pady=5)

output_button = tk.Button(generation_frame, text="Select Output Folder", width=25, command=open_output_folder)
output_button.grid(row=6, column=0, padx=5, pady=5)

submit_button = tk.Button(generation_frame, text="Submit", width=25, command=submit_action)
submit_button.grid(row=7, column=0, padx=5, pady=5)

send_status_label = tk.Label(send_frame, text="Send data pending.", fg="blue")
send_status_label.pack(pady=(0, 20))

send_button = tk.Button(send_frame, text="Send Data", width=25,
                        command=lambda: set_send_status_message("Send data feature pending.", "blue"))
send_button.pack(expand=True)

initialize_default_dirs()
refresh_submit_state()

m.mainloop()
