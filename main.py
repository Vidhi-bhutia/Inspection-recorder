import streamlit as st
import speech_recognition as sr
from datetime import datetime
import os
from gtts import gTTS
import tempfile
import pygame
import pymongo
from pymongo import MongoClient
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Initialize the speech recognition engine
recognizer = sr.Recognizer()

# Initialize Pygame mixer for playing audio
pygame.mixer.init()

def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        temp_file_path = tempfile.mktemp(suffix='.mp3')
        tts.save(temp_file_path)
        pygame.mixer.music.load(temp_file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        st.error(f"Error in text-to-speech: {e}")

def record_speech(prompt):
    speak(prompt)
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        st.write(f"Listening for: '{prompt}'")
        try:
            audio = recognizer.listen(source, timeout=20, phrase_time_limit=20)
            reply = recognizer.recognize_google(audio)
            st.write(f"You said: '{reply}'")
            return reply
        except sr.UnknownValueError:
            st.write(f"Sorry, I didn't catch that. Can you please repeat?")
            return "Unknown"
        except sr.RequestError:
            st.write(f"Sorry, I'm having trouble with speech recognition.")
            return "Error"
        except sr.WaitTimeoutError:
            st.write(f"Listening timed out. Please try again.")
            return "Timeout"

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB URI
db = client['truck_inspections']
collection = db['inspections']

# Streamlit app UI
st.title("Truck Inspection Data Collection")

# State variables
if 'inspection_data' not in st.session_state:
    st.session_state.inspection_data = {}

if st.button("Start Data Collection"):
    st.session_state.inspection_data = {
        "Inspection ID": str(collection.count_documents({}) + 1),  # Auto-incremented Inspection ID
        "Date & Time of Inspection": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Truck Serial Number": "",
        "Truck Model": "",
        "Inspector Name": "",
        "Inspection Employee ID": "",
        "Tires": {},
        "Battery": {},
        "Exterior": {},
        "Brakes": {},
        "Engine": {},
        "Voice of Customer": {}
    }

    # Collecting inputs for each component
    questions = {
        "Truck Serial Number": "Please provide the Truck Serial Number.",
        "Truck Model": "Please provide the Truck Model.",
        "Inspector Name": "Please provide your name.",
        "Inspection Employee ID": "Please provide your Employee ID.",
        "Location of Inspection": "Please provide the Location of Inspection.",
        "Geo Coordinates of Inspection": "Please provide the Geo Coordinates of Inspection if available.",
        "Service Meter Hours": "Please provide the Service Meter Hours.",
        "Inspector Signature": "Please provide your Signature verbally.",
        "Customer Name / Company Name": "Please provide the Customer Name or Company Name.",
        "CAT Customer ID": "Please provide the CAT Customer ID."

    }

    for key, question in questions.items():
        while True:
            response = record_speech(question)
            if response not in ["Unknown", "Error", "Timeout"]:
                st.session_state.inspection_data[key] = response
                break
            else:
                speak(f"Sorry, I couldn't get you. Can you please repeat the {key.lower()}?")

    # Collecting detailed inspection data
    detailed_questions = {
        "Tires": {
            "Tire Pressure for Left Front": "Tire Pressure for Left Front:",
            "Tire Pressure for Right Front": "Tire Pressure for Right Front:",
            "Tire Condition for Left Front": "Tire Condition for Left Front (Good, Ok, Needs Replacement):",
            "Tire Condition for Right Front": "Tire Condition for Right Front (Good, Ok, Needs Replacement):",
            "Tire Pressure for Left Rear": "Tire Pressure for Left Rear:",
            "Tire Pressure for Right Rear": "Tire Pressure for Right Rear:",
            "Tire Condition for Left Rear": "Tire Condition for Left Rear (Good, Ok, Needs Replacement):",
            "Tire Condition for Right Rear": "Tire Condition for Right Rear (Good, Ok, Needs Replacement):",
            "Overall Tire Summary": "Overall Tire Summary:",
        },
         "Battery": {
            "Battery Make": "Battery Make:",
            "Battery replacement date": "Battery replacement date:",
            "Battery Voltage": "Battery Voltage:",
            "Battery Water level": "Battery Water level (Good, Ok, Low):",
            "Condition of Battery": "Condition of Battery (Any damage) Y/N:",
            "Any Leak / Rust in battery": "Any Leak / Rust in battery (Y / N):",
            "Battery overall Summary": "Battery overall Summary:",
        },
        "Exterior": {
            "Rust, Dent or Damage to Exterior": "Rust, Dent or Damage to Exterior (Y/N):",
            "Oil leak in Suspension": "Oil leak in Suspension (Y/N):",
            "Overall Summary": "Overall Summary:",
        },
        "Brakes": {
            "Brake Fluid level": "Brake Fluid level (Good, Ok, Low):",
            "Brake Condition for Front": "Brake Condition for Front (Good, Ok, Needs Replacement):",
            "Brake Condition for Rear": "Brake Condition for Rear (Good, Ok, Needs Replacement):",
            "Emergency Brake": "Emergency Brake (Good, Ok, Low):",
            "Brake Overall Summary": "Brake Overall Summary:",
        },
        "Engine": {
            "Rust, Dents or Damage in Engine": "Rust, Dents or Damage in Engine (Y/N):",
            "Engine Oil Condition": "Engine Oil Condition (Good / Bad):",
            "Engine Oil Color": "Engine Oil Color:",
            "Brake Fluid Condition": "Brake Fluid Condition (Good / Bad):",
            "Brake Fluid Color": "Brake Fluid Color:",
            "Any oil leak in Engine": "Any oil leak in Engine (Y/N):",
            "Overall Summary": "Overall Summary:",
        },
        "Voice of Customer": {
            "Any feedback from Customer": "Any feedback from Customer:",
        }
        
    }

    for section, questions in detailed_questions.items():
        section_data = {}
        for key, question in questions.items():
            while True:
                response = record_speech(question)
                if response not in ["Unknown", "Error", "Timeout"]:
                    section_data[key] = response
                    break
                else:
                    speak(f"Sorry, I couldn't get you. Can you please repeat the {key.lower()}?")
        st.session_state.inspection_data[section] = section_data

if st.button("Save Inspection Data"):
    if st.session_state.inspection_data:
        inspection_id = st.session_state.inspection_data["Inspection ID"]

        # Check if the document with the same Inspection ID exists
        existing_record = collection.find_one({"Inspection ID": inspection_id})

        if existing_record:
            # Update the existing document
            update_fields = {}
            for key, value in st.session_state.inspection_data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        update_fields[f"{key}.{sub_key}"] = sub_value
                else:
                    update_fields[key] = value

            collection.update_one(
                {"Inspection ID": inspection_id},
                {"$set": update_fields}
            )
            st.success("Inspection record updated in MongoDB.")
        else:
            # Insert a new document
            collection.insert_one(st.session_state.inspection_data)
            st.success("New inspection record saved to MongoDB.")

        # Generate and download PDF report
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter
        y_position = height - 50

        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y_position, "Truck Inspection Report")
        y_position -= 30

        # Add inspection data
        c.setFont("Helvetica", 12)
        for key, value in st.session_state.inspection_data.items():
            if isinstance(value, dict):
                c.drawString(50, y_position, f"{key}:")
                y_position -= 20
                for sub_key, sub_value in value.items():
                    c.drawString(50, y_position, f"  {sub_key}: {sub_value}")
                    y_position -= 20
            else:
                c.drawString(50, y_position, f"{key}: {value}")
                y_position -= 20

        c.save()
        pdf_buffer.seek(0)
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name="truck_inspection_report.pdf",
            mime="application/pdf"
        )
    else:
        st.error("No inspection data to save.")
