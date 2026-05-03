import urllib.request, json
url = 'http://localhost:8000/api/v1/fetch'
headers = {
    'X-API-Key': 'sk-neuralsafety-22993f8b671041ad',
    'Content-Type': 'application/json'
}
data = json.dumps({'url': 'https://blog.dsacademy.com.br/10-bibliotecas-python-para-construir-aplicacoes-com-llms/', 'render_js': False}).encode('utf-8')

print('--- REQUEST 1 ---')
try:
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        print(f'Status: {response.status}')
        print(f'Remaining: {response.headers.get("X-RateLimit-Remaining")}')
except urllib.error.HTTPError as e:
    print(f'Status: {e.code}')
    print(e.read().decode())

print('\n--- REQUEST 2 ---')
try:
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        print(f'Status: {response.status}')
except urllib.error.HTTPError as e:
    print(f'Status: {e.code}')
    print(e.read().decode())
