# --- WEBHOOK ATUALIZADO ---
@app.route('/webhook', methods=['POST'])
def webhook():
    dados = request.json
    try:
        if dados and dados.get("event") == "messages.upsert":
            message_data = dados['data']
            
            # Ignora se a mensagem foi enviada pelo próprio bot
            if message_data.get('key', {}).get('fromMe'):
                return jsonify({"status": "ignored"}), 200

            # Captura o texto da mensagem (suporta texto simples ou estendido)
            msg_text = (message_data['message'].get('conversation') or 
                        message_data['message'].get('extendedTextMessage', {}).get('text', ''))
            
            remoto = message_data['key']['remoteJid']

            # NOVO GATILHO: @TIA (ignore case)
            if "@tia" in msg_text.lower():
                # Remove o "@tia" do texto para enviar apenas a pergunta à IA
                import re
                pergunta = re.sub(r'@tia', '', msg_text, flags=re.IGNORECASE).strip()
                
                if pergunta:
                    res = model.generate_content(pergunta)
                    enviar_whatsapp(res.text, remoto)
                else:
                    enviar_whatsapp("Oi! Como posso ajudar? (Você esqueceu de enviar a pergunta junto ao @TIA)", remoto)
                    
    except Exception as e:
        print(f"Erro no processamento do webhook: {e}")
            
    return jsonify({"status": "ok"}), 200
