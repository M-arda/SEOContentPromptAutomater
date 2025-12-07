import json
import time
import os
import webbrowser
from fastapi import FastAPI, Body
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import BackgroundTasks
from ollama import Client
import subprocess
from fastapi.middleware.cors import CORSMiddleware
import sys
from OllamaAccountSwitchTest import get_next_account
from OllamaAccountSwitchTest import get_account_count
from uuid import uuid4

try:
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    CONFIG = {"installed_models": ["derin","gpt","qwen"]}

MODELS = {
    "derin":"deepseek-v3.1:671b-cloud",
    "gpt":"gpt-oss:120b-cloud",
    "qwen":"qwen3-vl:235b-cloud"
}


# Allow your frontend origin
origins = [
    "http://127.0.0.1:3169",
    "http://localhost:3169",
    "*",  # optional: allow all origins
]

def get_client():
    account = get_next_account() 
    api_key = account["api"]
    print(f"API Key Changed -> {account['name']} ({api_key[:15]}...)")
    return Client(
        headers={'Authorization': f'Bearer {api_key}'}
)


# def ensure_ollama_running():
#     """
#     Ensures Ollama CLI server is running. Starts it if necessary.
#     """
#     client = Client()
#     try:
#         # Try a tiny generate to check if server responds
#         client.generate(model=MODELS["derin"], prompt="Hello")
#         # for i in CONFIG["installed_models"]:
#         #     client.generate(model=MODELS[i], prompt="Hello")
#         print(f"Ollama's {MODELS['derin']} model already running.")
#     except Exception:
#         print("Ollama not running. Starting Ollama CLI server...")
#         try:
#             # Start Ollama daemon in background
#             subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#             print("Waiting 5 seconds for Ollama to start...")
#             time.sleep(5)
#             # Test again
#             client.generate(model=MODELS["derin"], prompt="Hello")
#             # for i in CONFIG["installed_models"]:
#             #     client.generate(model=MODELS[i], prompt="Hello")
#             #     print(f"Ollama's {i} model already running.")
#             print("Ollama CLI server started successfully.")
#         except Exception as e:
#             print("Failed to start Ollama CLI server. Make sure 'ollama' is installed and in your PATH.")
#             raise e

# ensure_ollama_running()
client = get_client()
app = FastAPI()

jobs = {}  # {job_id: {'status': str, 'progress': int, 'message': str, 'data': dict or None}}

def update_job(job_id, status, step, message, data=None):
    if job_id in jobs:
        jobs[job_id].update({'status': status, 'step': step, 'message': message})
        if data is not None:
            jobs[job_id]['data'] = data
            

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

SOUNDS_DIR = os.path.join(os.getcwd(), "sounds")
app.mount("/sounds", StaticFiles(directory=SOUNDS_DIR), name="sounds")

# Load available models

