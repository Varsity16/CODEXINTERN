import speech_recognition as sr

recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("Please say something")
    # Try changing this line in your code
    recognizer.adjust_for_ambient_noise(source, duration=2) 
    audio_data = recognizer.listen(source)
    print("Recognizing your speech...")

    try:
        text = recognizer.recognize_google(audio_data)
        print(f"You said: '{text}'")

    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")