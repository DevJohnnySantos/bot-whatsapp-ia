import os
import requests
import schedule
import time
import threading
import re
from datetime import datetime
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURAÇÕES (Puxando variáveis do Railway) ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
NEWS_KEY = os.environ.get("NEWS_KEY")
WEATHER_KEY = os.environ.get("WEATHER_KEY")
EVO_URL = os.environ.get("EVO_URL")
EVO_KEY = os.environ.get("EVO_KEY")
EVO_INSTANCE = os.environ.get("EVO_INSTANCE", "BotGemini")
ID_GRUPO = os.environ.get("ID_GRUPO")
PORT = int(os.environ.get("PORT", 8080))

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- LISTA DE CIDADES ---
CIDADES = [
    "São Paulo, BR", 
    "Campo Grande, BR", 
    "Rio de Janeiro, BR",
    "Niterói, BR", 
    "Macerata, IT", 
    "João Pessoa, BR", 
    "Lucélia, BR", 
    "Vitória, BR", 
    "Eunápolis, BR"
]

# --- LOGICA DE BUSCA (Clima e Notícias Reais) ---
def buscar_dados():
    # 1. Busca Clima (OpenWeatherMap)
    clima_lista = []
    if WEATHER_KEY:
        for cidade in CIDADES:
            try:
                url_weather = f"http://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={WEATHER_KEY}&units=metric&lang=pt_br"
                r = requests.get(url_weather).json()
                if r.get("cod") == 200:
                    temp = r['main']['temp']
                    desc = r['weather'][0]['description']
                    clima_lista.append(f"{cidade}: {temp:.1f}°C, {desc.capitalize()}")
                else:
                    clima_lista.append(f"{cidade}: Não encontrado")
            except Exception as e:
                print(f"Erro ao buscar clima de {cidade}: {e}")
                clima_lista.append(f"{cidade}: Erro na busca")
    else:
        clima_lista.append("Chave de clima (WEATHER_KEY) não configurada.")
        
    clima_texto = " | ".join(clima_lista)

    # 2. Busca Notícias (NewsAPI)
    noticias_texto = "Nenhuma notícia bombástica no momento."
    if NEWS_KEY:
        try:
            url_news = f"https://newsapi.org/v2/top-headlines?country=br&apiKey={NEWS_KEY}"
            r = requests.get(url_news).json()
            if r.get("status") == "ok":
                artigos = r.get("articles", [])[:3] # Pega as 3 principais
                manchetes = [art["title"] for art in artigos if art.get("title")]
                noticias_texto = "; ".join(manchetes)
        except Exception as e:
            print(f"Erro ao buscar notícias: {e}")

    return clima_texto, noticias_texto

def enviar_whatsapp(texto):
    print(f"Enviando para o WhatsApp: {texto[:50]}...")
    url = f"{EVO_URL}/message/sendText/{EVO_INSTANCE}"
    payload = {"number": ID_GRUPO, "text": texto}
    headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Evolution: {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

# --- AGENDADOR ---
def tarefa_das_6h30():
    clima, noticias = buscar_dados()
    
    # Cálculo preciso do dia do ano
    hoje = datetime.now()
    dia_atual = hoje.timetuple().tm_yday
    # Verifica se o ano é bissexto para definir 365 ou 366
    bissexto = hoje.year % 4 == 0 and (hoje.year % 100 != 0 or hoje.year % 400 == 0)
    total_dias = 366 if bissexto else 365
    dia_do_ano = f"{dia_atual}/{total_dias}"

    # Prompt instruindo o Gemini
    prompt = (
        f"Hoje é dia {dia_do_ano}. Escreva um resumo matinal simpático para o WhatsApp. "
        f"Use os seguintes dados de Clima: ({clima}) e as seguintes Notícias: ({noticias}). "
        f"REGRAS DE FORMATAÇÃO RIGOROSAS: "
        f"1. Aja com a personalidade de uma 'Tia' muito querida, cuidadosa e carinhosa. "
        f"2. Inicie a mensagem com o dia do ano bem visível no topo. "
        f"3. Liste o clima de CADA cidade fornecida em tópicos curtos (um embaixo do outro) e use emojis de clima. "
        f"4. Resuma as notícias também em tópicos e coloque cada manchete em negrito e maiúscula. "
        f"5. Encerre com uma frase carinhosa, uma bênção ou um conselho típico de tia (ex: lembrando de levar casaco/guarda-chuva dependendo do tempo)."
    )
    
    try:
        resposta = model.generate_content(prompt)
        enviar_whatsapp(resposta.text)
    except Exception as e:
        print(f"Erro ao gerar conteúdo no Gemini: {e}")

def rodar_cron():
    schedule.every().day.at("06:30").do(tarefa_das_6h30)
    while True:
        schedule.run_pending()
        time.sleep(30) 

# --- SERVIDOR WEBHOOK ---
@app.route('/')
def home():
    return "TIA IA Online no Railway! 🚀", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    dados = request.json
    if dados and dados.get("event") == "messages.upsert":
        message_data = dados.get('data', {})
        msg = (message_data.get('message', {}).get('conversation') or 
               message_data.get('message', {}).get('extendedTextMessage', {}).get('text', '') or 
               "").lower()
        
        remoto = message_data.get('key', {}).get('remoteJid')

        if "@tia" in msg and remoto == ID_GRUPO:
            pergunta = re.sub(r'@tia', '', msg, flags=re.IGNORECASE).strip()
            
            if pergunta:
                try:
                    res = model.generate_content(pergunta)
                    enviar_whatsapp(res.text)
                except Exception as e:
                    print(f"Erro ao responder marcação: {e}")
            
    return jsonify({"status": "ok"}), 200

# --- INICIALIZAÇÃO ---
if __name__ != "__main__": 
    threading.Thread(target=rodar_cron, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=rodar_cron, daemon=True).start() # Garante que rode também se iniciado direto pelo python
    app.run(host='0.0.0.0', port=PORT)
