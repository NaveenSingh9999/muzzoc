from flask import Flask, render_template, request, Response, send_from_directory, send_file
import os, json, threading, requests
import yt_dlp
from queue import Queue
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import io

app = Flask(__name__)
DOWNLOAD_FOLDER = '../../Music/'
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

progress_queue = Queue()

def sanitize_filename(name):
    """Removes invalid characters for file systems."""
    return "".join(c for c in name if c.isalnum() or c in " _-").rstrip()

def search_and_download_youtube(song_name, queue):
    def progress_hook(d):
        if d['status'] == 'downloading':
            progress_info = {
                'status': 'downloading',
                'progress_str': d['_percent_str'],
                'eta': d['_eta_str'],
            }
            queue.put(json.dumps(progress_info))
        elif d['status'] == 'finished':
            queue.put(json.dumps({'status': 'converting'}))

    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'progress_hooks': [progress_hook],
        'quiet': True,
        'skip_download': False,
        'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'writethumbnail': True,  # downloads thumbnail
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song_name, download=True)
        
        title = sanitize_filename(info.get("title", song_name))
        artist = info.get("artist") or info.get("uploader") or "Unknown Artist"
        album = info.get("album") or "Unknown Album"
        thumbnail_url = info.get("thumbnail")

        mp3_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{title}.mp3")

        # ✅ Embed metadata + thumbnail
        if os.path.exists(mp3_path):
            try:
                audio = EasyID3(mp3_path)
            except:
                audio = EasyID3()
            audio["title"] = title
            audio["artist"] = artist
            audio["album"] = album
            audio.save(mp3_path)

            if thumbnail_url:
                img_data = requests.get(thumbnail_url).content
                audio = ID3(mp3_path)
                audio['APIC'] = APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=img_data
                )
                audio.save(mp3_path)

        queue.put(json.dumps({
            'status': 'completed',
            'song': title,
            'artist': artist,
            'album': album
        }))

    except Exception as e:
        queue.put(json.dumps({'status': 'error', 'message': str(e)}))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    song_name = request.form['song_name']
    download_thread = threading.Thread(target=search_and_download_youtube, args=(song_name, progress_queue))
    download_thread.start()
    return render_template('download.html', song_name=song_name)

@app.route('/progress')
def progress():
    def generate():
        while True:
            message = progress_queue.get()
            yield f"data: {message}\n\n"
            data = json.loads(message)
            if data['status'] in ['completed', 'error']:
                break
    return Response(generate(), mimetype='text/event-stream')

@app.route('/songs')
def list_songs():
    songs = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith('.mp3')]
    return render_template('songs.html', songs=songs)

@app.route('/play/<filename>')
def play(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename)


@app.route('/cover/<path:filename>')
def cover(filename):
    # Serve embedded cover art from MP3 APIC frame when available
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return send_from_directory('static', 'default-artwork.png')
    try:
        tags = ID3(file_path)
        apic = None
        for key in tags.keys():
            if key.startswith('APIC'):
                apic = tags.get(key)
                break
        if apic and getattr(apic, 'data', None):
            mime = getattr(apic, 'mime', 'image/jpeg') or 'image/jpeg'
            return send_file(io.BytesIO(apic.data), mimetype=mime)
    except Exception:
        pass
    return send_from_directory('static', 'default-artwork.png')

if __name__ == '__main__':
    app.run(host='0.0.0.0',port='5000',debug=True)
