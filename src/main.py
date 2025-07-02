import re
import os
import random
import subprocess
from pathlib import Path
from youtubesearchpython import VideosSearch
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# === Config ===
NUM_VIDEOS = 3
REELS_PER_VIDEO = 2
REEL_DURATION = 10  # seconds
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

# === Captions ===
CAPTIONS = [
    "This scene is so funny 😂",
    "This hits different",
    "I love this actor 😍",
    "Peak fiction!",
    "How can anyone not love this!",
    "Too good 🔥",
    "ICONIC moment 🤌",
    "I’ve watched this 10 times",
]

# === Helpers ===
def sanitize_filename(name: str) -> str:
    """Remove or replace characters invalid for file names."""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

# === Step 1: Search YouTube ===
def search_youtube_videos(keyword: str, num_results: int = 1):
    """Try VideosSearch; fallback to yt-dlp search if it fails."""
    print(f"🔍 Searching YouTube for: {keyword}")
    try:
        videos_search = VideosSearch(keyword, limit=num_results)
        results = videos_search.result().get('result', [])
        return [(item['title'], item['link']) for item in results]
    except Exception:
        # fallback: use yt-dlp search
        cmd = [
            "yt-dlp",
            f"ytsearch{num_results}:{keyword}",
            "--print", "%(title)s|||%(webpage_url)s",
            "--skip-download"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        videos = []
        for line in proc.stdout.strip().splitlines():
            if '|||' in line:
                title, url = line.split('|||', 1)
                videos.append((title.strip(), url.strip()))
        return videos

# === Step 2: Download video using yt-dlp ===
def download_video(title: str, url: str) -> Path:
    safe_title = sanitize_filename(title)
    filepath = VIDEO_DIR / f"{safe_title}.mp4"

    if filepath.exists():
        print(f"📁 Already downloaded: {filepath.name}")
        return filepath

    print(f"📥 Downloading: {title}")
    subprocess.run([
        "yt-dlp", url,
        "-o", str(filepath)
    ], check=True)
    return filepath

# === Step 3: Clip a short reel ===
def clip_video(input_path: Path, start: int, duration: int, output_path: Path) -> Path:
    print(f"🎬 Clipping: {input_path.name} [{start}s -> {start + duration}s]")
    with VideoFileClip(str(input_path)) as clip:
        try:
            sub = clip.subclip(start, start + duration)
        except AttributeError:
            sub = clip.subclipped(start, start + duration)
        sub.write_videofile(str(output_path), codec="libx264", audio_codec="aac")
    return output_path

# === Step 4: Add a caption ===
def add_caption(video_path: Path, caption: str, output_path: Path) -> Path:
    print(f"📝 Adding caption: '{caption}'")
    with VideoFileClip(str(video_path)) as video:
        try:
            txt_clip = (TextClip(caption, fontsize=50, color='white', 
                        font='Arial-Unicode-Regular',  # Try this common font
                        size=(video.size[0]*0.9, None))
                        .set_position(('center', 'top'))
                        .set_duration(video.duration))
            final = CompositeVideoClip([video, txt_clip])
            final.write_videofile(str(output_path), fps=24)
        except Exception as e:
            print(f"⚠️ Could not add caption: {e}")
            # Fallback - copy the video without caption
            video.write_videofile(str(output_path), fps=24)
    return output_path

# === Step 5: Generate Reels from One Video ===
def create_reels_from_video(video_path: Path, base_title: str):
    try:
        with VideoFileClip(str(video_path)) as video:
            duration = int(video.duration)
    except Exception as e:
        print(f"⚠️ Could not load video {video_path.name}: {e}")
        return []

    reels = []
    for i in range(REELS_PER_VIDEO):
        start = random.randint(0, max(0, duration - REEL_DURATION))
        caption = random.choice(CAPTIONS)
        reel_file = VIDEO_DIR / f"{base_title}_reel{i+1}.mp4"
        captioned_file = VIDEO_DIR / f"{base_title}_reel{i+1}_caption.mp4"

        clip_video(video_path, start, REEL_DURATION, reel_file)
        add_caption(reel_file, caption, captioned_file)
        reels.append(captioned_file)

    return reels

# === Main ===
def main():
    keyword = input("Enter genre or keyword: ")
    results = search_youtube_videos(keyword, NUM_VIDEOS)

    if not results:
        print("No results found.")
        return

    for title, url in results:
        print(f"\n📥 Processing video: {title}")
        try:
            video_path = download_video(title, url)
            safe_title = sanitize_filename(title)
            create_reels_from_video(video_path, safe_title)
        except subprocess.CalledProcessError:
            print(f"❌ Failed to download {title}")

    print("\n✅ All reels generated in 'videos/' folder.")

if __name__ == "__main__":
    main()