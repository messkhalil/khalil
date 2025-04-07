from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid
import re
import time
from datetime import datetime

app = Flask(__name__)

# تكوين المجلد المؤقت للتحميلات
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_downloads')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# إعدادات yt-dlp
ydl_opts = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': True,
}

def is_valid_youtube_url(url):
    """التحقق من صحة رابط يوتيوب"""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/v/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def format_size(bytes):
    """تنسيق حجم الملف"""
    for unit in ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} تيرابايت"

def format_duration(seconds):
    """تنسيق المدة الزمنية"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({"error": "يرجى إدخال رابط الفيديو"}), 400
        
        if not is_valid_youtube_url(url):
            return jsonify({"error": "الرجاء إدخال رابط يوتيوب صحيح"}), 400

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                return jsonify({"error": f"خطأ في استخراج معلومات الفيديو: {str(e)}"}), 400

            # تحضير تنسيقات الفيديو
            video_formats = []
            audio_formats = []

            for f in info['formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    # تنسيقات الفيديو مع الصوت
                    video_formats.append({
                        'itag': f['format_id'],
                        'resolution': f.get('height', 'unknown'),
                        'mime_type': f.get('ext', 'mp4'),
                        'fps': f.get('fps', 'unknown'),
                        'filesize': format_size(f.get('filesize', 0) or 0)
                    })
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    # تنسيقات الصوت فقط
                    audio_formats.append({
                        'itag': f['format_id'],
                        'abr': f.get('abr', 'unknown'),
                        'mime_type': f.get('ext', 'mp3'),
                        'filesize': format_size(f.get('filesize', 0) or 0)
                    })

            return jsonify({
                "title": info['title'],
                "thumbnail": info.get('thumbnail', ''),
                "author": info.get('uploader', ''),
                "length": info.get('duration', 0),
                "views": info.get('view_count', 0),
                "publish_date": info.get('upload_date', ''),
                "video_streams": video_formats,
                "audio_streams": audio_formats
            })

    except Exception as e:
        return jsonify({"error": f"حدث خطأ أثناء معالجة الفيديو: {str(e)}"}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        url = request.json.get('url')
        format_id = request.json.get('itag')
        file_type = request.json.get('type', 'video')
        
        if not url or not format_id:
            return jsonify({"error": "معلومات غير كافية للتحميل"}), 400

        # إنشاء اسم ملف فريد
        filename = f"{uuid.uuid4()}"
        if file_type == 'audio':
            filename += ".mp3"
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(TEMP_DIR, filename),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            }
        else:
            filename += ".mp4"
            ydl_opts = {
                'format': format_id,
                'outtmpl': os.path.join(TEMP_DIR, filename),
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                final_filename = filename
                
                return jsonify({
                    "download_url": f"/download/{final_filename}",
                    "filename": f"{info['title']}.{filename.split('.')[-1]}"
                })
            except Exception as e:
                return jsonify({"error": f"فشل في تحميل الفيديو: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"حدث خطأ أثناء التحميل: {str(e)}"}), 500

@app.route('/download/<filename>')
def serve_file(filename):
    try:
        file_path = os.path.join(TEMP_DIR, filename)
        if not os.path.exists(file_path):
            return "الملف غير موجود", 404

        original_filename = request.args.get('name', 'download')
        return send_file(
            file_path,
            as_attachment=True,
            download_name=original_filename,
            mimetype='video/mp4' if filename.endswith('.mp4') else 'audio/mpeg'
        )
    except Exception as e:
        return f"حدث خطأ: {str(e)}", 500

def clean_temp_files():
    """تنظيف الملفات المؤقتة القديمة"""
    try:
        current_time = time.time()
        for file in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file)
            if os.path.isfile(file_path) and current_time - os.path.getmtime(file_path) > 3600:
                os.remove(file_path)
    except Exception as e:
        print(f"خطأ في تنظيف الملفات المؤقتة: {str(e)}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