PROMPTS = {
    # Alt Başlıklar için Prompt
    "subtitlePrompt": """
You are a senior B2B conversion copywriter specializing in industrial and technical SaaS/products for over 20 years.
Write everything in perfect English only.

Topic: {topic}
Brand name: {brand_name}
Target audience: {brand_audience}

Task:
Generate exactly 10 professional, benefit-driven subheadings for a blog post.

Every subheading MUST:
- Be 100 percent English
- Contain {brand_name} at least once
- Explicitly reference the core subject of {topic}
- Stay under 20 words
- Focus on measurable results or solved pain points
- Maintain a serious, technical decision–maker tone

Allowed formats (use any):
1. How {brand_name} [Achieves Specific Result]
2. Why [Audience/Industry] Switch to {brand_name} in 2025
3. [Number] Ways {brand_name} Reduces [Cost/Risk/Downtime]
4. The Real Cost of [Old Method] vs {brand_name}
5. What Most Companies Get Wrong About [Topic] – And How {brand_name} Fixes It
6. [Number] Key Features That Set {brand_name} Apart
7. How {brand_name} Delivers [X] Percent Better [Metric] Than Competitors
8. The Hidden Risks of [Common Practice] and {brand_name}’s Solution
9. How {brand_name} Helps [Audience] Comply with [Regulation/Standard]
10. Why Legacy [Tool/System] Fails and {brand_name} Succeeds
11. [Number] Proven Strategies Using {brand_name} to Increase [Metric]
12. How Integrating {brand_name} Streamlines [Specific Process]

Output exactly this — nothing else:
1. First subheading
2. Second subheading
...
10. Tenth subheading
""",

    # İçerik Oluşturması için Prompt

    "contentPrompt":"""
You are a senior technical SEO copywriter who writes exclusively in perfect English for international B2B and industrial audiences.

Topic / subtitle: {subtitle}

Brand name – write EXACTLY as given below and NEVER translate it: {brand_name}


Content-specific keywords (all already in English – use only these, repeat 6–12 times total):
{content_keywords}

Target audience: {brand_audience}

LANGUAGE LOCK – THIS OVERRIDES EVERYTHING ELSE:
- The ONLY NON-ENGLISH text that is allowed is the exact brand name {brand_name} itself.
- EVERY SINGLE OTHER WORD YOU WRITE MUST BE ENGLISH.
- If any Turkish word tries to enter your output, DELETE IT IMMEDIATELY and replace with the correct English term.
- Zero exceptions, zero tolerance.

Task:
Write a 200–300 word technical essay about {subtitle}.

Strict rules:
- 200–300 words exactly
- Use {brand_name} and all brand-specific keywords heavily and naturally (never highlight them)
- Highlight 12–18 important technical terms / processes / benefits with:
  <span class="Renk--Metin-ANTRASIT"><strong>term or phrase</strong></span>
  (never the brand name)
- Start instantly with technical content
- No headings, lists, bullets, conclusions, greetings, CTAs
- ONLY allowed tags: <p> and <span class="Renk--Metin-ANTRASIT"><strong>...</strong></span>
- Professional, factual, slightly commercial tone

Output EXACTLY this and nothing else:
<p>First paragraph...</p>
<p>Second paragraph...</p>
<p>Third paragraph...</p>
...
No extra text, no word count, no notes.
    """,
    #Çeviri İçin Prompt

    "translationPrompt":"""
You are a professional translator specialized in technical and commercial content. Translate the following HTML essay from English to {lang}.

Rules:
- Translate only the visible text content inside HTML tags. Skip code, URLs, entities (&amp; etc.), dates, numbers, and proper nouns unless they need natural adaptation for the target language.
- Do not modify, remove, or add any tags or attributes except for adding a dir attribute to every relevant tag (see below).
- For direction: If {lang} is right-to-left (RTL: Arabic, Hebrew, Persian, Urdu, etc.), add dir="rtl" to every HTML tag containing text, such as <p>, <span>, <strong>. If left-to-right (LTR: most others, like French, German, Turkish, Spanish), add dir="ltr" to the same tags. Do this for all instances in the content.
- Keep all keyword highlights intact: <span class="Renk--Metin-ANTRASIT"><strong>keyword</strong></span>. Translate the keyword text only if it's not a technical term, brand, or proper noun (e.g., translate "machine learning" to the equivalent, but leave "TensorFlow" as-is).
- Maintain the original paragraph structure, formatting, and all other attributes/classes.
- Do not add explanations, summaries, or extra text of any kind.
- Output only the fully translated HTML content, nothing else.

Content to translate:
{content}
""",

    #Meta Description için prompt

    "metaDescPrompt":"""
You are an expert in SEO and digital marketing. Generate a CTA-style meta description (action-oriented summary that hooks users to click, e.g., "Discover X's features and boost your Y—start free today!") summarizing the following HTML content, tailored to {brand_keywords}, {brand_audience}, and {brand_services}.

Rules:
- Extract only the visible text from the HTML (ignore tags, attributes, scripts, and non-text elements).
- For each language, the meta description must be strictly under 130 characters (count all letters, numbers, punctuation, and spaces; verify the count yourself before finalizing).
- Summarize faithfully, emphasizing {brand_keywords} from the product, key features and benefits for {brand_audience}, and commercial hooks like {brand_services}, pricing, or trials.
- Translate into the languages in {langs} (format: comma-separated list, e.g., "es,fr,de"), generating one description per language in that exact order.
- Output all descriptions in a single line, separated by | (e.g., "Desc in es|Desc in fr|Desc in de"). No labels, numbering, or extra text.
- Do not add explanations or anything outside the single line.

HTML content to summarize:
{content}
""",
    # Meta Keywords için Prompt
    "metaKeywordPrompt":"""
    You are an expert in SEO and digital marketing. Generate a meta keywords list summarizing the {topic}, optimized for {brand_keywords}, {brand_audience}, and highlighting {brand_services}.

Rules:
- Extract and blend key terms from {topic}, weaving in {brand_keywords} naturally for search relevance.
- Focus on 5-10 high-impact keywords or phrases per language: Mix core terms, long-tails for {brand_audience} benefits, and action-oriented ones tied to {brand_services} (e.g., "AI automation, CRM consulting").
- Keep each list concise: Under 200 characters total (count commas, spaces; verify yourself).
- Generate one list per language in {langs} (comma-separated, e.g., "es,fr,de"), in that exact order.
- Format each as a comma-separated string (no quotes around terms, e.g., "kw1,kw2,kw3").
- Output all lists in a single line, with languages separated by | and keywords within each language separated by commas (e.g., "kw1,kw2,kw3|kw1,kw2|kw1,kw2,kw3"). No labels, numbering, or extra text.
- Do not add explanations or anything outside the single line.

Topic details:
{topic}
"""
}

