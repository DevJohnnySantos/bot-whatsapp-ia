import os
import requests
import schedule
import time
import threading
import re # Importado para limpar o gatilho do texto
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
NEWS_KEY = os.environ.get("NEWS_KEY")
WEATHER_KEY = os.environ.get("WEATHER_KEY")
EVO_URL = os.environ.get("EVO_URL")
EVO_KEY = os.environ.get("EVO_KEY")
EVO_INSTANCE = os.environ.get("EVO_INSTANCE", "BotGemini")
ID_GRUPO = "120363123456789@g.us" # Substitua pelo ID real do seu grupo

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- LOGICA DE BUSCA ---
def buscar_dados():
    clima = "Lisboa: 18°C, Sol; São Paulo: 22°C, Nublado"
    noticias = "1. Lançamento do novo Gemini; 2. Avanços na IA"
    return clima, noticias

def enviar_whatsapp(texto):
    print(f"A enviar para o WhatsApp: {texto[:50]}...")
    url = f"{EVO_URL}/message/sendText/{EVO_INSTANCE}"
    payload = {"number": ID_GRUPO, "text": texto}
    headers = {"apikey": EVO_KEY}
    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Erro ao enviar: {e}")

# --- AGENDADOR ---
def tarefa_das_6h30():
    clima, noticias = buscar_dados()
    prompt = f"Crie um resumo matinal com isto: {clima} e {noticias}"
    resposta = model.generate_content(prompt)
    enviar_whatsapp(resposta.text)

def rodar_cron():
    schedule.every().day.at("06:30").do(tarefa_das_6h30)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- SERVIDOR PARA COMANDOS (@TIA) ---
@app.route('/')
def home():
    return "IA Ativa e Operante! 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    dados = request.json
    if dados and dados.get("event") == "messages.upsert":
        # Pega o texto da mensagem (considerando diferentes formatos da Evolution API)
        msg = (dados['data']['message'].get('conversation') or 
               dados['data']['message'].get('extendedTextMessage', {}).get('text', '')).lower()
        
        remoto = dados['data']['key']['remoteJid']

        # ALTERAÇÃO AQUI: Verifica se contém @tia e se veio do grupo certo
        if "@tia" in msg and remoto == ID_GRUPO:
            # Remove o "@tia" da pergunta para a IA não se confundir
            pergunta = re.sub(r'@tia', '', msg, flags=re.IGNORECASE).strip()
            
            if pergunta:
                res = model.generate_content(pergunta)
                enviar_whatsapp(res.text)
            
    return jsonify({"status": "ok"}), 200

# threading.Thread(target=rodar_cron, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
