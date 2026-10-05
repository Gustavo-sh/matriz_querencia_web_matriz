import requests
import time

NOVO_TELEGRAM_BOT_TOKEN = "8427382302:AAGLT0_8PrmhelsWPpbX1Te2rCQ0ZOBETog"
NOVO_TELEGRAM_CHAT_ID=-5275539166

def notify_telegram(msg):
    url = f"https://api.telegram.org/bot{NOVO_TELEGRAM_BOT_TOKEN}/sendMessage"

    for tentativa in range(3):
        try:
            requests.post(
                url,
                json={
                    "chat_id": NOVO_TELEGRAM_CHAT_ID,
                    "text": msg
                },
                timeout=30
            )
            return

        except requests.exceptions.RequestException as e:
            print(f"Tentativa {tentativa + 1} falhou: {e}")

            if tentativa < 2:
                time.sleep(5)

    print("Não foi possível enviar mensagem ao Telegram.")