# client = get_client()
def generate_text(prompt: str, requested_model: str) -> str:
    global client

    print("generating")
    model_priority = [
        MODELS["derin"],
        MODELS["derin"],
        MODELS["qwen"],
        MODELS["gpt"],
        MODELS["derin"],
        requested_model,
        MODELS["qwen"],
        MODELS["gpt"]
    ]

    idx = 0
    account_counter = 0
    while True:
        try:
            print(f"Generating with -> Model: {model_priority[idx]}, Account_Key : {dict(client._client._headers)['authorization']}")

            start = time.time()
            response = client.generate(model=model_priority[idx], prompt=prompt)
            elapsed = round(time.time() - start, 2)
            print(f"Completed in {elapsed}s\n")
            print(f"Success with {model_priority[idx]}")
            return response.response.strip()

        except Exception as e:
            error_str = str(e).lower()
            status_code = getattr(e, "status_code", None)

            if idx >= len(model_priority) or account_counter >= get_account_count():
                break

            if status_code in (429, 401) or "429" in error_str or "rate limit" in error_str or "unauthorized" in error_str:
                client = get_client()
                account_counter+=1
                print(f"429/401 detected -> switching to next API key (retrying {model_priority[idx]})")
                continue  # try same model_priority[idx] again with new key

            else:
                idx+=1
                print(f"{model_priority[idx]} failed ({e}) -> moving to next model")
                continue

    print(f"All accounts exhausted for {model_priority[idx]} -> trying next model\n")

    return "|   THIS PROCESS FAILED    |"

