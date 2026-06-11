from ollama import Client
import time

MODELS = """
cogito-2.1:671b-cloud
gpt-oss:120b-cloud
deepseek-v4-pro:cloud
deepseek-v3.1:671b-cloud
qwen3.5:397b-cloud
minimax-m3:cloud
""".strip()

api_key = "YOUR_API_KEY"

client = Client(host="https://ollama.com",headers={'authorization': f'Bearer {api_key}'})


def test_model(model_name):
    print(f"\n{'=' * 60}")
    print(f"Testing: {model_name}")
    start = time.time()
    try:
        response = client.chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: TEST_OK"
                }
            ]
        )

        print("✅ WORKS")
        print("Response:", response["message"]["content"])

    except Exception as e:
        print("❌ FAILED")
        print("Reason:", str(e))
        print("Exception type:", type(e).__name__)

    
    elapsed = round(time.time() - start, 4)
    print(f"Tamamlandı {elapsed}s")


def main():
    models = [
        model.strip()
        for model in MODELS.splitlines()
        if model.strip()
    ]

    print(f"Testing {len(models)} models...")

    for model in models:
        test_model(model)


if __name__ == "__main__":
    main()