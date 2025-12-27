import json
import time
import os
import webbrowser
from fastapi import FastAPI, Body, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from ollama import Client
from fastapi.middleware.cors import CORSMiddleware
from OllamaAccountSwitch import get_next_account, get_account_count
from uuid import uuid4
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re
from vayes_panel_uploader import VayesUploader

try:
    with open("config.json", "r",encoding="utf-8") as f:
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

def get_client(is_first=False):
    account = get_next_account(first_time=is_first) 
    api_key = account["api"]
    print(f"API Key Changed -> {account['name']} ({api_key[:15]}...)")

    return Client(
        host='https://ollama.com',
        headers={'authorization': f'Bearer {api_key}'}
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
client = get_client(is_first=True)
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

PROMPTS_OBSOLETE = {
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

Brand Info:
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
You are an expert in SEO and digital marketing. Your task is to generate a CTA-style meta description (action-oriented summary that hooks clicks, e.g., \"Tame melasma triggers with safe lasers and routines—book your consult for even skin today!\") from the provided topic, subtitles, and keywords, tailored to {brand_audience} and {brand_services}.

Topic: {topic}
Subtitles: {subtitles}
Keywords: {content_keywords}

Strict Rules:
- Distill from {topic}, {subtitles} (treat as key angles), and {content_keywords}—blend into a cohesive hook without adding fluff or inventing details.
- Strictly under 130 characters (count every letter, number, punctuation, space precisely; verify internally, aim 100-120 for SERP bite).
- Summarize faithfully: Spotlight top {content_keywords}, hit {brand_audience} pains/benefits (e.g., quick non-surgical fixes), weave {brand_services} hooks like consults or low-downtime care. End with strong CTA verb (e.g., \"Schedule now!\").
- Engaging, persuasive, SEO-optimized: Natural {content_keywords} flow, no hype—nod evidence-based vibes for trust.
- Output the single description only. No labels, extras, counts, or text—pure output.

""",
    # Meta Keywords için Prompt
    "metaKeywordPrompt":"""
You are an expert in SEO and digital marketing. Generate a concise, high-impact meta keywords list summarizing the {topic}, optimized for {brand_keywords}, targeted at {brand_audience}, and highlighting {brand_services}.
Strict Rules:

Extract the most relevant terms directly from {topic}, then naturally blend in {brand_keywords} and {brand_services} for maximum search relevance.
Produce exactly 5–10 powerful keywords/phrases: include a mix of head terms, long-tail phrases focused on {brand_audience} pain points/benefits, and action-oriented terms tied to {brand_services}.
Keep the list under 200 characters total (count every letter, comma, and space; verify the exact count internally before finalizing—target 120-180 chars for safety).
Format as a plain comma-separated string with NO quotes, brackets, or extra punctuation.
Output just the one English list. Absolutely NO labels, numbering, explanations, line breaks, or any other text.

Topic details:
{topic}
"""
}


def google_translate(input, target_lang, is_HTML):
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
        'german': 'de',
        'italian':'it',
        'polish':'pl',
        'portuguese':'pt'
    }
    
    # Normalize to code if full name
    if target_lang.lower() in lang_map:
        target_lang = lang_map[target_lang.lower()]
    else:
        return "Requested language not found in lang_map"
    
    translator = GoogleTranslator(source='en', target=target_lang)

    if not is_HTML:
        return translator.translate(input)
    
    soup = BeautifulSoup(input, 'html.parser')
    
    # Target elements: p, h2, h3, li (ul skipped as wrapper)
    for elem in soup.find_all(['p', 'h2', 'h3', 'li']):
        has_marker = False
    # Swap span to **bold** marker
        spans = elem.find_all('span', class_='Renk--Metin-ANTRASIT')
        for span in spans:
            has_marker = True
            if span and span.strong:
                bold_text = span.strong.get_text(strip=True)
                span.replace_with(f'<B>{bold_text}</B>')
        
        # Grab full marked text (or plain)
        full_text = elem.get_text(separator=' ', strip=True)
        
        # Always translate full (context for all)
        full_translated = translator.translate(full_text)
    
        final_text = full_translated
        if has_marker:
            # Extract translated bold from between **
            def replace_bold(match):
                translated_bold = match.group(1).strip()
                return f'<span class="Renk--Metin-ANTRASIT"><strong>{translated_bold}</strong></span>'
            final_text = re.sub(r'<B>(.*?)</B>', replace_bold, full_translated)
        
        # Nuke and insert
        elem.clear()
        elem.append(final_text)
    
    return str(soup).replace('&lt;','<').replace('&gt;','>')


current_brand = ""
messages = {}
# client = get_client()
def generate_text(prompt: str, requested_model: str, brand: str, system_prompt:str, topic, jobId) -> str:
    global current_brand, messages, client
    if not current_brand == brand:
        current_brand = brand


    if f'{brand}_{topic}_{jobId}' not in messages:
        messages[f'{brand}_{topic}_{jobId}'] = []
        messages[f'{brand}_{topic}_{jobId}'].append({
            'role':'system',
            'content':f'{system_prompt}'
        })
    
    # print("generating")
    model_priority = [
        MODELS["derin"],
        MODELS["derin"],
        MODELS["derin"],
        MODELS["derin"],
        MODELS["derin"],
        MODELS["derin"],
        MODELS["derin"],
        MODELS["derin"],
        MODELS["qwen"],
        requested_model,
        MODELS["qwen"],
        MODELS["gpt"],
        MODELS["gpt"],
    ]

    idx = 0
    account_counter = 0
    messages[f'{brand}_{topic}_{jobId}'].append({'role':'user','content':f'{prompt}'})
    while True:
        try:
            print(f"Generating with -> Model: {model_priority[idx]}, Account : {dict(client._client._headers)['authorization']}")

            
            start = time.time()
            # response = client.generate(model=model_priority[idx], prompt=prompts[generation_type])
            response = client.chat(model=model_priority[idx],messages=messages[f'{brand}_{topic}_{jobId}'])
            elapsed = round(time.time() - start, 2)
            print(f"Completed in {elapsed}s\n")
            print(f"Success with {model_priority[idx]}")
            messages[f'{brand}_{topic}_{jobId}'].append({'role': 'assistant', 'content': response['message']['content']})
            return response['message']['content']

        except Exception as e:
            error_str = str(e).lower()
            status_code = getattr(e, "status_code", None)

            if idx >= len(model_priority) or account_counter >= get_account_count()*2:
                break

            if status_code in (429, 401) or "429" in error_str or "rate limit" in error_str or "unauthorized" in error_str:
                client = get_client()
                account_counter+=1
                print(f"429/401 detected -> switching to next API key (retrying {model_priority[idx]})")
                print(f"{error_str}")
                continue  # try same model_priority[idx] again with new key

            else:
                print(f"{model_priority[idx-1] if idx > 0 else f'{MODELS['derin']}'} failed...")
                idx+=1
                continue

    print(f"All accounts exhausted or None of the models are reachable\n")

    return "|   THIS PROCESS FAILED    |"

def run_generation(job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name, description, brand_prompts):
    topics = {}

    try:
        topics['english'] = topic
        for lang in langs:
            if lang == 'english':
                continue
            topics[lang] = google_translate(topic,lang,False)
    except Exception as e:
        for lang in langs:
            topics[lang] = topic
        print("Google Translator didnt work every topic is English. Manually translate and replace")
        print(e)

    try:
        # Subtitles
        subtitles = []
        update_job(job_id, 'generating', 1, 'Generating subtitles...')
        subtitle_prompt = brand_prompts["subtitle"].format(
            topic=topic, brand_name=brand, brand_audience=audience, brand_description=description)
        subtitles_response = generate_text(subtitle_prompt, model_name, brand, brand_prompts['system'], topic=topic, jobId=job_id)
        print(f"Subtitle Text {subtitles_response}")

        titles_raw = [line.strip() for line in subtitles_response.splitlines() if line.strip()]

        for raw_title in titles_raw:
            cleaned = re.sub(r'^\d+[\.\)\-\s]+', '', raw_title).strip()
            subtitles.append(cleaned.strip())
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
        subtitlesHTML = subtitlesHTML.replace('%',' percent').replace('—','-')

        # Meta Keywords
        metaKeywords = {}
        update_job(job_id, 'generating', 2, "Cranking meta keywords...")
        metaKeywords_raw = generate_text(
            PROMPTS_OBSOLETE['metaKeywordPrompt'].format(
                topic=topic, brand_keywords=brandKeywords, brand_audience=audience, brand_services=services
            ), 
            model_name, brand, brand_prompts['system'], topic=topic, jobId=job_id
        )
        
        for lang in langs:
            if lang == "english":
                metaKeywords[lang] = metaKeywords_raw
            metaKeywords[lang] = google_translate(metaKeywords_raw, target_lang=lang, is_HTML=False)
        update_job(job_id, 'running', 2, "Meta keywords locked in.")

        # Content gen
        # /../themes/default/assets/images/global/vayes_no_preview.jpg

        contents_subtitled = [subtitlesHTML]
        total = len(subtitles)
        update_job(job_id, 'generating', 3, f"Generating {total} content sections...")
        for idx, subtitle in enumerate(subtitles, start=1):
            print(f"\n[{idx}/{total}] Generating content for subtitle: '{subtitle}'")
            content_prompt = brand_prompts["content"].format(
                subtitle=subtitle, brand_name=brand,
                content_keywords=metaKeywords.get("english", ), brand_audience=audience, brand_description=description
            )
            content_text = f"<p>&nbsp;</p><h2>{subtitle}</h2>" + generate_text(content_prompt, model_name, brand, brand_prompts['system'], topic=topic, jobId=job_id)
            content_text = content_text.replace('%',' percent')
            if idx == 3:
                content_text += f'<p>&nbsp;</p><img src="/../themes/default/assets/images/global/vayes_no_preview.jpg" alt="{topic}" title="{topic}"/>'
            contents_subtitled.append(content_text)
            sub_step = f'3.{idx}'
            update_job(job_id, 'generating', float(sub_step), f"{idx}/{total} Content '{subtitle}' finished.")
        update_job(job_id, 'running', 3, "All content generated.")
        print(f"\nGeneration complete for topic: '{topic}'")

        # Translations
        contents = {}
        update_job(job_id, 'generating', 4, 'Translating content...')

        contents["english"] = "".join(contents_subtitled)
        for lang in langs:
            if lang == "english":
                continue 

            update_job(job_id, 'translating', 4, f"{lang} translating...")
            contents[lang] = ""
            for content_w_subtitle in contents_subtitled:
                try:
                    translated_subtitled = google_translate(content_w_subtitle, target_lang=lang, is_HTML=True)
                except:
                    print("Something went wrong during translation, manuel translate this part")
                    translated_subtitled = content_w_subtitle
                translated_subtitled = translated_subtitled.replace(
                    '%', f" {google_translate('percent', target_lang=lang, is_HTML=False)}"
                ).replace('—', '-')
                contents[lang] += translated_subtitled
            update_job(job_id, 'translating', 4, f"{lang} finished.")

        update_job(job_id, 'running', 4, "Translations complete.")

        # Meta Descs
        metaDescs = {}
        update_job(job_id, 'generating', 5, 'Building meta descriptions...')
        metaDescription_raw = generate_text(
            PROMPTS_OBSOLETE['metaDescPrompt'].format(
                topic=topic,
                content=contents.get('english', ''), 
                brand_audience=audience, content_keywords=metaKeywords.get("english", []),
                brand_services=services, subtitles=",".join(subtitles)
            ), 
            model_name, brand, brand_prompts['system'], topic=topic, jobId=job_id
        )
        metaDescription_raw = metaDescription_raw.replace('%',' percent').replace('—','-')
        for lang in langs:
            if lang == "english":
                metaDescs[lang] = metaDescription_raw
            metaDescs[lang] = google_translate(metaDescription_raw, target_lang=lang, is_HTML=False)
        update_job(job_id, 'running', 5, "Meta descs ready.")

        messages_log = {}
        try:
            with open('messages.json','r',encoding="utf-8") as f:
                try:
                    messages_log = json.load(f)
                except:
                    messages_log = {}
                # messages_log = json.load(f)
        except FileNotFoundError:
            with open("messages.json", "a"):
                pass
        except Exception as e:
            print(f"Something went wrong {e}")
        

        if f'{brand}_{topic}_{job_id}' not in messages_log:
            messages_log[f'{brand}_{topic}_{job_id}'] = messages[f'{brand}_{topic}_{job_id}']


        with open(f'messages.json','w',encoding="utf-8") as f:
            json.dump(messages_log,f,indent=4,ensure_ascii=False)


        # Final
        final_data = {
            "subtitles": subtitles,
            "contents": contents,
            "metaDescs": metaDescs,
            "metaKeywords": metaKeywords,
            "topics":topics,
            "langs":langs
        }
        update_job(job_id, 'done', 5, "Full results ready.", final_data)
        print(messages)

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
    prompts: dict = Body(...,embed=True),
    background_tasks: BackgroundTasks = None
):
    job_id = str(uuid4())
    jobs[job_id] = {'status': 'started', 'step': 0, 'message': 'Kicking off...', 'data': None}
    
    print("---- Incoming Request ----")
    print(json.dumps({"brand": brand, "topic": topic, "services": services, "audience": audience, "brandKeywords": brandKeywords, "langs": langs, "ai_model": ai_model}, indent=4))

    model_name = MODELS["derin"]
    print(f"\nStarting generation for topic: '{topic}'")

    background_tasks.add_task(run_generation, job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name, description, prompts)
    # return run_generation(job_id, brand, topic, langs, ai_model, services, audience, brandKeywords, model_name, description)
    return JSONResponse({"job_id": job_id, "status": "started", "message": "Job queued—polling for updates."})




@app.get("/progress/{job_id}")
def get_progress(job_id: str):
    job = jobs.get(job_id)
    if not job:
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
    

uploader_cache = {}

@app.post('/login_to_panel')
def login_to_panel(body: dict = Body(...)):
    brand = body.get('brand')
    url = body.get('url')
    username = body.get('username')
    password = body.get('password')
    if not all([brand, url, username, password]):
        raise HTTPException(422, detail="Missing required fields")
    
    uploader = VayesUploader(base_url=url)
    success = uploader.login(username, password)
    if success:
        uploader_cache[brand] = {'uploader': uploader, 'creds': {'username': username, 'password': password, 'url': url}}
        return {"status": "logged in", "brand": brand}
    return {"error": "login flopped—check creds/logs"}

@app.post("/upload")
def upload_to_panel(body: dict = Body(...)):
    brand = body.get('brand')
    post_params = body.get('postParameters')
    if not brand:
        raise HTTPException(422, detail="Missing 'brand' in body")
    
    try:
        cached = uploader_cache[brand]
        uploader = cached['uploader']
    except KeyError:
        print(f"Failed to find {brand}—retry login?")
        return {"error": "No cached uploader—hit /login_to_panel first"}

    if not uploader.logged_in:
        creds = cached['creds']
        uploader = VayesUploader(base_url=creds['url'])
        if not uploader.login(creds['username'], creds['password']):
            return {"error": "Re-login bombed"}
        cached['uploader'] = uploader 

    success = uploader.upload_article(**post_params)  # Spreads the nested dict direct
    if success:
        return {"status": "uploaded", "brand": brand}
    return {"error": "Upload failed—peek logs"}


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