import json
import time
import os
import webbrowser
from fastapi import FastAPI, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ollama import Client
import subprocess
from fastapi.middleware.cors import CORSMiddleware
import sys

try:
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    CONFIG = {"installed_models": ["7b"]}

MODELS = {
    "goat":"deepseek-v3.1:671b-cloud",
    "3b": "phi3:mini",
    "7b": "mistral:7b"
}


# Allow your frontend origin
origins = [
    "http://127.0.0.1:3169",
    "http://localhost:3169",
    "*",  # optional: allow all origins
]

app = FastAPI()

def ensure_ollama_running():
    """
    Ensures Ollama CLI server is running. Starts it if necessary.
    """
    client = Client()
    try:
        # Try a tiny generate to check if server responds
        # client.generate(model=CONFIG["installed_models"], prompt="Hello")
        for i in CONFIG["installed_models"]:
            client.generate(model=MODELS[i], prompt="Hello")
            print(f"Ollama's {i} model already running.")
    except Exception:
        print("Ollama not running. Starting Ollama CLI server...")
        try:
            # Start Ollama daemon in background
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Waiting 5 seconds for Ollama to start...")
            time.sleep(5)
            # Test again
            # client.generate(model="phi3:mini", prompt="Hello")
            for i in CONFIG["installed_models"]:
                client.generate(model=MODELS[i], prompt="Hello")
                print(f"Ollama's {i} model already running.")
            print("Ollama CLI server started successfully.")
        except Exception as e:
            print("Failed to start Ollama CLI server. Make sure 'ollama' is installed and in your PATH.")
            raise e

# Use before Client() in backend
ensure_ollama_running()
client = Client()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # allow POST, OPTIONS, GET, etc.
    allow_headers=["*"],
)

# Serve frontend folder as static
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend")
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# Load available models

PROMPTS = {
    # Alt Başlıklar için Prompt
    "subtitlePrompt": """
You are an expert in SEO and digital marketing since the birth of the web.

Topic: {topic}

Task: Generate exactly 6 original blog titles that are SEO-friendly, attention-grabbing, and based on questions or topics. 
Titles should match the style of the example provided and maintain a professional, technical tone suitable for industrial audiences. Allowed formats: question, guide, list, comparison.

Output requirements:
- Output the titles as a list (bullet points, dashes, or numbers are fine).
- Output only the titles, nothing else.
""",

    # İçerik Oluşturması için Prompt

    "contentPrompt":"""
You are an expert in SEO and digital marketing since the beginning of the web.

Compose a professional, product-focused technical essay about "{subtitle}" for industrial engineers, product managers, and commercial decision-makers. The essay should be factual, commercial, and informative, emphasizing the benefits, features, and applications of {subtitle} in real-world industrial or environmental contexts.

Write the essay in HTML, structuring all content in <p> tags. Naturally integrate 5–10 important technical keywords throughout the text and highlight each keyword using this format: <span class="Renk--Metin-ANTRASIT"><strong>keyword</strong></span>. Use only <p>, <span>, and <strong> tags. Mention only "{brand}" — do not reference any other brands.

Start immediately with technical content. Avoid any greetings, audience addresses, casual expressions, headings, lists, or conclusions. Ensure the essay flows naturally across paragraphs and totals approximately 300–400 words. Output **only the HTML content**, without explanations, notes, or markdown.

Example structure (not content):
<p>...</p>
<p>...</p>
<p>...</p>
    """,
    #Çeviri İçin Prompt

    "translationPrompt":"""
You are a professional translator specialized in technical and commercial content. Translate the following HTML essay from English to {lang}. 

Rules:
- Translate only the text content inside the HTML tags. Do not modify, remove, or add any tags except for adding a direction attribute.
- Add dir="rtl" to all tags if the target language is a right-to-left language (like Arabic, Hebrew), or dir="ltr" if the target language is left-to-right (like Turkish, French, German). Apply this attribute to every HTML tag (<p>, <span>, <strong>).
- Keep all keyword highlights (<span class="Renk--Metin-ANTRASIT"><strong>keyword</strong></span>) intact, translating the keyword text itself if applicable.
- Maintain the original paragraph structure and formatting.
- Do not add explanations, summaries, or extra text.
- Output only the translated HTML content.

Content to translate:
{content}
""",

    #Meta Description için prompt

    "metaDescPrompt":"""
You are an expert in SEO and digital marketing. Generate a **CTA-style meta description** summarizing the following HTML content. 

Rules:
- The meta description must be **strictly under 130 characters** for each language (count all letters, numbers, and punctuation).  
- Summarize the HTML content faithfully, focusing on the product, features, benefits, and commercial aspects.  
- Translate the meta description into the following languages **in order**, separated by |: {langs}.  
- Output all translations in a single line, in the specified order, separated by |.  
- Do not add explanations, numbering, or any extra text outside the translations.  

HTML content to summarize:
{content}
"""
}

