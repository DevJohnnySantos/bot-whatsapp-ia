import os
import requests
import schedule
import time
import threading
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURAÇÕES (Ajustadas para o seu Railway) ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") # Ajustado para o nome comum
EVO_URL = os.environ.get("EVO_URL")
EVO_KEY = os.environ.get("EVO_KEY")
EVO_INSTANCE = os.environ.get("EVO_INSTANCE", "BotGemini")
ID_GRUPO = os.environ.get("ID_GRUPO") # Recomendo colocar o ID nas variáveis também
PORT = int(os.environ.get("PORT", 8080))

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_whatsapp(texto, destinatario):
    url = f"{EVO_URL}/message/sendText/{EVO_INSTANCE}"
    payload = {
        "number": destinatario, 
        "text": texto,
        "delay": 1200, # Delay de 1.2s para parecer humano
        "linkPreview": True
    }
    headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers)
        print(f"Resposta Evolution: {res.status_code}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

# --- AGENDADOR ---
def tarefa_das_6h30():
    # Aqui você deve colocar as requisições reais de clima e notícias
    prompt = "Crie um resumo matinal curto para um grupo de WhatsApp sobre tecnologia e clima."
    resposta = model.generate_content(prompt)
    enviar_whatsapp(resposta.text, ID_GRUPO)

def rodar_cron():
    schedule.every().day.at("06:30").do(tarefa_das_6h30)
    while True:
        schedule.run_pending()
        time.sleep(10) # 10 segundos é suficiente e poupa CPU

# --- WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    dados = request.json
    # A Evolution API envia dados estruturados. Ajuste conforme a versão:
    try:
        if dados.get("event") == "messages.upsert":
            message_data = dados['data']
            # Evita responder ao próprio bot para não entrar em loop
            if message_data['key']['fromMe']:
                return jsonify({"status": "ignored"}), 200

            msg_text = message_data['message'].get('conversation') or \
                       message_data['message'].get('extendedTextMessage', {}).get('text', '')
            
            remoto = message_data['key']['remoteJid']

            if "!ia" in msg_text.lower():
                pergunta = msg_text.lower().replace("!ia", "").strip()
                res = model.generate_content(pergunta)
                enviar_whatsapp(res.text, remoto)
    except Exception as e:
        print(f"Erro no processamento: {e}")
            
    return jsonify({"status": "ok"}), 200

@app.route('/')
def health_check():
    return "Bot Online", 200

# INICIA O CRON EM BACKGROUND
threading.Thread(target=rodar_cron, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
