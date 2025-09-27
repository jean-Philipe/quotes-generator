from flask import Flask, request, send_file
import os
import requests
import subprocess
from uuid import uuid4
import textwrap

app = Flask(__name__)

def wrap_text_lines(text, max_chars_per_line=25):
    return textwrap.wrap(text, width=max_chars_per_line)

def build_drawtext_filters(lines, font_path, author, author_font_path, font_size=38, spacing=10):
    drawtext_filters = []
    total_lines = len(lines)
    line_height = font_size + spacing
    base_y = 640  # vertical center of 1280 height
    start_y = base_y - (line_height * total_lines // 2)

    # Quote lines (with yellow background box)
    for i, line in enumerate(lines):
        y_position = start_y + i * line_height
        drawtext = (
            f"drawtext=fontfile={font_path}:"
            f"text='{line}':"
            f"fontcolor=black:fontsize={font_size}:"
            f"box=1:boxcolor=yellow@0.6:boxborderw=6:"
            f"x=(w-text_w)/2:y={y_position}"
        )
        drawtext_filters.append(drawtext)

    # Author (without box, smaller font, with dash)
    if author:
        author_y = start_y + total_lines * line_height + spacing * 2
        author_line = f"- {author}"
        author_drawtext = (
            f"drawtext=fontfile={author_font_path}:"
            f"text='{author_line}':"
            f"fontcolor=black:fontsize={font_size - 10}:"
            f"x=(w-text_w)/2:y={author_y}"
        )
        drawtext_filters.append(author_drawtext)

    return ",".join(drawtext_filters)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    quote = request.form.get('quote')
    author = request.form.get('author', '')
    file_url = request.form.get('fileUrl')  # <-- CAMBIO
    file_url = get_direct_download_url(file_url)

    if not quote or not file_url:
        return {"error": "Missing 'quote' or 'fileUrl'"}, 400

    image_path = f"/tmp/{uuid4()}.png"
    video_path = f"/tmp/{uuid4()}.mp4"

    try:
        response = requests.get(file_url)  # <-- CAMBIO
        response.raise_for_status()
        with open(image_path, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        return {"error": f"Failed to download image: {str(e)}"}, 500

    lines = wrap_text_lines(quote, max_chars_per_line=25)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    author_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    drawtext_filter = build_drawtext_filters(lines, font_path, author, author_font_path)

    ffmpeg_cmd = [
        'ffmpeg',
        '-loop', '1',
        '-i', image_path,
        '-vf', f"scale=720:1280,{drawtext_filter}",
        '-c:v', 'libx264',
        '-t', '8',
        '-pix_fmt', 'yuv420p',
        '-y', video_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg failed: {str(e)}"}, 500

    return send_file(video_path, mimetype='video/mp4')


@app.route('/generate-video-from-clip', methods=['POST'])
def generate_video_from_clip():
    quote = request.form.get('quote')
    author = request.form.get('author', '')
    file_url = request.form.get('fileUrl')
    file_url = get_direct_download_url(file_url)

    if not quote or not file_url:
        return {"error": "Missing 'quote' or 'fileUrl'"}, 400

    input_video_path = f"/tmp/{uuid4()}.mp4"
    output_video_path = f"/tmp/{uuid4()}.mp4"

    try:
        response = requests.get(file_url)
        response.raise_for_status()
        with open(input_video_path, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        return {"error": f"Failed to download video: {str(e)}"}, 500

    lines = wrap_text_lines(quote, max_chars_per_line=30)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    author_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_size = 38
    spacing = 10

    drawtext_filters = []
    total_lines = len(lines)
    line_height = font_size + spacing
    base_y = 640
    start_y = base_y - (line_height * total_lines // 2)

    for i, line in enumerate(lines):
        y_position = start_y + i * line_height
        drawtext = (
            f"drawtext=fontfile={font_path}:"
            f"text='{line}':"
            f"fontcolor=black:fontsize={font_size}:"
            f"box=1:boxcolor=yellow@0.6:boxborderw=6:"
            f"x=(w-text_w)/2:y={y_position}"
        )
        drawtext_filters.append(drawtext)

    if author:
        author_y = start_y + total_lines * line_height + spacing * 2
        author_line = f"- {author}"
        author_drawtext = (
            f"drawtext=fontfile={author_font_path}:"
            f"text='{author_line}':"
            f"fontcolor=white:fontsize={font_size}:"
            f"box=1:boxcolor=black@0.6:boxborderw=6:"
            f"x=(w-text_w)/2:y={author_y}"
        )
        drawtext_filters.append(author_drawtext)

    full_filter = ",".join(drawtext_filters)

    ffmpeg_cmd = [
        'ffmpeg',
        '-i', input_video_path,
        '-vf', f"scale=720:1280,{full_filter}",
        '-c:v', 'libx264',
        '-t', '8',
        '-pix_fmt', 'yuv420p',
        '-y', output_video_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"FFmpeg failed: {str(e)}"}, 500

    return send_file(output_video_path, mimetype='video/mp4')



def get_direct_download_url(url):
    if "drive.google.com" in url:
        file_id = None
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]

        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