def generate_text(prompt: str, requested_model: str) -> str:
            
    preferred_model = "deepseek-v3.1:671b-cloud"

    for model in [preferred_model, requested_model]:
        try:
            print(f"Model: {model}")
            start = time.time()
            response = client.chat(model=model, messages=[{"role": "user", "content": prompt}]).message.content
            elapsed = round(time.time() - start, 2)
            print(f"Completed in {elapsed}s\n")
            return response.strip()

        except Exception as e:
            print(f"Model {model} failed ({e}), trying next...")
    # Fallback output if both fail
    return "THIS PROCESS FAILED"

@app.post("/generate")
def generate(
    brand: str = Body(..., embed=True),
    topic: str = Body(..., embed=True),
    langs: list = Body(..., embed=True),
    ai_model: str = Body(... , embed=True)
):

    print("---- Incoming Request ----")
    print(sys.stdout.encoding)
    print(json.dumps({"brand": brand, "topic": topic, "langs": langs, "ai_model": ai_model}, indent=4))

    """Generate blog structure: subtitles + intro paragraphs."""
    if ai_model not in MODELS:
        return {"error": "Invalid model. Choose '3b' or '7b'."}

    model_name = MODELS[ai_model]
    
    print(f"\nStarting generation for topic: '{topic}'")

    # Step 1: Generate subtitles
    try:
        subtitle_prompt = PROMPTS["subtitlePrompt"].format(topic=topic)
        subtitles_response = generate_text(subtitle_prompt, model_name)
        print(f"Subtitle Text {subtitles_response}")

            # Clean and split subtitles
        titles_raw = [line.strip() for line in subtitles_response.splitlines() if line.strip()]
        subtitles =[]
        for title in titles_raw:
            subtitles.append(title.lstrip("-0123456789. "))
    except Exception as e:
        print(e)


    print(f"\nFound {len(subtitles)} subtitles.\n")
    subtitlesHTML = "<h3>Table of Contents</h3><ul>"
    for i, s in enumerate(subtitles, start=0):
        print(f"{i}. {s}")
        subtitlesHTML += f"<li>{subtitles[i]}</li>"
    subtitlesHTML += "</ul>"

    # Step 2: Generate content for each subtitle
    contents_subtitled = [subtitlesHTML]
    total = len(subtitles)

    try:
        for idx, subtitle in enumerate(subtitles, start=1):
            print(f"\n[{idx}/{total}] Generating content for subtitle: '{subtitle}'")
            content_prompt = PROMPTS["contentPrompt"].format(subtitle=subtitle, brand=brand)
            content_text = f"<h2>{subtitle}</h2>" + generate_text(content_prompt, model_name)
            contents_subtitled.append(content_text)
    except Exception as e:
        print(e)

    print(f"\nGeneration complete for topic: '{topic}'")

    # Step 3: Translate to languages
    contents = {}
    try:
        for lang in langs:
            contents[lang] = ""
            for content_w_subtitle in contents_subtitled:
                translated_subtitled = generate_text(prompt=PROMPTS["translationPrompt"].format(lang=lang, content=content_w_subtitle), requested_model=model_name)
                contents[lang] += translated_subtitled
    except Exception as e:
        print(e)

    # Step 4: Meta Des
    metaDescs = {}
    try:
        metaDescription_raw = generate_text(prompt=PROMPTS['metaDescPrompt'].format(content=contents['english'], langs=langs), requested_model=model_name)
        metaDescription = [desc.strip().strip("|") for desc in metaDescription_raw.split("|") if desc.strip()]
        for i in range(len(langs)):
            metaDescs[langs[i]] = metaDescription[i]
    except Exception as e:
        print(e)


    return {
        "subtitles": subtitles,
        "contents": contents,
        "metaDescs": metaDescs
    }


# Serve the main index.html at root
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    # Open the default browser to the frontend
    url = "http://127.0.0.1:3169"
    print(f"Opening frontend at {url}")
    webbrowser.open(url)

    # Start server
    uvicorn.run(app, host="127.0.0.1", port=3169)
