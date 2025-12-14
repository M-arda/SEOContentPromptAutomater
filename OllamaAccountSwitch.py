import json
from typing import Dict, Any

def get_next_account(file_path: str = "ollamaAccounts.json",first_time:bool = False) -> Dict[str, Any]:
    # Dosyayı oku
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError("JSON dosyası boş veya hesap bulunamadı.")

    # En yüksek last_used olan anahtarı bul
    
    if first_time:
        best_key = min(data, key=lambda k:data[k]["last_used"])
    else:
        best_key = max(data, key=lambda k: data[k]["last_used"])
        # Güncellemeleri yap
        for key, account in data.items():
            if key == best_key:
                account["last_used"] = 0
            else:
                account["last_used"] += 1

    # Dosyaya geri yaz
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Seçilen hesabı döndür
    selected = data[best_key]
    selected["name"] = best_key
    return selected

def get_account_count(file_path: str = "ollamaAccounts.json") -> int:
    """Kaç tane hesap var döndürür"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return len(data)


if __name__ == "__main__":
    account = get_next_account()
    print("Şu an kullanılacak hesap:")
    print(f"  Name   : {account['name']}")
    print(f"  Mail   : {account['mail']}")
    print(f"  API    : {account['api']}")