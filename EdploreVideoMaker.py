import tkinter as tk
from tkinter import filedialog
import os
import cv2
from moviepy import VideoFileClip

# Global paths
image_folder = ""
video_folder = ""
output_folder = ""


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
    print("Found image files:", image_files)

    if not image_files:
        print("Error: No image files found in folder:", image_folder)
        return

    # Source videos list
    video_files = [
        os.path.join(video_folder, f)
        for f in sorted(os.listdir(video_folder))
        if f.lower().endswith((".mp4", ".avi", ".mov"))
    ]
    if not video_files:
        print("Error: No video files found in folder:", video_folder)
        return

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

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
        video.release()

        base_video_name = os.path.splitext(os.path.basename(video_file))[0]

        for image_file in image_files:
            image_path = os.path.join(image_folder, image_file)
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                print("Error: Unable to read the image file", image_path)
                continue

            img_height, img_width = img.shape[:2]

            # Maintain aspect ratio and fit into video frame
            scale_width = frame_width / img_width
            scale_height = frame_height / img_height
            scale = min(scale_width, scale_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

            x_offset = max((frame_width - new_width) // 2, 0)
            y_offset = 0  # align overlay at top of the frame

            has_alpha = img_resized.shape[2] == 4
            if has_alpha:
                img_bgr_float = img_resized[:, :, :3].astype("float32")
                alpha_mask = img_resized[:, :, 3].astype("float32") / 255.0
                alpha_mask = alpha_mask[:, :, None]
                mask_inv = 1.0 - alpha_mask
            else:
                img_bgr = img_resized[:, :, :3]

            tmp_path = os.path.join(
                output_folder,
                f"tmp_{base_video_name}_{os.path.splitext(image_file)[0]}.mp4"
            )
            op_video = cv2.VideoWriter(tmp_path, fourcc, fps, (frame_width, frame_height))

            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                print("Error: Could not open video for image", image_file)
                op_video.release()
                continue

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

            video.release()
            op_video.release()

            video_clip = VideoFileClip(tmp_path)
            final_output_path = os.path.join(
                output_folder,
                f"{base_video_name}_{os.path.splitext(image_file)[0]}.mp4"
            )
            audio_clip = VideoFileClip(video_file).audio
            video_clip.audio = audio_clip
            video_clip.write_videofile(
                final_output_path,
                codec="libx264",
                audio_codec="aac"
            )
            video_clip.close()
            audio_clip.close()
            os.remove(tmp_path)

    cv2.destroyAllWindows()

    print("Videos Uploaded Successfully")


# ---------------- GUI SETUP ----------------

m = tk.Tk()
m.geometry("500x400")
m.title("Edplore Video Maker")

image_label = tk.Label(m, text="")
image_label.grid(row=0, columnspan=2, padx=5, pady=5)

video_label = tk.Label(m, text="")
video_label.grid(row=1, columnspan=2, padx=5, pady=5)

output_label = tk.Label(m, text="")
output_label.grid(row=2, columnspan=2, padx=5, pady=5)

image_button = tk.Button(m, text="Select Image Folder", width=25, command=open_win_diag_folder)
image_button.grid(row=3, columnspan=2, padx=5, pady=5)

video_button = tk.Button(m, text="Select Video Folder", width=25, command=open_video_folder)
video_button.grid(row=4, columnspan=2, padx=5, pady=5)

output_button = tk.Button(m, text="Select Output Folder", width=25, command=open_output_folder)
output_button.grid(row=5, columnspan=2, padx=5, pady=5)

submit_button = tk.Button(m, text="Submit", width=25, command=submit_action)
submit_button.grid(row=6, columnspan=2, padx=5, pady=5)

m.mainloop()
