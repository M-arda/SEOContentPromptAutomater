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
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re

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
You are an expert in SEO, digital marketing, and content optimization since the dawn of the internet, with a deep understanding of transactional strategies to drive conversions, leads, and sales.

Topic: {topic}

Brand Info:
    Brand Name: {brand_name}
    Brand Description: {brand_description}
    Target Audience: {brand_audience}

Task:  
Generate exactly 10 original, SEO-optimized, and highly transactional blog titles.  
Every title must keep the main focus on the {topic} itself (not on the brand.  
The brand ({brand_name}) and its offerings may only appear as a supporting element that adds credibility, proof, or solution (never as the primary subject).  
Allowed formats only: question, guide/how-to, listicle, or comparison.  
Each title must contain strong commercial/transactional intent (ROI, cost savings, efficiency, compliance, scalability, speed, risk reduction, etc.).

Tone: professional, technical, authoritativeideal for industrial B2B decision-makers.

Output requirements:
- Output only the 10 titles as a numbered list (1. to 10.).
- Absolutely no introductions, explanations, disclaimers, or any other text.
""",

    # İçerik Oluşturması için Prompt

    "contentPrompt":"""
You are an expert in SEO, digital marketing, and content optimization since the dawn of the internet, with a deep understanding of transactional strategies to drive conversions, leads, and sales.

Topic / Subtitle: {subtitle}

Brand Info (provide exactly as below, one per line):
Brand Name: {brand_name}
Brand Description: {brand_description}
Target Audience: {brand_audience}
Topic's Keywords: {content_keywords} 


Task:
Compose a professional, technical essay focused primarily on the {subtitle}, emphasizing its benefits, features, and real-world applications in industrial or environmental contexts. Infuse strong transactional intent.

Mention {brand_name} only as a supporting element for credibility, examples, or proven solutions (never as the main subject). Naturally integrate 5–10 important technical keywords throughout and highlight each using: <span class="Renk--Metin-ANTRASIT"><strong>keyword</strong></span>.

Write in HTML, structuring all content in <p> tags. Use ONLY <p>, <span>, and <strong> tags.

Strict rules:
- Approximately 200–300 words
- Start instantly with technical content
- No greetings, audience addresses, casual expressions, headings, lists, bullets, conclusions
- Factual, commercial, informative tone with a professional flow across paragraphs

Output EXACTLY the HTML content and nothing else:
<p>First paragraph...</p>
<p>Second paragraph...</p>
<p>Third paragraph...</p>
...
No extra text, no word count, no notes.
    """,
    #Çeviri İçin Prompt

    "translationPrompt":"""
You are a professional translator specialized in technical and commercial content. Your task is to translate the following HTML essay from English to {lang}, where {lang} is the target language name (e.g., Arabic, Hebrew, Turkish, French, German).

Strict Rules:
- Translate ONLY the text content inside HTML tags. Do NOT modify, remove, add, or rearrange any HTML tags, attributes, or structure except for the specified direction attribute.
- Automatically detect if the target language is right-to-left (RTL) like Arabic or Hebrew, and add dir="rtl" to EVERY relevant HTML tag that contains text (e.g., <p>, <span>, <strong>, <div>, <h1-6>, <li>, etc.). For left-to-right (LTR) languages like Turkish, French, or German, add dir="ltr" instead. If unsure about a language's direction, default to LTR and note it in your internal thinking (but not in output).
- Preserve all keyword highlights exactly as they are, such as <span class="Renk--Metin-ANTRASIT"><strong>keyword</strong></span>. Translate the keyword text inside if it's translatable content, but keep the surrounding tags and classes unchanged.
- Maintain the exact original paragraph structure, line breaks, and formatting. Do not merge or split elements.
- Handle special characters, entities (e.g., &amp;), and code snippets accurately without alteration.
- Do NOT add any explanations, summaries, introductions, conclusions, or extra text outside the HTML. Output MUST be pure HTML starting with the root tag (e.g., <html> or <body> if that's the structure) and nothing else—no wrappers, no markdown, no comments.
- If the content includes non-translatable elements like URLs, code, or proper names, leave them unchanged.
- Edge cases: If {lang} is not a valid language or unclear, stop and output "Invalid target language specified." But assume it's valid here.

Content to translate:
{content}
""",

    #Meta Description için prompt

    "metaDescPrompt":"""
You are an expert in SEO and digital marketing. Your task is to generate CTA-style meta descriptions (action-oriented summaries that hook users to click, e.g., "Discover X's features and boost your Y—start free today!") summarizing the provided HTML content, tailored to {brand_keywords}, {brand_audience}, and {brand_services}.

Strict Rules:
- Extract ONLY the visible text from the HTML by parsing and concatenating all text nodes (e.g., content inside <p>, <h1>, <span>, etc.), ignoring tags, attributes, scripts, styles, comments, and non-text elements like images or empty nodes. Treat the extracted text as a cohesive summary source.
- For each language, ensure the meta description is strictly under 130 characters (count every letter, number, punctuation, space, and special character precisely; verify the count internally before finalizing—aim for 100-120 chars for safety).
- Summarize faithfully: Emphasize {content_keywords} from the product, highlight key features and benefits targeted at {brand_audience}, and include commercial hooks like {brand_services}, pricing details, free trials, or urgency calls-to-action to encourage clicks.
- Make each description engaging, persuasive, and SEO-optimized with natural inclusion of {content_keywords} where relevant, ending with a strong CTA verb (e.g., "Try now!", "Sign up free!").
- Translate into the exact languages listed in {langs} (a comma-separated list, e.g., "es,fr,de" for Spanish, French, German). Generate one description per language in the precise order provided in {langs}.
- Output ALL descriptions in a SINGLE line, separated by | (e.g., "Desc in es|Desc in fr|Desc in de"). Include NO labels, numbering, explanations, introductions, conclusions, or any extra text—pure output only.
- Handle special cases: If {langs} is empty or invalid, output "No languages specified." If the extracted text is too short or irrelevant, create a generic CTA based on brand placeholders, but prioritize fidelity to content.
- Do NOT add any metadata, character counts, or comments in the output.

HTML content to summarize:
{content}
""",
    # Meta Keywords için Prompt
    "metaKeywordPrompt":"""
    You are an expert in SEO and digital marketing. Generate a concise, high-impact meta keywords list summarizing the {topic}, optimized for {brand_keywords}, targeted at {brand_audience}, and highlighting {brand_services}.

Strict Rules:
- Extract the most relevant terms directly from {topic}, then naturally blend in {brand_keywords} and {brand_services} for maximum search relevance.
- Produce exactly 5–10 powerful keywords/phrases per language: include a mix of head terms, long-tail phrases focused on {brand_audience} pain points/benefits, and action-oriented terms tied to {brand_services} (e.g., "AI workflow automation", "CRM implementation services").
- Keep each language’s list under 200 characters total (count every letter, comma, and space; verify the exact count internally before finalizing—target 120-180 chars for safety).
- Generate one list per language specified in {langs}, strictly in the order given.
- Format each list as a plain comma-separated string with NO quotes, brackets, or extra punctuation (e.g., "automatización IA,consultoría CRM,flujos de trabajo inteligentes").
- Output everything on a SINGLE line: language lists separated only by | (e.g., "kw1,kw2,kw3|kw1,kw2,kw3,kw4|kw1,kw2"). Absolutely NO labels, language codes, numbering, explanations, line breaks, or any other text.
- If {langs} is missing or empty, output "No languages specified." Otherwise assume the list is valid.

Topic details:
{topic}
"""
}


def translate_html(html_input, target_lang):
    """
    Swaps highlights to **bold** marker, translates full marked text in context, extracts translated bold,
    wraps it back in tags. Targets p/h2/h3/li, preserves structure/ul.
    """
    # Lang map: full name -> ISO code
    lang_map = {
        'turkish': 'tr',
        'english': 'en',
        'arabic': 'ar',
        'russian': 'ru',
        'french': 'fr',
        'spanish': 'es',
        'german': 'de'
    }
    
    # Normalize to code if full name
    if target_lang.lower() in lang_map:
        target_lang = lang_map[target_lang.lower()]
    
    translator = GoogleTranslator(source='en', target=target_lang)
    soup = BeautifulSoup(html_input, 'html.parser')
    
    # Target elements: p, h2, h3, li (ul skipped as wrapper)
    for elem in soup.find_all(['p', 'h2', 'h3', 'li']):
        has_marker = False
    # Swap span to **bold** marker
    span = elem.find('span', class_='Renk--Metin-ANTRASIT')
    if span and span.strong:
        bold_text = span.strong.get_text(strip=True)
        span.replace_with(f'**{bold_text}**')
        has_marker = True
    
    # Grab full marked text (or plain)
    full_text = elem.get_text(separator=' ', strip=True)
    
    # Always translate full (context for all)
    full_translated = translator.translate(full_text)
    
    final_text = full_translated
    if has_marker:
        # Extract translated bold from between **
        bold_match = re.search(r'\*\*(.*?)\*\*', full_translated)
        if bold_match:
            translated_bold = bold_match.group(1).strip()
            def replace_bold(match):
                return f' <span class="Renk--Metin-ANTRASIT"><strong>{translated_bold}</strong></span> '
            final_text = re.sub(r'\*\*(.*?)\*\*', replace_bold, full_translated)
    
    # Nuke and insert
    elem.clear()
    elem.append(final_text)
    
    return str(soup).replace('&lt;','<').replace('&gt;','>')
    

# client = get_client()
def generate_text(prompt: str, requested_model: str) -> str:
    global client

    # print("generating")
    model_priority = [
        MODELS["qwen"],
        MODELS["gpt"],
        MODELS["derin"],
        MODELS["qwen"],
        MODELS["derin"],
        MODELS["gpt"],
        MODELS["derin"],
        requested_model,
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

def run_generation(job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name, description):

    try:
        # Subtitles
        subtitles = []
        update_job(job_id, 'generating', 1, 'Generating subtitles...')
        subtitle_prompt = PROMPTS["subtitlePrompt"].format(
            topic=topic, brand_name=brand, brand_audience=audience, brand_description=description)
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
            subtitlesHTML = subtitlesHTML.replace('%',' percent')
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
                content_keywords=metaKeywords.get("english", []), brand_audience=audience, brand_description=description
            )
            content_text = f"<p>&nbsp;</p><h2>{subtitle}</h2>" + generate_text(content_prompt, model_name)
            content_text = content_text.replace('%',' percent')
            contents_subtitled.append(content_text)
            sub_step = f'3.{idx}'
            update_job(job_id, 'generating', float(sub_step), f"{idx}/{total} Content '{subtitle}' finished.")
        update_job(job_id, 'running', 3, "All content generated.")
        print(f"\nGeneration complete for topic: '{topic}'")

        # Translations
        contents = {}
        update_job(job_id, 'generating', 4, 'Translating content...')
        if "english" not in langs:
            contents["english"] = "".join(contents_subtitled)
        for lang in langs:
            if lang == "english":
                contents["english"] = ""
                for content_w_subtitle in contents_subtitled:
                    contents["english"] += content_w_subtitle
            else:
                contents[lang] = ""
                for content_w_subtitle in contents_subtitled:
                    # translated_subtitled = generate_text(
                    #     PROMPTS["translationPrompt"].format(lang=lang, content=content_w_subtitle), 
                    #     model_name
                    # )
                    translated_subtitled = translate_html(content_w_subtitle, target_lang=lang)
                    contents[lang] += translated_subtitled
        update_job(job_id, 'running', 4, "Translations complete.")

        # Meta Descs
        metaDescs = {}
        update_job(job_id, 'generating', 5, 'Building meta descriptions...')
        metaDescription_raw = generate_text(
            PROMPTS['metaDescPrompt'].format(
                content=contents.get('english', ''), brand_keywords=brandKeywords, 
                brand_audience=audience, content_keywords=metaKeywords.get("english", []), brand_services=services, langs=",".join(langs)
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

        # return {
        #     "subtitles": subtitles,
        #     "contents": contents,
        #     "metaDescs": metaDescs,
        #     "metaKeywords": metaKeywords
        # }
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
    description: str = Body(...,embed=True),
    background_tasks: BackgroundTasks = None
):
    job_id = str(uuid4())
    jobs[job_id] = {'status': 'started', 'step': 0, 'message': 'Kicking off...', 'data': None}
    
    print("---- Incoming Request ----")
    print(json.dumps({"brand": brand, "topic": topic, "services": services, "audience": audience, "brandKeywords": brandKeywords, "langs": langs, "ai_model": ai_model}, indent=4))

    model_name = MODELS["derin"]
    print(f"\nStarting generation for topic: '{topic}'")

    background_tasks.add_task(run_generation, job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name, description)
    # return run_generation(job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name, description)
    return JSONResponse({"job_id": job_id, "status": "started", "message": "Job queued—polling for updates."})

@app.get("/progress/{job_id}")
def get_progress(job_id: str):
    job = jobs.get(job_id)
    if not job:
        # 404 yerine 200 dön + status: "pending" veya "not_started"
        return {
            "status": "pending",
            "step": 0,
            "message": "Job queued — warming up...",
            "data": None
        }
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
    import webbrowser
    import threading
    import time

    url = "http://127.0.0.1:3169"
    print(f"Opening frontend at {url}")

    def open_browser():
        time.sleep(1)
        webbrowser.open(url)
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "backend:app",
        host="127.0.0.1",
        port=3169,
        workers=4,
        reload=True
    )