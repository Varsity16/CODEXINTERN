import speech_recognition as sr
import pyttsx3
import datetime
import requests
import sys
import subprocess
import json
import os
from dotenv import load_dotenv
import parsedatetime as pdt 
import time 

load_dotenv()
engine = pyttsx3.init()

rate = engine.getProperty('rate')
engine.setProperty('rate', 140)     
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id) # 0 means male and female is 1



WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def speak(text):
    
    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()

def listen_for_command():
   
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source)

    try:
        print("Recognizing...")
        command = recognizer.recognize_google(audio, language='en-in')
        print(f"User said: {command}\n")
        return command.lower()
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that. Could you please repeat?")
        return None
    except sr.RequestError:
        speak("Sorry, my speech service is down. Please check your internet connection.")
        return None
    except Exception as e:
        print(e)
        speak("An unexpected error occurred. Please try again.")
        return None


def tell_time():
   
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The current time is {current_time}")

def get_weather(city="Mysuru"):
    
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}appid={WEATHER_API_KEY}&q={city}&units=metric"
    
    try:
        response = requests.get(complete_url)
        data = response.json()
        
        if data["cod"] != "404":
            main = data["main"]
            weather_desc = data["weather"][0]["description"]
            temp = main["temp"]
            humidity = main["humidity"]
            
            weather_report = (f"The weather in {city} is currently {weather_desc}, "
                              f"with a temperature of {temp} degrees Celsius "
                              f"and humidity at {humidity} percent.")
            speak(weather_report)
        else:
            speak(f"Sorry, I couldn't find the city {city}. Please try another one.")
    except Exception as e:
        speak("Sorry, I couldn't fetch the weather data. Please check your API key and internet connection.")

def get_news():
 
   if not NEWS_API_KEY:
    print("\nERROR: Could not load NEWS_API_KEY from .env file. Please check the file.")
   else:

    base_url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    
    try:
        print(f"Attempting to connect to: {base_url}")
        response = requests.get(base_url)
        print(f"Status Code: {response.status_code}")


        if response.status_code == 200:
            data = response.json()
            

            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                
                if articles:
                    print("\n--- Top Headlines ---")

                    for i, article in enumerate(articles):
                        print(f"{i + 1}. {article.get('title')}")
                    print("---------------------\n")
                else:
                    print("\nAPI request was successful, but no articles were found for this query.")
            
            else:

                print(f"\nAPI returned an error: {data.get('message')}")
        
        else:

            print(f"\nHTTP Error: Failed to retrieve data. Status code: {response.status_code}")
            print(f"Response: {response.text}")


    except requests.exceptions.RequestException as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        print("This is likely a network problem. Check your internet connection or firewall.")
        
def open_application(app_name):
  
    speak(f"Opening {app_name}...")
    platform = sys.platform
    

    if platform == "win32": # Windows
        if app_name == "notepad":
            subprocess.Popen(["notepad.exe"])
        elif app_name == "document":
            subprocess.Popen(["start", "winword"], shell=True)
        elif app_name == "excel":
            subprocess.Popen(["start", "excel"], shell=True)
        else:
            speak(f"Sorry, I don't know how to open {app_name} on Windows.")
            
    elif platform == "darwin": # macOS
        if app_name == "notepad":
            subprocess.Popen(["open", "-a", "TextEdit"])
        elif app_name == "document":
            subprocess.Popen(["open", "-a", "Microsoft Word"]) # or "Pages"
        elif app_name == "excel":
            subprocess.Popen(["open", "-a", "Microsoft Excel"]) # or "Numbers"
        else:
            speak(f"Sorry, I don't know how to open {app_name} on macOS.")

    elif platform.startswith("linux"): # Linux
        if app_name == "notepad":
            subprocess.Popen(["gedit"]) # or "kate", "mousepad" etc.
        elif app_name == "document":
            subprocess.Popen(["libreoffice", "--writer"])
        elif app_name == "excel":
            subprocess.Popen(["libreoffice", "--calc"])
        else:
            speak(f"Sorry, I don't know how to open {app_name} on Linux.")
            
    else:
        speak(f"Unsupported operating system: {platform}")




def run_assistant():

    speak("Hello! I am your voice assistant. How can I help you today?")

    while True:
        command = listen_for_command()
        
        if command is None:
            continue

      
        if 'time' in command:
            tell_time()
            
        elif 'weather' in command:
      
            try:
                city = command.split("in")[-1].strip()
                if city:
                    get_weather(city)
                else:
                    get_weather() 
            except Exception:
                get_weather()

        elif 'news' in command or 'headlines' in command:
          get_news()

        elif 'open notepad' in command:
            open_application("notepad")
            
        elif 'open document' in command or 'create a document' in command:
            open_application("document")

        elif 'open excel' in command or 'open spreadsheet' in command:
            open_application("excel")

        elif 'stop' in command or 'exit' in command or 'quit' in command:
            speak("Goodbye! Have a great day.")
            break
        
 
        elif 'set speed to' in command  :           
            try:
                speed = command.split("to")[-1].strip()
                set_speech_rate(speed)
            except Exception as e:
                speak("Please specify a number to set the speed.")

        elif 'remind' in command: 
            if 'remind me to' in command: 
                reminder_text = command.split('remind me to', 1)[1].strip()
                if reminder_text:
                    set_reminder(reminder_text)
                else:
                    speak("Certainly. What should I remind you about?")
                    reminder_command = listen_for_command()
                    if reminder_command:
                        set_reminder(reminder_command)
            else:
                speak("Certainly. What should I remind you about?")
                reminder_command = listen_for_command()
                if reminder_command:
                    set_reminder(reminder_command)
                else:
                    speak("I didn't hear a response. Cancelling reminder.")

        else:
            speak("Sorry, I don't know how to do that yet.")

def set_speech_rate(rate_value):
   
    try:
        rate_value = int(rate_value)
        engine.setProperty('rate', rate_value)
        speak(f"My speech rate has been set to {rate_value}.")
    except ValueError:
        speak("Sorry, please specify a valid number for the speed.")

def set_reminder(reminder_text):
    speak(f"Okay, you want me to remind you to '{reminder_text}'. When should I remind you?")


    time_command = listen_for_command()
    if time_command is None:
        speak("I didn't hear a time. Cancelling reminder.")
        return
        
    cal = pdt.Calendar()
    now = datetime.datetime.now()
    
    time_struct, parse_status = cal.parse(time_command, now)
    
    if parse_status != 0:
    
        reminder_time = datetime.datetime(*time_struct[:6])
        
       
        formatted_time = reminder_time.strftime("%A, %B %d at %I:%M %p")
        speak(f"Okay, reminder set to '{reminder_text}' for {formatted_time}.")
        
    else:
        speak("Sorry, I couldn't understand the time. Please try again.")

if __name__ == "__main__":
    run_assistant()