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

try:
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    CONFIG = {"installed_models": ["3b"]}

MODELS = {
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
You are an expert in SEO and digital marketing since the birth of the web. I am planning content for the blog section of a website.
Our topic: “{topic}”
My goal is to generate original blog title ideas that are strong in terms of SEO, grab the reader’s attention, and are based on questions or topics.
Generate exactly 6 titles and provide them in a single line, separated by commas. Do not add any other explanation, text, or extra information.
The title formats can be: question, guide, list, comparison.
""",

    # İçerik Oluşturması için Prompt

    "contentPrompt":"""
You are an expert in SEO and digital marketing since the inception of the web. I am a writer creating blog posts for a digital agency.
For me, create a blog content with the topic "{subtitle}", minimum 300 words, in plain text, in HTML format.
Rules:

Do not include a concluding sentence or summary; end the text abruptly.
Randomly colorize keywords in this format: <span class="Renk--Metin-ANTRASIT"><strong>keyword</strong></span>
Apply this colorization only to keywords.
Do not mention any brand other than {brand}.

Provide the output only in HTML format.
    """,
    #Çeviri İçin Prompt

    "translationPrompt":"""
You are a language translator specializing in web content and HTML format.
I will provide you with an HTML content. Translate this HTML content into {lang} language and add dir="rtl" or dir="ltr" to each HTML tag, depending on the language's direction.
Rules:

Provide output only in HTML format, without additional explanations.
Do not modify existing tags, only add the dir attribute.
Translate the text into {lang} language, preserving the HTML structure.
HTML content:
{content}
""",

    #Meta Description için prompt

    "metaDescPrompt":"""
You are an expert in web content, SEO, and digital marketing.
Given HTML content:
{content}
For this HTML, create:

A meta description containing target keywords
Clear and unique for humans
Including a call-to-action (CTA)
Mobile-friendly
Length under 130 characters

Then translate this meta description into {langs} languages.
Provide the output in a single line, separated by commas, without additional explanations.
"""
}


def generate_text(prompt: str, model: str) -> str:
    """Send a single prompt to Ollama and return the text response."""
    print(f"\n[{model}] Running prompt:\n{prompt[:100]}...")
    start = time.time()
    response = client.generate(model=model, prompt=prompt)
    elapsed = round(time.time() - start, 2)
    print(f"Completed in {elapsed}s\n")
    return response["response"].strip()


@app.post("/generate")
def generate(
    brand: str = Body(..., embed=True),
    topic: str = Body(..., embed=True),
    langs: list = Body(..., embed=True),
    ai_model: str = Body("7b", embed=True)
):
    """Generate blog structure: subtitles + intro paragraphs."""
    if ai_model not in MODELS:
        return {"error": "Invalid model. Choose '3b' or '7b'."}

    model_name = MODELS[ai_model]
    print(f"\nStarting generation for topic: '{topic}' with model: {model_name}")

    # Step 1: Generate subtitles
    subtitle_prompt = PROMPTS["subtitlePrompt"].format(topic=topic)
    subtitles_raw = generate_text(subtitle_prompt, model_name)
    print(f"Subtitle Text {subtitles_raw}")

        # Clean and split subtitles
    subtitles = [s.strip().strip(",") for s in subtitles_raw.split(",") if s.strip()]

    print(f"Found {len(subtitles)} subtitles.")
    for i, s in enumerate(subtitles, start=1):
        print(f"{i}. {s}")

    # Step 2: Generate content for each subtitle
    contents_subtitled = []
    total = len(subtitles)
    for idx, subtitle in enumerate(subtitles, start=1):
        print(f"\n[{idx}/{total}] Generating content for subtitle: '{subtitle}'")
        content_prompt = PROMPTS["contentPrompt"].format(subtitle=subtitle, brand=brand)
        content_text = generate_text(content_prompt, model_name)
        contents_subtitled.append(content_text)

    print(f"\nGeneration complete for topic: '{topic}'")
    # Step 3: Translate to languages
    contents = {}
    for lang in langs:
        contents[lang] = ""
        for content_w_subtitle in contents_subtitled:
            translated_subtitled = generate_text(prompt=PROMPTS["translationPrompt"].format(lang=lang, content=content_w_subtitle), model=model_name)
            contents[lang] += translated_subtitled

    # Step 4: Meta Des
    metaDescs = {}
    metaDescription_raw = generate_text(prompt=PROMPTS['metaDescPrompt'].format(content=contents['turkce'], langs=langs), model=model_name)
    metaDescription = [desc.strip().strip(",") for desc in metaDescription_raw.split(",") if desc.strip()]
    for i in range(len(langs)):
        metaDescs[langs[i]] = metaDescription


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
