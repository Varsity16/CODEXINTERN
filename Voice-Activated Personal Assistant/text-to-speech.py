import pyttsx3

engine = pyttsx3.init()
text_to_speak = "Hello, this is project x"
engine.say(text_to_speak)
engine.runAndWait()
print("Speech finished.")