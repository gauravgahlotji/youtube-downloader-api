import os
import shutil
import yt_dlp
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logger import log_event
from app.engine.progress_hook import YTDLPProgressHook, StepEvent


class YTDLPEngine:
    @staticmethod
    def get_common_opts() -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "restrictfilenames": True,
        }
        # Check if deno binary exists in system or common paths
        deno_path = shutil.which("deno") or "/home/appuser/.deno/bin/deno"
        if os.path.exists(deno_path):
            opts["js_runtimes"] = {"deno": {"path": deno_path}}
        return opts

    @classmethod
    def validate_and_extract_metadata(cls, url: str) -> Dict[str, Any]:
        log_event("DOWNLOAD_LOGS", "INFO", f"Extracting metadata for URL: {url}")
        opts = cls.get_common_opts()
        opts["extract_flat"] = "in_playlist"
        opts["skip_download"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                log_event("ERROR_LOGS", "ERROR", f"Metadata extraction failed for {url}: {str(e)}")
                raise ValueError(f"Failed to extract video metadata: {str(e)}")

        formats_list = []
        if "formats" in info:
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" or f.get("acodec") != "none":
                    formats_list.append({
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "resolution": f.get("resolution") or f"{f.get('width', '')}x{f.get('height', '')}",
                        "height": f.get("height"),
                        "fps": f.get("fps"),
                        "vcodec": f.get("vcodec"),
                        "acodec": f.get("acodec"),
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                        "filesize_human": f"{round((f.get('filesize') or f.get('filesize_approx') or 0)/1024/1024, 2)} MB" if (f.get('filesize') or f.get('filesize_approx')) else "Unknown",
                    })

        subtitles_list = list(info.get("subtitles", {}).keys()) + list(info.get("automatic_captions", {}).keys())

        return {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "duration_string": info.get("duration_string") or (f"{info.get('duration')}s" if info.get("duration") else "Unknown"),
            "uploader": info.get("uploader") or info.get("channel"),
            "thumbnail": info.get("thumbnail"),
            "description": info.get("description", "")[:300] if info.get("description") else "",
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "formats": formats_list[:20],  # Return top formats
            "subtitles": subtitles_list[:10],
            "is_playlist": info.get("_type") == "playlist" or "entries" in info,
            "playlist_count": len(info.get("entries", [])) if "entries" in info else 1
        }

    @classmethod
    def execute_video_download(
        cls,
        url: str,
        job_id: str,
        quality: str = "best",
        format_ext: str = "mp4",
        include_subtitles: bool = False,
        sub_lang: str = "en",
        update_callback: Optional[Any] = None
    ) -> str:
        output_template = str(settings.DOWNLOAD_DIR / f"{job_id}.%(ext)s")
        opts = cls.get_common_opts()

        # Quality format selector mapping
        format_str = "bestvideo+bestaudio/best"
        if quality == "1080p":
            format_str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        elif quality == "720p":
            format_str = "bestvideo[height<=720]+bestaudio/best[height<=720]"
        elif quality == "480p":
            format_str = "bestvideo[height<=480]+bestaudio/best[height<=480]"
        elif quality == "360p":
            format_str = "bestvideo[height<=360]+bestaudio/best[height<=360]"
        elif quality == "4k":
            format_str = "bestvideo[height<=2160]+bestaudio/best[height<=2160]"

        opts.update({
            "outtmpl": output_template,
            "format": format_str,
            "merge_output_format": format_ext,
        })

        if include_subtitles:
            opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [sub_lang],
                "subtitlesformat": "vtt/srt",
            })

        if update_callback:
            hook = YTDLPProgressHook(job_id, update_callback)
            opts["progress_hooks"] = [hook]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # If merged format was specified, file extension might be updated
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                expected_target = f"{base}.{format_ext}"
                if os.path.exists(expected_target):
                    filename = expected_target

        return filename

    @classmethod
    def execute_audio_download(
        cls,
        url: str,
        job_id: str,
        audio_format: str = "mp3",
        bitrate: str = "192",
        update_callback: Optional[Any] = None
    ) -> str:
        output_template = str(settings.DOWNLOAD_DIR / f"{job_id}.%(ext)s")
        opts = cls.get_common_opts()

        opts.update({
            "outtmpl": output_template,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": bitrate,
            }],
        })

        if update_callback:
            hook = YTDLPProgressHook(job_id, update_callback)
            opts["progress_hooks"] = [hook]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base = os.path.splitext(ydl.prepare_filename(info))[0]
            filename = f"{base}.{audio_format}"

        return filename

    @classmethod
    def execute_thumbnail_download(cls, url: str, job_id: str) -> str:
        meta = cls.validate_and_extract_metadata(url)
        thumb_url = meta.get("thumbnail")
        if not thumb_url:
            raise ValueError("No thumbnail available for this video.")

        import httpx
        target_path = settings.DOWNLOAD_DIR / f"{job_id}.jpg"
        response = httpx.get(thumb_url, follow_redirects=True, timeout=15)
        response.raise_for_status()

        with open(target_path, "wb") as f:
            f.write(response.content)

        return str(target_path)
