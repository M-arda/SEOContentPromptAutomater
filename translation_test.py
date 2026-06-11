from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import re


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
    
    try:

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
    except:
        return input


print(google_translate("It's just for a test.","turkish",False))