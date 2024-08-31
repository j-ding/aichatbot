import os
import string
from openai import OpenAI
import customtkinter as ctk
import time
import tkinter.font as tkFont
from tkinter import *
import speech_recognition as sr


api_key = "xxxxxxxx"

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

def generate_questions():
    global result

    # Clear the result textbox
    result.delete("0.0", "end")

    # Create a custom bold font
    bold_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
    
    # Get the job title from the dropdown
    career = careerDropdown.get()
    prompt = "You are job preperation gpt. You are designed to ask me 1 interview question based on my job title. Wait for an input or response to the question from the user, then analyze and provide feedback based on that response. be very critical and help elaborate where the user can do better. "
    prompt += "The job I am interviewing for is a " + career + " position."

    while True:
        # Call the API to get the completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )

        # Extract the question from the API response
        question = response.choices[0].message.content

        current_text = result.get("0.0", "end-1c")
        result.insert("end", "> "+question + "\n", ("bold",))
        result.see("0.0")

        user_response_frame = ctk.CTkFrame(root, width=500, height=120)
        user_response_frame.place(relx=0.5, rely=0.8, relwidth=0.7, relheight=0.15, anchor="n")

        num_lines = 5  # You can change this value to adjust the height
        user_response = ctk.CTkEntry(user_response_frame, placeholder_text="Please enter your response", height=num_lines * 5)
        user_response.pack(ipadx=100,pady=10)

        send_button_var = ctk.BooleanVar()

        def send_response():
            send_button_var.set(True)
            send_button.configure(fg_color=("green", "gray35"))

        send_button = ctk.CTkButton(user_response_frame, text="Send", command=send_response)
        send_button.pack(pady=(10), padx=(100))

        # Wait for the user to click the Send button
        user_response.wait_variable(send_button_var)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": user_response.get()}
            ]
        )

        user_response_text = user_response.get()
        print("User Response: ", user_response_text)

    

        # Display the user response to the user
        result.insert("end", "\n"+"User: "+user_response_text + "\n")
        result.see("0.0")

        feedback = response.choices[0].message.content
        print("Feedback: ", feedback +'\n')

        # Display the feedback to the user
        result.insert("end",  'Feedback: '+feedback + "\n")
        print('\n')
        result.see("0.0")

        # Clear the user response entry box
        user_response.delete(0, ctk.END)
        # Update the prompt with the user's response for the next question
        prompt = feedback + "\nNew interview question for a " + career + " position:"

        # Adjust the height of the user_response widget based on the number of lines of text
        num_lines = len(user_response_text.split('\n'))
        user_response.configure(height=num_lines * 30)


def generate_new_question():
    global result

    # Clear the result textbox
    result.delete("0.0", "end")

    # Get the job title from the dropdown
    career = careerDropdown.get()
    prompt = "You are job preperation gpt. You are designed to ask me 1 interview question based on my job title. Wait for an input or response to the question from the user, then analyze and provide feedback based on that response. be very critical and help elaborate where the user can do better. "
    prompt += "The job I am interviewing for is a " + career + " position."

    # Generate a new question
    generate_questions()
    
root = ctk.CTk()
root.geometry("850x950")
root.title("Chatbot")

ctk.set_appearance_mode("dark")

title_label = ctk.CTkLabel(root, text="Ai Interview Bot",
                            font=ctk.CTkFont(size=30, weight="bold"))
title_label.pack(padx=10, pady=(40, 20))

frame = ctk.CTkFrame(root)
frame.pack(fill="x", padx=100)

careerFrame = ctk.CTkFrame(frame)
careerFrame.pack(padx=100, pady=(20, 5), fill="both")

careerLabel = ctk.CTkLabel(careerFrame, text="Job", font=ctk.CTkFont(weight="bold"))
careerLabel.pack()
careerDropdown = ctk.CTkEntry(careerFrame, placeholder_text="Please enter a Job Title")
careerDropdown.pack(pady=10, ipadx=10)

# Create a New Question button
new_question_button = ctk.CTkButton(careerFrame, text="Reset", command=generate_new_question)
new_question_button.pack(side="bottom", pady=(10), padx=(100), fill="x")

button = ctk.CTkButton(frame, text='Generate Questions', command=generate_questions)
button.pack(padx=100, fill="x", pady=(5, 20))

result = ctk.CTkTextbox(root, font=ctk.CTkFont(size=15))
result.pack(pady=10, fill='both', padx=100,ipady=100)

root.mainloop()
