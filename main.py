import os
import requests
import schedule
import time
import threading
import re
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURAÇÕES (Puxando variáveis do Railway) ---
GEMINI_KEY = os.environ.get("GEMINI_KEY") # No Railway, adicione com esse nome
NEWS_KEY = os.environ.get("NEWS_KEY")
WEATHER_KEY = os.environ.get("WEATHER_KEY")
EVO_URL = os.environ.get("EVO_URL")
EVO_KEY = os.environ.get("EVO_KEY")
EVO_INSTANCE = os.environ.get("EVO_INSTANCE", "BotGemini")
ID_GRUPO = os.environ.get("ID_GRUPO") # Recomendo colocar o ID nas variáveis do Railway
# O Railway define a porta automaticamente, você DEVE usar a variável PORT
PORT = int(os.environ.get("PORT", 8080))

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- LOGICA DE BUSCA ---
def buscar_dados():
    clima = "Lisboa: 18°C, Sol; São Paulo: 22°C, Nublado"
    noticias = "1. Lançamento do novo Gemini; 2. Avanços na IA"
    return clima, noticias

def enviar_whatsapp(texto):
    print(f"Enviando para o WhatsApp: {texto[:50]}...")
    url = f"{EVO_URL}/message/sendText/{EVO_INSTANCE}"
    payload = {"number": ID_GRUPO, "text": texto}
    headers = {"apikey": EVO_KEY, "Content-Type": "application/json"} # Content-Type é importante
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Evolution: {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

# --- AGENDADOR ---
def tarefa_das_6h30():
    clima, noticias = buscar_dados()
    prompt = f"Crie um resumo matinal simpático com isto: {clima} e {noticias}. Responda como uma 'Tia' querida."
    resposta = model.generate_content(prompt)
    enviar_whatsapp(resposta.text)

def rodar_cron():
    schedule.every().day.at("06:30").do(tarefa_das_6h30)
    while True:
        schedule.run_pending()
        time.sleep(30) # Aumentado para 30s para economizar CPU no Railway

# --- SERVIDOR ---
@app.route('/')
def home():
    return "TIA IA Online no Railway! 🚀", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    dados = request.json
    if dados and dados.get("event") == "messages.upsert":
        # Melhoria para pegar o texto de mensagens de grupo/marcadas
        message_data = dados.get('data', {})
        msg = (message_data.get('message', {}).get('conversation') or 
               message_data.get('message', {}).get('extendedTextMessage', {}).get('text', '') or 
               "").lower()
        
        remoto = message_data.get('key', {}).get('remoteJid')

        if "@tia" in msg and remoto == ID_GRUPO:
            # Remove o gatilho @tia para o Gemini não se confundir
            pergunta = re.sub(r'@tia', '', msg, flags=re.IGNORECASE).strip()
            
            if pergunta:
                res = model.generate_content(pergunta)
                enviar_whatsapp(res.text)
            
    return jsonify({"status": "ok"}), 200

# --- INICIALIZAÇÃO CORRETA PARA O RAILWAY ---
# Ativar o agendador em uma thread separada
if __name__ != "__main__": # Isso garante que rode quando usado com Gunicorn
    threading.Thread(target=rodar_cron, daemon=True).start()

if __name__ == "__main__":
    # Importante: host 0.0.0.0 e usar a variável PORT do Railway
    app.run(host='0.0.0.0', port=PORT)
