from flask import Flask, render_template, request, jsonify, send_file
import os, uuid, threading, time
import yt_dlp

app = Flask(__name__)
DOWNLOAD_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Keep temporary downloads from filling the server disk.
FILE_TTL_SECONDS = int(os.getenv("FILE_TTL_SECONDS", "1800"))

jobs = {}

def cleanup_old_files():
    now = time.time()
    for name in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, name)
        try:
            if os.path.isfile(path) and now - os.path.getmtime(path) > FILE_TTL_SECONDS:
                os.remove(path)
        except OSError:
            pass

QUALITY_MAP = {
    "360": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "1440": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
}

def download_video(job_id, url, quality):
    cleanup_old_files()
    jobs[job_id] = {"status": "starting", "progress": 0, "filename": None, "error": None}

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            current = d.get("downloaded_bytes", 0)
            if total:
                jobs[job_id]["progress"] = round(current / total * 100, 1)
            jobs[job_id]["status"] = "downloading"
        elif d["status"] == "finished":
            jobs[job_id]["progress"] = 100
            jobs[job_id]["status"] = "processing"

    output = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    options = {
        "format": QUALITY_MAP.get(quality, QUALITY_MAP["1080"]),
        "outtmpl": output,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
            requested = info.get("requested_downloads") or []
            final = os.path.join(DOWNLOAD_DIR, f"{job_id}.mp4")

            # If yt-dlp selected another final extension, find the generated file.
            if not os.path.exists(final):
                candidates = [
                    os.path.join(DOWNLOAD_DIR, x)
                    for x in os.listdir(DOWNLOAD_DIR)
                    if x.startswith(job_id + ".")
                ]
                if candidates:
                    final = max(candidates, key=os.path.getsize)

            jobs[job_id].update({
                "status": "complete",
                "progress": 100,
                "filename": final,
                "title": title,
            })
    except Exception as e:
        jobs[job_id].update({"status": "error", "error": str(e)})

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/info")
def info():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "Please enter a video URL."}), 400

    try:
        opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(url, download=False)
        return jsonify({
            "title": result.get("title"),
            "thumbnail": result.get("thumbnail"),
            "duration": result.get("duration"),
            "uploader": result.get("uploader"),
        })
    except Exception as e:
        return jsonify({"error": "Could not read this URL. Check the link and try again."}), 400

@app.post("/api/download")
def start_download():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    quality = str((data or {}).get("quality", "1080"))

    if not url:
        return jsonify({"error": "Please enter a video URL."}), 400
    if quality not in QUALITY_MAP:
        return jsonify({"error": "Unsupported quality."}), 400

    job_id = uuid.uuid4().hex
    threading.Thread(
        target=download_video,
        args=(job_id, url, quality),
        daemon=True
    ).start()

    return jsonify({"job_id": job_id})

@app.get("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404

    response = dict(job)
    if response.get("filename"):
        response["download_url"] = f"/api/file/{job_id}"
        response.pop("filename", None)
    return jsonify(response)

@app.get("/api/file/<job_id>")
def get_file(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("filename") or not os.path.exists(job["filename"]):
        return jsonify({"error": "File is not ready."}), 404

    return send_file(
        job["filename"],
        as_attachment=True,
        download_name=f'{job.get("title", "video")}.mp4'
    )

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
