import re

__all__ = ["process_lines", "slugify_line"]

def deasciify_turkish(text: str) -> str:
    replacements = {
        "ç": "c", "Ç": "c",
        "ğ": "g", "Ğ": "g",
        "ı": "i", "I": "i",
        "İ": "i",
        "ö": "o", "Ö": "o",
        "ş": "s", "Ş": "s",
        "ü": "u", "Ü": "u"
    }
    for tr, asc in replacements.items():
        text = text.replace(tr, asc)
    return text


def slugify_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""

    line = deasciify_turkish(line)
    line = line.lower()
    line = re.sub(r"[^a-z0-9\s]", "", line)
    line = re.sub(r"\s+", "_", line)

    return line


def process_lines(multiline_text) -> dict:
    result = {
        "kapak": [],
        "icerik": []
    }

    for raw_line in multiline_text.splitlines():
        line = slugify_line(raw_line)
        if not line:
            continue

        result["kapak"].append(f"kapak_{line}")
        result["icerik"].append(f"icerik_{line}")

    return result

# Dosyadaki değil paneldeki başlıkları kullan

def main():

    basliklar = """
    İhracat Yapan Markalar İçin GEO
    Perplexity Optimizasyonu
    B2B SaaS için GEO
    Sağlık ve Estetik Klinikleri için GEO
    ChatGPT Optimizasyonu
    Claude Optimizasyonu
    E-ticaret için GEO
    Gemini Optimizasyonu
    """

    baslikListe = [line.strip() for line in basliklar.strip().splitlines() if line.strip()]

    with open("slugified.txt","a",encoding='utf-8') as f:
        f.write("\n")
        for baslik in baslikListe:
            f.write(f"\n{slugify_line(baslik)}")

if __name__ == "__main__":
    main()