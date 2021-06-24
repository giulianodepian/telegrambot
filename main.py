from os import environ
import telebot
from dotenv import load_dotenv
from ibm_watson import SpeechToTextV1
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

load_dotenv()
API_KEY = environ.get("API_KEY")
bot = telebot.TeleBot(API_KEY)  # Creamos el bot

IBM_KEY = environ.get("IBM_KEY")
authenticator = IAMAuthenticator(IBM_KEY)
speech_to_text = SpeechToTextV1(
    authenticator=authenticator
)

IBM_KEY2 = environ.get("IBM_KEY2")
authenticator = IAMAuthenticator(IBM_KEY2)
assistant = AssistantV2(
    version='2020-09-24',
    authenticator=authenticator
)


speech_to_text.set_service_url("https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/4580bff0-de17-4dcd-a72b-824e5bebe119")
assistant.set_service_url("https://api.us-south.assistant.watson.cloud.ibm.com/instances/89d698b5-cc02-43df-ae51-6efab4ac629c")

session_response = assistant.create_session(
    assistant_id="a5482507-c0fc-4d95-9ada-ccc695605c05").get_result()

@bot.message_handler(commands=['greet'])  # Manejador (func) del comando greet
def greet(message):
    bot.reply_to(message, "Hey! How it's going?")


@bot.message_handler(content_types=['voice'])  # Manejador de msg voz
def hello(message):
    audio_info = bot.get_file(message.voice.file_id) # Para descargar/reusar voz
    downloaded_audio = bot.download_file(audio_info.file_path) # Obtener audio file
    text = speech_to_text.recognize(
        audio=downloaded_audio,
        content_type="audio/ogg",
        model="es-ES_BroadbandModel",
        ).get_result()
    agroresponse = assistant.message(
        assistant_id="a5482507-c0fc-4d95-9ada-ccc695605c05",
        session_id=str(session_response["session_id"]),
        input={
        'message_type': 'text',
        'text': str(text["results"][0]["alternatives"][0]["transcript"])
        }
        ).get_result()
    bot.send_message(message.chat.id, str(text["results"][0]["alternatives"][0]["transcript"]))
    bot.send_message(message.chat.id, str(agroresponse["output"]["generic"][0]["text"]))


bot.polling()  # Chequea mensajes continuamente
