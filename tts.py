from yapper import Yapper
yapper = Yapper()

def say(text: str):
    """Basic wrapper function to output TTS messages."""
    yapper.yap(text)