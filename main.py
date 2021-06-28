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

text = ""
confirmation_awaiting = False


speech_to_text.set_service_url("https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/4580bff0-de17-4dcd-a72b-824e5bebe119")
assistant.set_service_url("https://api.us-south.assistant.watson.cloud.ibm.com/instances/89d698b5-cc02-43df-ae51-6efab4ac629c")

session_response = assistant.create_session(
    assistant_id="a5482507-c0fc-4d95-9ada-ccc695605c05").get_result()


class Strategy:
    def confirmation(self, message):
        pass


class StrategyConfirmation(Strategy):
    def confirmation(self, message):
        global confirmation_awaiting
        confirmation_awaiting = True
        audio_info = bot.get_file(message.voice.file_id) # Para descargar/reusar voz
        downloaded_audio = bot.download_file(audio_info.file_path) # Obtener audio file
        global text
        text = speech_to_text.recognize(
            audio=downloaded_audio,
            content_type="audio/ogg",
            model="es-AR_BroadbandModel",
            ).get_result()
        bot.send_message(message.chat.id, str(text["results"][0]["alternatives"][0]["transcript"]))
        bot.send_message(message.chat.id, "Es este el mensaje que enviaste? (contesta /si o /no)")


class StrategyNotConfirmation(Strategy):
    def confirmation(self, message):
        audio_info = bot.get_file(message.voice.file_id) # Para descargar/reusar voz
        downloaded_audio = bot.download_file(audio_info.file_path) # Obtener audio file
        text = speech_to_text.recognize(
            audio=downloaded_audio,
            content_type="audio/ogg",
            model="es-AR_BroadbandModel",
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


class Bot:
    def __init__(self, strategy):
        self.strategy = strategy

    def useStrategy(self, message):
        self.strategy.confirmation(message)

    def setStrategy(self, strategy):
        self.strategy = strategy

    def getStrategy(self):
        return self.strategy


confirm = StrategyConfirmation()
notConfirm = StrategyNotConfirmation()
b = Bot(notConfirm)


@bot.message_handler(commands=['cambiarmodo'])
def cambiarEstrategia(message):
    if isinstance(b.getStrategy(), StrategyNotConfirmation):
        bot.send_message(message.chat.id, "Cambiado a modo CONFIRMACION")
        b.setStrategy(confirm)
    else:
        bot.send_message(message.chat.id, "Cambiado a modo NO CONFIRMACION")
        b.setStrategy(notConfirm)


@bot.message_handler(content_types=['voice'])  # Manejador de msg voz
def voice(message):
    if confirmation_awaiting is False:
        b.useStrategy(message)

@bot.message_handler(func=lambda message: confirmation_awaiting == True, commands=['si'])
def si(message):
    global confirmation_awaiting
    confirmation_awaiting = False
    agroresponse = assistant.message(
        assistant_id="a5482507-c0fc-4d95-9ada-ccc695605c05",
        session_id=str(session_response["session_id"]),
        input={
        'message_type': 'text',
        'text': str(text["results"][0]["alternatives"][0]["transcript"])
        }
        ).get_result()
    bot.send_message(message.chat.id, str(agroresponse["output"]["generic"][0]["text"]))

@bot.message_handler(func=lambda message: confirmation_awaiting == True, commands=['no'])
def no(message):
    global confirmation_awaiting
    confirmation_awaiting = False
    bot.send_message(message.chat.id, "Envio de mensaje cancelado")


bot.polling()  # Chequea mensajes continuamente
