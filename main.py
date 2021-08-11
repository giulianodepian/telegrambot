from os import environ
import telebot
from dotenv import load_dotenv
from ibm_watson import SpeechToTextV1
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import requests

load_dotenv()
TELEBOT_KEY = environ.get("TELEBOT_KEY")
apibot = telebot.TeleBot(TELEBOT_KEY)  # Creamos el bot

Speech_KEY = environ.get("Speech_KEY")
authenticator = IAMAuthenticator(Speech_KEY)
speech_to_text = SpeechToTextV1(
    authenticator=authenticator
)

ASSISTANT_KEY = environ.get("ASSISTANT_KEY")
authenticator = IAMAuthenticator(ASSISTANT_KEY)
assistant = AssistantV2(
    version='2020-09-24',
    authenticator=authenticator
)

speech_to_text.set_service_url("https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/4580bff0-de17-4dcd-a72b-824e5bebe119")
assistant.set_service_url("https://api.us-south.assistant.watson.cloud.ibm.com/instances/89d698b5-cc02-43df-ae51-6efab4ac629c")

session_response = assistant.create_session(
    assistant_id="a5482507-c0fc-4d95-9ada-ccc695605c05").get_result()


def enviar_post(agroresponse):
    argumentos = str(agroresponse["output"]["generic"][0]["text"]).split()
    nueva_accion = {
        "comando": argumentos[0],
        "producto_kg": argumentos[1],
        "lote": argumentos[len(argumentos) - 1]
    }
    for x in range(2, len(argumentos) - 1):
        nueva_accion["producto_kg"] = " ".join([nueva_accion["producto_kg"], argumentos[x]])
    requests.post("http://127.0.0.1:5000/req", json=nueva_accion)

def AudioToText(message):
    audio_info = apibot.get_file(message.voice.file_id) # Para descargar/reusar voz
    downloaded_audio = apibot.download_file(audio_info.file_path) # Obtener audio file
    text = speech_to_text.recognize(
        audio=downloaded_audio,
        content_type="audio/ogg",
        model="es-AR_BroadbandModel",
        ).get_result()
    return text

def ConvertTextWithAssistant(text):
    agroresponse = assistant.message(
        assistant_id="a5482507-c0fc-4d95-9ada-ccc695605c05",
        session_id=str(session_response["session_id"]),
        input={
        'message_type': 'text',
        'text': str(text["results"][0]["alternatives"][0]["transcript"])
        }
        ).get_result()
    return agroresponse


class States():
    def __init__(self, bot):
        self.bot = bot

    def si(self, message):
        pass

    def no(self, message):
        pass


class AwaitingConfirmation(States):
    def __init__(self, bot):
        super().__init__(bot)

    def si(self, message):
        agroresponse = ConvertTextWithAssistant(self.bot.getText())
        enviar_post(agroresponse)
        self.bot.setState(NotAwaitingConfirmation(self.bot))
        self.bot.setStrategy(StrategyConfirmation(self.bot))

    def no(self, message):
        apibot.send_message(message.chat.id, "Envio de mensaje cancelado")
        self.bot.setState(NotAwaitingConfirmation(self.bot))
        self.bot.setStrategy(StrategyConfirmation(self.bot))


class NotAwaitingConfirmation(States):
    def __init__(self, bot):
        super().__init__(bot)

    def si(self, message):
        apibot.send_message(message.chat.id, "No se esperaba este comando")

    def no(self, message):
        apibot.send_message(message.chat.id, "No se esperaba este comando")


class Strategy:
    def __init__(self, bot):
        self.bot = bot

    def confirmation(self, message):
        pass

    def changeStrategy(self, message):
        pass


class StrategyConfirmation(Strategy):
    def __init__(self, bot):
        super().__init__(bot)

    def confirmation(self, message):
        text = AudioToText(message)
        apibot.send_message(message.chat.id, str(text["results"][0]["alternatives"][0]["transcript"]))
        apibot.send_message(message.chat.id, "Es este el mensaje que enviaste? (contesta /si o /no)")
        self.bot.setState(AwaitingConfirmation(self.bot))
        self.bot.setStrategy(StrategyDisabled(self.bot))
        self.bot.setText(text)

    def changeStrategy(self, message):
        apibot.send_message(message.chat.id, "Se cambio a MODO NO CONFIRMACION")
        return StrategyNotConfirmation(self.bot)


class StrategyNotConfirmation(Strategy):
    def __init__(self, bot):
        super().__init__(bot)

    def confirmation(self, message):
        text = AudioToText(message)
        agroresponse = ConvertTextWithAssistant(text)
        enviar_post(agroresponse)

    def changeStrategy(self, message):
        apibot.send_message(message.chat.id, "Se cambio a MODO CONFIRMACION")
        return StrategyConfirmation(self.bot)


class StrategyDisabled(Strategy):
    def __init__(self, bot):
        super().__init__(bot)

    def confirmation(self, message):
        apibot.send_message(message.chat.id, "No se esperaba un audio")

    def changeStrategy(self, message):
        apibot.send_message(message.chat.id, "No se puede cambiar de modo en este momemento")
        return StrategyDisabled(self.bot)


class Bot:
    def __init__(self):
        self.text = ""

    def useStrategy(self, message):
        self.strategy.confirmation(message)

    def setStrategy(self, strategy):
        self.strategy = strategy

    def changeStrategy(self, message):
        self.strategy = self.strategy.changeStrategy(message)

    def setState(self, state):
        self.state = state

    def si(self, message):
        self.state.si(message)

    def no(self, message):
        self.state.no(message)

    def setText(self, text):
        self.text = text

    def getText(self):
        return self.text


b = Bot()
b.setStrategy(StrategyNotConfirmation(b))
b.setState(NotAwaitingConfirmation(b))


@apibot.message_handler(commands=['cambiarmodo'])
def cambiarEstrategia(message):
    b.changeStrategy(message)


@apibot.message_handler(content_types=['voice'])  # Manejador de msg voz
def voice(message):
    b.useStrategy(message)


@apibot.message_handler(commands=['si'])
def si(message):
    b.si(message)


@apibot.message_handler(commands=['no'])
def no(message):
    b.no(message)


@apibot.message_handler(content_types=['text'])
def text(message):
    apibot.send_message(message.chat.id, "No se esperaba un texto")


apibot.polling()  # Chequea mensajes continuamente