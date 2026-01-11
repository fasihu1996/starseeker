from yapper import Yapper, PiperSpeaker, PiperVoiceGermany

deutsch = PiperSpeaker(
    voice=PiperVoiceGermany.EVA_K
)
yapper = Yapper(speaker=deutsch)

def say(text: str):
    """Basic wrapper function to output TTS messages."""
    yapper.yap(text)