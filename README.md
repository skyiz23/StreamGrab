# YT 4K Downloader — Public Web Downloader

A Flask + yt-dlp web app with 360p, 720p, 1080p, 1440p and 2160p options.

## Run locally

Requirements: Python 3.11+ and FFmpeg.

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Deploy publicly with Render

This project includes a `Dockerfile`, so FFmpeg is installed inside the server automatically.

1. Put the project in a GitHub repository.
2. In Render, choose **New → Web Service** and connect the repository.
3. Set **Language/Runtime: Docker**.
4. Deploy.

Render provides a public `onrender.com` URL. The Docker image starts Gunicorn and binds to Render's `PORT` automatically.

The included `render.yaml` is optional; the Dockerfile is enough for deployment.

## Notes

- Downloads are stored temporarily and cleaned after 30 minutes by default.
- The app uses one Gunicorn worker because job state is held in memory.
- Public hosting resources are limited, so this is intended as a school/demo project rather than a high-volume service.
- Use the downloader only for videos you own, have permission to download, or that are otherwise legally available for downloading. Follow the source platform's terms.