async def run_generation(job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name):

    try:
        # Subtitles
        subtitles = []
        update_job(job_id, 'generating', 1, 'Generating subtitles...')
        subtitle_prompt = PROMPTS["subtitlePrompt"].format(
            topic=topic, brand_name=brand, brand_audience=audience)
        subtitles_response = generate_text(subtitle_prompt, model_name)
        print(f"Subtitle Text {subtitles_response}")

        titles_raw = [line.strip() for line in subtitles_response.splitlines() if line.strip()]
        for title in titles_raw:
            subtitles.append(title.lstrip("*-0123456789. "))
        update_job(job_id, 'running', 1, f"Got {len(subtitles)} subtitles.")

        if not subtitles:
            update_job(job_id, 'error', 1, "No subtitles generated—aborting.")
            return

        print(f"\nFound {len(subtitles)} subtitles.\n")
        subtitlesHTML = "<h3>Table of Contents</h3><ul>"
        for i, s in enumerate(subtitles):
            print(f"{i}. {s}")
            subtitlesHTML += f"<li>{subtitles[i]}</li>"
        subtitlesHTML += "</ul>"

        # Meta Keywords
        metaKeywords = {}
        update_job(job_id, 'generating', 2, "Cranking meta keywords...")
        metaKeywords_raw = generate_text(
            PROMPTS['metaKeywordPrompt'].format(
                topic=topic, brand_keywords=brandKeywords, brand_audience=audience, 
                brand_services=services, langs=",".join(langs)
            ), 
            model_name
        )
        keyword_lists = [kw_list.strip() for kw_list in metaKeywords_raw.split('|') if kw_list.strip()]
        for i in range(len(langs)):
            kws = [kw.strip() for kw in keyword_lists[i].split(',') if kw.strip()]
            metaKeywords[langs[i]] = kws
        update_job(job_id, 'running', 2, "Meta keywords locked in.")

        # Content gen
        contents_subtitled = [subtitlesHTML]
        total = len(subtitles)
        update_job(job_id, 'generating', 3, f"Generating {total} content sections...")
        for idx, subtitle in enumerate(subtitles, start=1):
            print(f"\n[{idx}/{total}] Generating content for subtitle: '{subtitle}'")
            content_prompt = PROMPTS["contentPrompt"].format(
                subtitle=subtitle, brand_name=brand,
                content_keywords=metaKeywords.get("english", []), brand_audience=audience
            )
            content_text = f"<h2>{subtitle}</h2>" + generate_text(content_prompt, model_name)
            contents_subtitled.append(content_text)
            sub_step = f'3.{idx}'
            update_job(job_id, 'generating', float(sub_step), f"{idx}/{total} Content '{subtitle}' running.")
        update_job(job_id, 'running', 3, "All content generated.")
        print(f"\nGeneration complete for topic: '{topic}'")

        # Translations
        contents = {}
        update_job(job_id, 'generating', 4, 'Translating content...')
        if "english" not in langs:
            contents["english"] = "".join(contents_subtitled)
        for lang in langs:
            contents[lang] = ""
            for content_w_subtitle in contents_subtitled:
                translated_subtitled = generate_text(
                    PROMPTS["translationPrompt"].format(lang=lang, content=content_w_subtitle), 
                    model_name
                )
                contents[lang] += translated_subtitled
        update_job(job_id, 'running', 4, "Translations complete.")

        # Meta Descs
        metaDescs = {}
        update_job(job_id, 'generating', 5, 'Building meta descriptions...')
        metaDescription_raw = generate_text(
            PROMPTS['metaDescPrompt'].format(
                content=contents.get('english', ''), brand_keywords=brandKeywords, 
                brand_audience=audience, brand_services=services, langs=",".join(langs)
            ), 
            model_name
        )
        metaDescription = [desc.strip().strip("|") for desc in metaDescription_raw.split("|") if desc.strip()]
        for i in range(len(langs)):
            metaDescs[langs[i]] = metaDescription[i]
        update_job(job_id, 'running', 5, "Meta descs ready.")

        # Final
        final_data = {
            "subtitles": subtitles,
            "contents": contents,
            "metaDescs": metaDescs,
            "metaKeywords": metaKeywords
        }
        update_job(job_id, 'done', 5, "Full results ready.", final_data)
    except Exception as e:
        print(f"Background generation bombed: {e}")
        update_job(job_id, 'error', 0, f"Gen failed: {e}")

@app.post("/generate")
def generate(
    brand: str = Body(..., embed=True),
    topic: str = Body(..., embed=True),
    langs: list = Body(..., embed=True),
    ai_model: str = Body(..., embed=True),
    services: str = Body(..., embed=True),
    audience: str = Body(..., embed=True),
    brandKeywords: str = Body(..., embed=True),
    background_tasks: BackgroundTasks = None
):
    job_id = str(uuid4())
    jobs[job_id] = {'status': 'started', 'step': 0, 'message': 'Kicking off...', 'data': None}
    
    print("---- Incoming Request ----")
    print(json.dumps({"brand": brand, "topic": topic, "services": services, "audience": audience, "brandKeywords": brandKeywords, "langs": langs, "ai_model": ai_model}, indent=4))

    model_name = MODELS["derin"]
    print(f"\nStarting generation for topic: '{topic}'")

    background_tasks.add_task(run_generation, job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name)
    
    return JSONResponse({"job_id": job_id, "status": "started", "message": "Job queued—polling for updates."})

@app.get("/progress/{job_id}")
def get_progress(job_id: str):
    if job_id not in jobs:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    job = jobs[job_id]
    return job

@app.get("/sounds")
def list_sounds():
    try:
        files = [f for f in os.listdir(SOUNDS_DIR) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        return JSONResponse(content={"sounds": files})
    except Exception as e:
        print(f"Sounds list bombed: {e}")
        return JSONResponse(content={"sounds": []}, status_code=500)

# Serve the main index.html at root
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    url = "http://127.0.0.1:3169"
    print(f"Opening frontend at {url}")
    webbrowser.open(url)

    uvicorn.run(app, host="127.0.0.1", port=3169)