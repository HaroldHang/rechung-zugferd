from pathlib import Path
import json
from typing import Any, Dict, Union, List
from loguru import logger
from llama_cpp import Llama
import re
from llama_cpp.llama_chat_format import Qwen25VLChatHandler
from openai import OpenAI
import os
import subprocess
import time
import requests
import signal
import sys
import socket
import threading

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "domain" / "rechnung" / "schema.json"
"""
PROMPT_TEMPLATE = (
    "Du bist ein Parser für deutsche Rechnungen.\n\n"
    "AUFGABE:\n"
    "Extrahiere Rechnungsdaten aus dem folgenden Text und gib AUSSCHLIESSLICH ein JSON-Objekt zurück,\n"
    "das exakt diesem Schema entspricht.\n\n"
    "REGELN:\n"
    "- Verwende NUR deutsche Feldnamen wie im Schema\n"
    "- Gib ausschließlich valides JSON zurück\n"
    "- Wenn ein Feld nicht erkennbar ist, lasse es weg\n"
    "- Berechne KEINE Summen oder Steuern\n"
    "- Erfinde keine Daten\n\n"
    "SCHEMA:\n"
    "<<< INSERT schema.json HERE >>>\n\n"
    "RECHNUNGSTEXT:\n"
    "<<< INSERT RAW TEXT HERE >>>\n"
)
PROMPT_TEMPLATE = (
    "Du bist ein Parser für deutsche Rechnungen.\n\n"
    "AUFGABE:\n"
    "Analysiere den untenstehenden Rechnungstext und extrahiere die relevanten Rechnungsdaten.\n"
    "Gib AUSSCHLIESSLICH ein JSON-Objekt zurück, das EXAKT dem vorgegebenen Schema entspricht.\n\n"
    "VERBINDLICHE REGELN:\n"
    "- Antworte NUR mit einem JSON-Objekt, ohne Einleitung, Erklärung oder Zusatztext\n"
    "- Verwende AUSSCHLIESSLICH die im Schema definierten deutschen Feldnamen\n"
    "- Das JSON MUSS syntaktisch valide sein\n"
    "- JEDES Feld aus dem Schema MUSS enthalten sein\n"
    "- Wenn ein Wert nicht eindeutig im Text erkennbar ist, setze den Wert auf einen leeren String \"\"\n"
    "- Berechne KEINE Beträge, Steuern oder Summen\n"
    "- Erfinde KEINE Daten\n\n"
    "SCHEMA:\n"
    "<<< INSERT schema.json HERE >>>\n\n"
    "RECHNUNGSTEXT:\n"
    "<<< INSERT RAW TEXT HERE >>>\n"
)
"""

PROMPT_TEMPLATE = (
    "Du bist ein Parser für deutsche Rechnungen.\n\n"
    "AUFGABE:\n"
    "Analysiere den folgenden Rechnungstext und extrahiere alle relevanten Rechnungsdaten.\n\n"
    "REGELN:\n"
    "- Gib ausschließlich ein einzelnes JSON-Objekt zurück, ohne jegliche Einleitung oder Erklärung.\n"
    "- Verwende exakt die deutschen Feldnamen wie im Schema.\n"
    "- Das JSON muss valide sein.\n"
    "- JEDES Feld aus dem Schema muss im JSON enthalten sein.\n"
    "- Wenn ein Feld im Text nicht erkennbar ist, setze seinen Wert auf einen leeren String \"\".\n"
    "- Berechne keine Summen, Steuern oder andere Werte.\n"
    "- Erfinde keine Daten.\n"
    "- Antworte nur mit JSON, keine Kommentare, kein Text.\n\n"
    "SCHEMA:\n"
    "<<< INSERT schema.json HERE >>>\n\n"
    "RECHNUNGSTEXT:\n"
    "<<< INSERT RAW TEXT HERE >>>\n"
)


