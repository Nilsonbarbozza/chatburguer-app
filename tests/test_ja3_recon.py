import requests
from curl_cffi import requests as curl_requests

import sys, os
sys.path.insert(0, os.getcwd())
from core.executors.waterfall import CHROME_120_HEADERS

# Alvo de calibracao: API publica que ecoa a assinatura TLS/JA3 do cliente
TARGET_URL = "https://tls.peet.ws/api/all"

def test_standard_python():
    print("[L0 - PADRAO] Disparando com biblioteca nativa (requests)...")
    try:
        response = requests.get(TARGET_URL, timeout=10)
        data = response.json()
        
        tls = data.get('tls', {})
        http_info = data.get('http_version', 'unknown')
        print(f"   JA3 Hash:       {tls.get('ja3_hash', 'N/A')}")
        ja3_str = tls.get('ja3', '')
        print(f"   JA3 String:     {ja3_str[:80]}..." if ja3_str else "   JA3 String:     N/A")
        print(f"   HTTP Version:   {http_info}")
        print(f"   User-Agent:     {data.get('http', {}).get('headers', {}).get('user-agent', 'N/A')}")
        print()
    except Exception as e:
        print(f"   [Erro]: {e}\n")

def test_l12_impersonation():
    print("[L12 - CURLCFFI] Disparando com TLS Spoofing (Chrome 120)...")
    try:
        response = curl_requests.get(
            TARGET_URL, 
            impersonate="chrome120", 
            timeout=10
        )
        data = response.json()
        
        tls = data.get('tls', {})
        http_info = data.get('http_version', 'unknown')
        print(f"   JA3 Hash:       {tls.get('ja3_hash', 'N/A')}")
        ja3_str = tls.get('ja3', '')
        print(f"   JA3 String:     {ja3_str[:80]}..." if ja3_str else "   JA3 String:     N/A")
        print(f"   HTTP Version:   {http_info}")
        print(f"   User-Agent:     {data.get('http', {}).get('headers', {}).get('user-agent', 'N/A')}")
        print()
    except Exception as e:
        print(f"   [Erro]: {e}\n")

def test_l12_with_headers():
    print("[L12 - HARDENED] Disparando com TLS Spoofing + Headers Completos...")
    try:
        headers = {**CHROME_120_HEADERS, "referer": "https://www.google.com/search?q=tls.peet.ws"}
        response = curl_requests.get(
            TARGET_URL, 
            impersonate="chrome120",
            headers=headers,
            timeout=10
        )
        data = response.json()
        
        tls = data.get('tls', {})
        http_info = data.get('http_version', 'unknown')
        received_headers = data.get('http', {}).get('headers', {})
        
        print(f"   JA3 Hash:       {tls.get('ja3_hash', 'N/A')}")
        print(f"   HTTP Version:   {http_info}")
        print(f"   User-Agent:     {received_headers.get('user-agent', 'N/A')}")
        print(f"   Sec-Ch-Ua:      {received_headers.get('sec-ch-ua', 'MISSING!')}")
        print(f"   Sec-Fetch-Dest: {received_headers.get('sec-fetch-dest', 'MISSING!')}")
        print(f"   Accept-Lang:    {received_headers.get('accept-language', 'MISSING!')}")
        print()
    except Exception as e:
        print(f"   [Erro]: {e}\n")

if __name__ == "__main__":
    print("=" * 70)
    print("OPERACAO DE RECONHECIMENTO TLS/JA3")
    print("=" * 70 + "\n")
    test_standard_python()
    test_l12_impersonation()
    test_l12_with_headers()
    print("=" * 70)
    print("OPERACAO CONCLUIDA")
    print("=" * 70)
