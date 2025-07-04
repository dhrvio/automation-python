import os
import re
import random
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from youtubesearchpython import VideosSearch
from instagrapi import Client

# === Load environment from .env ===
load_dotenv()

# === Config from Environment ===
SEARCH_TERM  = os.environ.get("YT_SEARCH_TERM")
NUM_SHORTS   = int(os.environ.get("YT_SHORTS_COUNT", 10))
MIN_VIEWS    = int(os.environ.get("YT_MIN_VIEWS", 10000))    # threshold for "nice" views
MAX_AGE_DAYS = int(os.environ.get("YT_MAX_AGE_DAYS", 700))    # only recent uploads
IG_USERNAME  = os.environ.get("IG_USERNAME")
IG_PASSWORD  = os.environ.get("IG_PASSWORD")

# Create output directory
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)

# === Helpers ===

def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in (' ', '.', '_') else '_' for c in name).strip()


def parse_views(text: str) -> int:
    """
    Convert strings like '1.2M views', '500K views' into an integer.
    """
    num_str = text.lower().replace(' views', '').strip()
    match = re.match(r"([\d\.,]+)([km]?)", num_str)
    if not match:
        return 0
    val, suffix = match.groups()
    val = float(val.replace(',', ''))
    if suffix == 'k':
        val *= 1_000
    elif suffix == 'm':
        val *= 1_000_000
    return int(val)


def parse_age_days(published: str) -> int:
    """
    Convert strings like '3 hours ago', '2 days ago', '1 week ago', '5 months ago'
    into a rough day-count. Unknown formats count as old (> MAX_AGE_DAYS).
    """
    parts = published.lower().split()
    if len(parts) < 2:
        return MAX_AGE_DAYS + 1

    try:
        n = int(parts[0])
    except ValueError:
        return MAX_AGE_DAYS + 1

    unit = parts[1]
    if 'minute' in unit or 'hour' in unit:
        return 0
    if 'day' in unit:
        return n
    if 'week' in unit:
        return n * 7
    if 'month' in unit:
        return n * 30
    if 'year' in unit:
        return n * 365

    return MAX_AGE_DAYS + 1


def search_recent_shorts(keyword: str, limit: int = 10):
    print(f"🔍 Searching for recent shorts: {keyword}")
    raw = VideosSearch(f"{keyword} #shorts", limit=limit * 3).result().get('result', [])
    shorts = []

    for item in raw:
        title      = item.get('title', 'No title')
        url        = item.get('link')
        channel    = item.get('channel', {}).get('name', 'Unknown')
        views_text = item.get('viewCount', {}).get('text', '0 views')
        age_text   = item.get('publishedTime', '')

        views = parse_views(views_text)
        age   = parse_age_days(age_text)

        if views < MIN_VIEWS:
            print(f"  ✂️ SKIP '{title}' — only {views_text}")
            continue
        if age > MAX_AGE_DAYS:
            print(f"  ✂️ SKIP '{title}' — {age_text} (>{MAX_AGE_DAYS} days)")
            continue

        print(f"  ✅ KEEP '{title}' — {views_text}, {age_text}")
        shorts.append((title, url, channel))
        if len(shorts) >= limit:
            break

    return shorts


def download_video(title: str, url: str) -> Path:
    safe = sanitize_filename(title)
    out  = VIDEO_DIR / f"{safe}.mp4"
    if not out.exists():
        print(f"📥 Downloading: {title}")
        subprocess.run(["yt-dlp", url, "-f", "mp4", "-o", str(out)], check=True)
    else:
        print(f"📁 Already exists: {out.name}")
    return out


def upload_reel(video_path: Path, caption: str):
    cl = Client()
    cl.login(IG_USERNAME, IG_PASSWORD)
    print(f"🚀 Uploading to Instagram: {video_path.name}")
    cl.clip_upload(str(video_path), caption)
    cl.logout()


def main():
    if not (SEARCH_TERM and IG_USERNAME and IG_PASSWORD):
        print("⚠️ Please set YT_SEARCH_TERM, IG_USERNAME & IG_PASSWORD in your .env or shell.")
        return

    shorts = search_recent_shorts(SEARCH_TERM, NUM_SHORTS)
    if not shorts:
        print("❌ No suitable shorts found.")
        return

    for title, url, channel in shorts:
        try:
            vid    = download_video(title, url)
            credit = f"Credit: {channel} - {title}"
            upload_reel(vid, credit)
        except Exception as e:
            print(f"⚠️ Error processing '{title}': {e}")

    print("✅ Done: All reels uploaded.")

if __name__ == "__main__":
    main()