def clean_json_string(json_str: str) -> str:
    """
    Clean a JSON string that might contain extra characters, newlines, etc.
    
    Args:
        json_str: A potentially messy JSON string
        
    Returns:
        A clean, valid JSON string
    """
    # If it's already a dict/list, convert to string
    if isinstance(json_str, (dict, list)):
        json_str = str(json_str)
    
    # Remove extra whitespace at the beginning and end
    json_str = json_str.strip()
    
    # Common fixes for malformed JSON:
    
    # 1. Remove any leading/trailing characters that aren't part of JSON
    # JSON must start with {, [, ", or a number
    if not json_str.startswith(('{', '[', '"', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', 't', 'f', 'n')):
        # Find the first valid JSON character
        for i, char in enumerate(json_str):
            if char in '{[":0123456789-tfn':
                json_str = json_str[i:]
                break
    
    # 2. Remove trailing characters after valid JSON ends
    # Find the last valid JSON character
    bracket_stack = []
    last_valid_index = -1
    
    for i, char in enumerate(json_str):
        if char in '{[':
            bracket_stack.append(char)
            last_valid_index = i
        elif char in '}]':
            if bracket_stack:
                bracket_stack.pop()
            last_valid_index = i
        elif char == '"':
            # Skip quoted strings
            # Find the closing quote
            next_quote = json_str.find('"', i + 1)
            if next_quote != -1:
                i = next_quote
                last_valid_index = i
        else:
            last_valid_index = i
    
    if last_valid_index != -1:
        json_str = json_str[:last_valid_index + 1]
    
    # 3. Fix common escaping issues
    json_str = json_str.replace('\\n', '\\\\n')  # Fix escaped newlines in strings
    json_str = json_str.replace('\\t', '\\\\t')  # Fix escaped tabs
    json_str = json_str.replace('\\"', '\"')     # Fix escaped quotes
    json_str = re.sub(r'(?<!\\)\\(?![\\/bfnrt"])', r'\\\\', json_str)  # Fix single backslashes
    
    # 4. Remove control characters (except in strings)
    # This is tricky, so we'll try to parse and catch errors
    return json_str

def safe_json_parse(json_str: str, max_attempts: int = 3) -> Union[Dict, List, str, None]:
    """
    Safely parse a potentially malformed JSON string.
    
    Args:
        json_str: A potentially messy JSON string
        max_attempts: Number of attempts to clean and parse
        
    Returns:
        Parsed JSON object, or None if all attempts fail
    """
    original_str = json_str
    
    for attempt in range(max_attempts):
        try:
            # First, try to parse as-is
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            if attempt == 0:
                # First attempt failed, try to clean it
                json_str = clean_json_string(json_str)
            elif attempt == 1:
                # Try more aggressive cleaning
                # Remove all newlines and extra spaces
                json_str = re.sub(r'\s+', ' ', json_str)
                # Try to find JSON content between { } or [ ]
                match = re.search(r'(\{[^{}]*\}|\[[^\[\]]*\])', json_str)
                if match:
                    json_str = match.group(1)
            elif attempt == 2:
                # Last resort: try to extract any valid JSON substring
                try:
                    # Find the first { and last }
                    start = json_str.find('{')
                    end = json_str.rfind('}')
                    if start != -1 and end != -1 and start < end:
                        json_str = json_str[start:end+1]
                        return json.loads(json_str)
                    
                    # Find the first [ and last ]
                    start = json_str.find('[')
                    end = json_str.rfind(']')
                    if start != -1 and end != -1 and start < end:
                        json_str = json_str[start:end+1]
                        return json.loads(json_str)
                except:
                    pass
            
            # If this is the last attempt and still failing
            if attempt == max_attempts - 1:
                print(f"Failed to parse JSON after {max_attempts} attempts")
                print(f"Original string: {original_str[:200]}...")
                print(f"Last attempt string: {json_str[:200]}...")
                return None

def extract_json_from_text(text: str) -> Union[Dict, List, None]:
    """
    Extract JSON from a text that might contain JSON mixed with other content.
    
    Args:
        text: Text that might contain JSON
        
    Returns:
        Parsed JSON object if found, None otherwise
    # Look for JSON patterns
    json_patterns = [
        r'(\{[^{}]*\{[^{}]*\}[^{}]*\})',  # Nested objects
        r'(\[[^\[\]]*\])',                # Arrays
        r'(\{[^{}]*\})',                  # Simple objects
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                return parsed
            except json.JSONDecodeError:
                continue
    
    return None
    """

    # Regular expression to match JSON objects (from first { to last })
    match = re.search(r'\{(?:.|\s)*\}', text)
    if not match:
        return {}  # No JSON found

    json_str = match.group(0)

    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError:
        # If JSON is malformed, return empty dict
        return {}

def build_prompt(raw_text: str, schema_text: str) -> str:
    return PROMPT_TEMPLATE.replace("<<< INSERT schema.json HERE >>>", schema_text).replace(
        "<<< INSERT RAW TEXT HERE >>>", raw_text
    )

def call_llm_via_openai(prompt: str, system_prompt: str, schema_text: Dict, model: str = "gpt-4o-mini") -> str:
    #base_url = "https://api.aimlapi.com/v1"
    base_url = os.getenv("AI_API_BASE_URL")
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("AI_API_KEY environment variable not set")
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        #response_format={
        #    "type": "json_object",
        #    "schema": schema_text,
        #},
        temperature=0.7,
        max_tokens=4096,
    )
    #print(response)
    return response.choices[0].message.content
def wait_for_port(host: str, port: int, timeout: int = 30):
    start = time.time()
    while time.time() - start < timeout:
        """
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # force IPv4
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            sock.close()
            return True
        except (OSError, ConnectionRefusedError):
            sock.close()
            time.sleep(0.5)
        """
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                sock = socket.socket(family, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((host, port))
                sock.close()
                return True
            except (OSError, ConnectionRefusedError):
                sock.close()
        time.sleep(0.5)
    raise RuntimeError(f"LLM server did not start on {host}:{port}")
def start_llama_server(model_path, port=7001, n_threads=6, ctx_size=4096):
    print(sys.executable)
    print(model_path)
    cmd = [
        sys.executable,
        "-m",
        "llama_cpp.server",
        "--model", str(model_path),
        "--host", "127.0.0.1",
        "--port", str(port),
        "--n_threads", str(n_threads),
        "--n_ctx", str(ctx_size),
    ]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
    )
    # Give it time to load model
    #for line in process.stdout:
    #  print(line, end='', flush=True)

    # Wait for the process to finish and get the exit code
    #process.wait()
    #time.sleep(8)
    def stream_logs(proc):
        for line in proc.stdout:
            print(line, end="", flush=True)
    threading.Thread(target=stream_logs, args=(process,), daemon=True).start()
    wait_for_port("127.0.0.1", port) 
    print(process)
    return process

def call_llama(prompt, port=7001):
    payload = {
        "model": "local",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist ein Parser für deutsche Rechnungen.\n"
                    "Antworte ausschließlich mit einem gültigen JSON-Objekt.\n"
                    "Kein Text außerhalb des JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    r = requests.post(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        json=payload,
        timeout=3600,
    )
    r.raise_for_status()
    response = r.json()
    print(response)
    return response["choices"][0]["message"]["content"]

def stop_llama_server(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def llm_extract_draft_json(raw_text_path: Path, model_path: Path, clip_model_path: Path) -> Dict[str, Any]:
    logger.info("Starte LLM für strukturierte JSON-Extraktion")
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    raw_text = Path(raw_text_path).read_text(encoding="utf-8", errors="ignore")
    prompt = build_prompt(raw_text, schema_text)
    
    if not model_path.exists():
        raise FileNotFoundError(f"LLM Modell nicht gefunden: {model_path}")

    #chat_handler = Qwen25VLChatHandler(clip_model_path=str(clip_model_path))
    #llm = Llama(model_path=str(model_path), chat_handler=chat_handler, n_ctx=4096)
    
    #llm = Llama(model_path=str(model_path), n_ctx=4096)
    process = start_llama_server(model_path)
    print("start of prompt")
    #output = llm.create_completion(prompt=prompt, temperature=0.7, max_tokens=4096)
    """
    output = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": "Du bist ein Parser für deutsche Rechnungen, der das Ergebnis in strukturiertem JSON liefert.."},
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_object",
            "schema": schema_text,
        },
        temperature=0.7,
        max_tokens=4096,
    )
    """
    #text = output["choices"][0]["text"].strip()
    #text = clean_json_string(text)
    #text = extract_json_from_text(text)
    #text = call_llm_via_openai(prompt, "Du bist ein Parser für deutsche Rechnungen, der das Ergebnis in strukturiertem JSON liefert..", json.dumps(schema_text),)
    try:
        text = call_llama(prompt)
    except Exception as e:
        raise ValueError(f"LLM lieferte kein valides JSON:\n {e}")
    finally:
        stop_llama_server(process)
    print(text)
    # Ensure it's valid JSON only
    try:
        data = extract_json_from_text(text)
        data = json.loads(text)
        #print(data)
    except Exception as e:
        # Attempt to locate JSON substring
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            possible = text[start : end + 1]
            data = json.loads(possible)
        else:
            raise ValueError(f"LLM lieferte kein valides JSON:\n {e}\n{text}")
    return data