
import anthropic
import requests
import datetime

client = anthropic.Anthropic(api_key="METTI_QUI_LA_TUA_CHIAVE")

def che_ore_sono():
    adesso = datetime.datetime.now()
    ora_italiana = adesso + datetime.timedelta(hours=2)
    return f"Sono le {ora_italiana.hour}:{ora_italiana.minute}"

def controlla_meteo(citta):
    url_coordinate = f"https://geocoding-api.open-meteo.com/v1/search?name={citta}&count=1&language=it"
    risposta_coord = requests.get(url_coordinate)
    dati_coord = risposta_coord.json()
    lat = dati_coord["results"][0]["latitude"]
    lon = dati_coord["results"][0]["longitude"]
    url_meteo = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation&timezone=Europe/Rome"
    risposta_meteo = requests.get(url_meteo)
    dati_meteo = risposta_meteo.json()
    temperatura = dati_meteo["current"]["temperature_2m"]
    pioggia = dati_meteo["current"]["precipitation"]
    return f"A {citta}: {temperatura}°C, Pioggia: {pioggia}mm"

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import asyncio
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

tools = [
    {
        "name": "che_ore_sono",
        "description": "Usa questo tool quando l utente chiede che ore sono",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "controlla_meteo",
        "description": "Usa questo tool quando l utente chiede del meteo o se deve prendere l ombrello",
        "input_schema": {
            "type": "object",
            "properties": {
                "citta": {"type": "string", "description": "Il nome della citta"}
            },
            "required": ["citta"]
        }
    }
]

conversazione = []

def agente(messaggio):
    conversazione.append({"role": "user", "content": messaggio})
    testo = ""
    for _ in range(3):
        risposta = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system="Sei l assistente personale di Cecilia che vive a Ravenna. Sei gentile e simpatico. Conosci il suo gatto che si chiama Pixel. Rispondi sempre in italiano. Quando ti chiedono del meteo USA SEMPRE il tool controlla_meteo. Non dire mai di andare su siti esterni.",
            tools=tools,
            messages=conversazione
        )
        if risposta.stop_reason == "tool_use":
            tool_block = risposta.content[0]
            if tool_block.name == "che_ore_sono":
                risultato = che_ore_sono()
            elif tool_block.name == "controlla_meteo":
                citta = tool_block.input["citta"]
                risultato = controlla_meteo(citta)
            conversazione.append({"role": "assistant", "content": risposta.content})
            conversazione.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": risultato}]})
        else:
            testo = risposta.content[0].text
            break
    conversazione.append({"role": "assistant", "content": testo})
    return testo

async def rispondi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    messaggio = update.message.text
    risposta_agente = agente(messaggio)
    await update.message.reply_text(risposta_agente)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, rispondi))
    print("Bot avviato!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
