from flask import Flask, render_template, request, jsonify
import datetime
from openai import OpenAI
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize NVIDIA API client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

def get_current_year():
    return datetime.datetime.now().year

@app.context_processor
def inject_year():
    return {'current_year': get_current_year()}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        scenes = request.form.getlist("ide")
        bahasa = request.form.get("bahasa", "id")
        style = request.form.get("style", "realistic")
        duration = request.form.get("duration", "15s")
        genre = request.form.get("genre", "vlog")
        media_filename = None
        
        if 'media' in request.files and request.files['media'].filename:
            media = request.files['media']
            filename = secure_filename(media.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            media.save(file_path)
            media_filename = filename
            
        if not scenes or all(not s.strip() for s in scenes):
            return "Silakan isi minimal satu scene", 400
        result = generate_prompt(scenes, bahasa, media_filename, None, genre)
        return result
    return render_template("index.html")

def bersihkan_markdown(teks):
    teks = re.sub(r'[\*\_\`]', '', teks)
    return teks.strip()

def generate_scene_prompt(scene, bahasa, genre):
    # Template instruksi per genre
    genre_templates = {
        "vlog": {
            "id": "Buatlah deskripsi scene vlog yang menarik, santai, dan komunikatif. Fokus pada pengalaman pribadi, interaksi dengan penonton, dan suasana lokasi.",
            "en": "Write a vlog scene description that is engaging, casual, and communicative. Focus on personal experience, audience interaction, and location atmosphere."
        },
        "iklan": {
            "id": "Buatlah deskripsi scene iklan yang persuasif, singkat, dan menonjolkan keunggulan produk/jasa. Sertakan call-to-action yang kuat.",
            "en": "Write an advertisement scene description that is persuasive, concise, and highlights the product/service advantages. Include a strong call-to-action."
        },
        "edukasi": {
            "id": "Buatlah deskripsi scene edukasi yang informatif, mudah dipahami, dan menarik. Fokus pada penjelasan konsep dan contoh nyata.",
            "en": "Write an educational scene description that is informative, easy to understand, and engaging. Focus on explaining concepts and real-life examples."
        },
        "sinetron": {
            "id": "Buatlah deskripsi scene sinetron yang dramatis, penuh emosi, dan konflik antar karakter. Gunakan gaya bahasa naratif dan dialog yang kuat.",
            "en": "Write a soap opera scene description that is dramatic, emotional, and full of character conflict. Use narrative style and strong dialogues."
        },
        "film_pendek": {
            "id": "Buatlah deskripsi scene film pendek yang sinematik, artistik, dan mendalam. Fokus pada visual, suasana, dan pesan moral.",
            "en": "Write a short film scene description that is cinematic, artistic, and deep. Focus on visuals, atmosphere, and moral message."
        },
    }
    instruksi_genre = genre_templates.get(genre, genre_templates['vlog'])[bahasa]

    if bahasa == "id":
        system_prompt = f"""
{instruksi_genre}\nSkenario: {scene}\nTuliskan seluruh deskripsi dalam Bahasa Indonesia, mencakup suasana, ekspresi karakter, latar, pencahayaan, gaya berpakaian, dan emosi yang ingin disampaikan. Sertakan juga narasi singkat yang cocok untuk video berdurasi 10-15 detik.
"""
        narasi = "Gunakan narasi Bahasa Indonesia dengan nada natural, percaya diri, dan persuasif."
        audio = "Efek suara ambient sesuai lokasi. Suara karakter sinkron dan natural. Musik latar opsional dengan mood mendukung."
        ai_mode = "ID"
    else:
        system_prompt = f"""
{instruksi_genre}\nScene: {scene}\nWrite the entire description in English, including atmosphere, character expressions, background, lighting, clothing style, and emotions. Include a short narration suitable for a 10-15 second video.
"""
        narasi = "Use English narration with a natural, confident, and persuasive tone."
        audio = "Ambient sound effects according to the location. Character voice is synchronized and natural. Optional background music with a supportive mood."
        ai_mode = "EN"

    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=1024,
            frequency_penalty=0,
            presence_penalty=0
        )
        enhanced_description = completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling NVIDIA API: {str(e)}")
        if bahasa == "id":
            enhanced_description = f"Seorang karakter dalam suasana realistis melakukan {scene.lower()}. Video berdurasi 10–15 detik, bergaya sinematik, dengan ekspresi alami, gerakan tubuh realistis, dan suasana sekitar sesuai konteks."
        else:
            enhanced_description = f"A character in a realistic setting performs {scene.lower()}. The video lasts 10–15 seconds, cinematic style, with natural expressions, realistic body movements, and context-appropriate surroundings."

    enhanced_description = bersihkan_markdown(enhanced_description)

    return f"Deskripsi Scene:\n{enhanced_description}\n\nNarasi:\n{narasi}\n\nAudio:\n{audio}\n"

def generate_prompt(scenes, bahasa, media_filename=None, detected_objects=None, genre='vlog'):
    now = datetime.datetime.now().strftime("%d %B %Y")
    ai_mode = "ID" if bahasa == "id" else "EN"

    if isinstance(scenes, str):
        scenes = [scenes]

    scene_prompts = []
    for idx, scene in enumerate(scenes, 1):
        scene_title = f"SCENE {idx}: {scene.strip().split()[0].capitalize() if scene.strip() else idx}"
        scene_prompt = generate_scene_prompt(scene, bahasa, genre)
        scene_prompts.append(f"{scene_title}\n{scene_prompt}")

    prompt = f"""
Prompt VEO 3 — Dihasilkan pada {now}\n\n"""
    if media_filename:
        prompt += f"Inspirasi visual: {media_filename}\n\n"
    prompt += "\n".join(scene_prompts)
    prompt += f"\nTeknologi AI yang Digunakan:\n- Realistic face tracking\n- Voice-to-face sync\n- Motion AI integration\n- Multilingual narrative synthesis (mode: {ai_mode})\n"
    return prompt

if __name__ == "__main__":
    app.run(debug=True)