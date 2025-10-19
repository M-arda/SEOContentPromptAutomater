import os
import json
import subprocess
import sys
import platform
import shutil

# === Local AI Installer using Ollama ===

MODELS = {
    "3b": "phi3:mini",
    "7b": "mistral:7b"
}

def is_ollama_installed():
    """Check if Ollama is installed and available in PATH."""
    return shutil.which("ollama") is not None


def install_ollama():
    """Install Ollama automatically based on OS."""
    system = platform.system().lower()
    print(f"Ollama not detected. Installing for {system}...")

    try:
        if "windows" in system:
            # Windows: use the official installer (silent)
            url = "https://ollama.com/download/OllamaSetup.exe"
            installer_path = os.path.join(os.getcwd(), "OllamaSetup.exe")
            subprocess.run(["powershell", "-Command", f"Invoke-WebRequest -Uri {url} -OutFile {installer_path}"], check=True)
            subprocess.run([installer_path, "/SILENT"], check=True)
        elif "darwin" in system:  # macOS
            subprocess.run(["brew", "install", "ollama"], check=True)
        elif "linux" in system:
            subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh", "|", "sh"], shell=True, check=True)
        else:
            print("Unsupported OS. Please install Ollama manually from https://ollama.com")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Ollama installation failed: {e}")
        sys.exit(1)

    print("Ollama installed successfully. Restart terminal if needed.")


def pull_model(model_name: str):
    """Pull model using Ollama CLI."""
    print(f"\nPulling model: {model_name} ...")
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"Model '{model_name}' pulled successfully.")
    except subprocess.CalledProcessError:
        print(f"Failed to pull model: {model_name}")
        sys.exit(1)


def ensure_models(selected):
    """Ensure each selected model is installed."""
    try:
        existing = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        for key in selected:
            model = MODELS[key]
            if model in existing.stdout:
                print(f"Model '{model}' already installed, skipping.")
            else:
                pull_model(model)
    except Exception as e:
        print(f"Error checking model status: {e}")
        for key in selected:
            pull_model(MODELS[key])


def main():
    print("=== Local AI Installer (Ollama) ===")

    # Check or install Ollama
    if not is_ollama_installed():
        install_ollama()

    print("\nWhich models do you want to install?")
    print("1) 3B (faster, smaller) → phi3:mini")
    print("2) 7B (better quality, slower) → mistral:7b")
    print("3) Both")
    
    choice = input("Enter choice (1/2/3): ").strip()

    selected = []
    if choice == "1":
        selected = ["3b"]
    elif choice == "2":
        selected = ["7b"]
    elif choice == "3":
        selected = ["3b", "7b"]
    else:
        print("Invalid choice, exiting.")
        sys.exit(0)

    ensure_models(selected)

    # Save config
    config = {"installed_models": selected}
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print("\nSetup complete! You can now run backend.py")
    print("Installed models:", ", ".join(MODELS[k] for k in selected))


if __name__ == "__main__":
    main()
