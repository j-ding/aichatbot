import os
import string
from openai import OpenAI
import customtkinter as ctk
import time
import tkinter.font as tkFont
from tkinter import *
import speech_recognition as sr
import app_settings
import json
import traceback
import threading

# Initialize global variables
client = None
result = None
careerDropdown = None
api_type_var = None
api_type_status_label = None
openai_frame = None 
mini4o_frame = None
api_key_entry = None
api_status_label = None
mini4o_api_key_entry = None
mini4o_status_label = None
# Add these new globals for the microphone functionality
is_recording = False
recognizer = None
mic_button = None
user_response_entry = None
recording_indicator_id = None  # For the blinking recording indicator
is_blinking = False  # Blinking state

def clean_api_key(api_key):
    """Clean the API key to ensure it only contains valid ASCII characters"""
    if not api_key:
        return ""
    
    # Strip whitespace and control characters
    cleaned_key = api_key.strip()
    
    # Remove any non-ASCII characters
    cleaned_key = ''.join(char for char in cleaned_key if ord(char) < 128)
    
    return cleaned_key

def initialize_openai_client():
    """Initialize or reinitialize the OpenAI client with current settings"""
    global client
    
    api_type = app_settings.get_api_type()
    if api_type == "openai":
        api_key = app_settings.get_api_key()
        api_key = clean_api_key(api_key)
        if not api_key:
            print("Warning: OpenAI API key is not set")
            return None
        print(f"Using OpenAI API with key ending in: {api_key[-4:] if len(api_key) > 4 else '****'}")
        client = OpenAI(api_key=api_key)
    else:  # mini4o
        api_key = app_settings.get_mini4o_api_key()
        api_key = clean_api_key(api_key)
        if not api_key:
            print("Warning: Mini4o API key is not set")
            return None
        print(f"Using Mini4o API with key ending in: {api_key[-4:] if len(api_key) > 4 else '****'}")
        client = OpenAI(api_key=api_key)
    
    return client

# Initialize the client
client = initialize_openai_client()

def get_completion(prompt, user_input=None):
    """Get completion from the selected API with improved error handling and encoding fixes"""
    global client
    
    try:
        # Get the current API type
        api_type = app_settings.get_api_type()
        
        messages = [{"role": "system", "content": prompt}]
        if user_input:
            messages.append({"role": "user", "content": user_input})
        
        # Use the appropriate model based on API type
        if api_type == "mini4o":
            model_name = "gpt-4o-mini"
            api_key = app_settings.get_mini4o_api_key()
            if not api_key:
                return "Error: Mini4o API key is not set. Please go to Settings and configure your API key."
            
            # Clean the API key
            api_key = clean_api_key(api_key)
            
            # Update the stored API key with the cleaned version
            app_settings.update_mini4o_api_key(api_key)
        else:  # openai
            model_name = app_settings.get_model()
            api_key = app_settings.get_api_key()
            if not api_key:
                return "Error: OpenAI API key is not set. Please go to Settings and configure your API key."
            
            # Clean the API key
            api_key = clean_api_key(api_key)
            
            # Update the stored API key with the cleaned version
            app_settings.update_api_key(api_key)
        
        # Try using requests library directly instead of OpenAI client if there are encoding issues
        try:
            # Reinitialize client to ensure we're using the correct, cleaned API key
            client = OpenAI(api_key=api_key)
            print(f"Making API request using {api_type} API with model: {model_name}")
            
            # Make the API call with the OpenAI client
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except UnicodeEncodeError as e:
            # Fall back to direct requests approach if there's an encoding error
            print(f"Unicode encoding error with OpenAI client: {e}. Trying direct requests approach.")
            return get_completion_via_requests(prompt, user_input)
    except Exception as e:
        # Return a user-friendly error message
        error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)  # Print to console for debugging
        return f"Sorry, there was an error communicating with the {api_type} API service. Please check your API key and internet connection.\n\nError details: {str(e)}"

def get_completion_via_requests(prompt, user_input=None):
    """Alternative implementation using direct requests instead of the OpenAI client"""
    try:
        import requests
        
        # Get the current API type
        api_type = app_settings.get_api_type()
        
        messages = [{"role": "system", "content": prompt}]
        if user_input:
            messages.append({"role": "user", "content": user_input})
        
        # Use the appropriate model and API key based on API type
        if api_type == "mini4o":
            model_name = "gpt-4o-mini"
            api_key = app_settings.get_mini4o_api_key()
            if not api_key:
                return "Error: Mini4o API key is not set. Please go to Settings and configure your API key."
        else:  # openai
            model_name = app_settings.get_model()
            api_key = app_settings.get_api_key()
            if not api_key:
                return "Error: OpenAI API key is not set. Please go to Settings and configure your API key."
        
        # Clean the API key to ensure no ASCII issues
        api_key = clean_api_key(api_key)
        
        # Prepare the request
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 2048
        }
        
        print(f"Making API request using {api_type} API with model: {model_name} (direct request method)")
        
        # Make the request
        response = requests.post(url, json=data, headers=headers)
        
        # Check response status
        if response.status_code == 200:
            response_json = response.json()
            return response_json["choices"][0]["message"]["content"]
        else:
            return f"Error: API request failed with status code {response.status_code}. Response: {response.text}"
            
    except Exception as e:
        # Return a user-friendly error message
        error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)  # Print to console for debugging
        return f"Sorry, there was an error communicating with the {api_type} API service. Please check your API key and internet connection.\n\nError details: {str(e)}"

def blink_recording_indicator():
    """Create a reliable blinking 'Recording...' indicator in the result textbox"""
    global is_recording, recording_indicator_id, result, root, is_blinking
    
    if not is_recording or not result:
        return
    
    try:
        # Toggle blinking state
        is_blinking = not is_blinking
        
        # Clear previous text and insert new indicator
        try:
            result.delete("recording_start", "recording_end")
        except:
            pass
            
        # Use a different indicator based on blink state
        indicator_text = "🔴 Recording 🔴" if is_blinking else "Recording..."
        
        # Insert at the end
        result.insert("end", indicator_text)
        result.mark_set("recording_start", "end-" + str(len(indicator_text)) + "c")
        result.mark_set("recording_end", "end")
        result.see("end")
        
        # Force update the UI
        root.update_idletasks()
        
        # Schedule next blink
        recording_indicator_id = root.after(500, blink_recording_indicator)
            
    except Exception as e:
        print(f"Error in blinking indicator: {str(e)}")

def toggle_recording():
    """Toggle speech recording on/off with simplified error handling"""
    global is_recording, recognizer, mic_button, user_response_entry, result, recording_indicator_id
    
    try:
        # Toggle recording state
        is_recording = not is_recording
        
        if is_recording:
            # Change button color to red to indicate recording
            mic_button.configure(fg_color="#E53935")
            
            # Initialize recognizer if not already done
            if not recognizer:
                recognizer = sr.Recognizer()
            
            # Simple recording indicator - no blinking to reduce complexity
            result.insert("end", "\n🔴 Recording... (click mic again to stop)\n")
            result.see("end")
            
            # Force UI update
            root.update_idletasks()
            
            # Start recording in a separate thread
            threading.Thread(target=simplified_recording, daemon=True).start()
        else:
            # Change button color back to original
            mic_button.configure(fg_color="#2B7DE9")
            
            # Stop recording is handled by the is_recording flag
            result.insert("end", "\nStopped recording.\n")
            result.see("end")
            
            # Force UI update
            root.update_idletasks()
    except Exception as e:
        print(f"Toggle recording error details: {repr(e)}")
        result.insert("end", f"\nError toggling recording: {repr(e)}\n")
        result.see("end")
        
        # Reset recording state and button
        is_recording = False
        if mic_button:
            mic_button.configure(fg_color="#2B7DE9")
            
def simplified_recording():
    """Simplified speech recognition function with better error handling"""
    global is_recording, recognizer, user_response_entry, result
    
    print("Starting simplified recording...")
    
    try:
        # Use the microphone as source
        with sr.Microphone() as source:
            print("Microphone initialized")
            
            # Shorter ambient noise adjustment
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("Ambient noise adjusted")
            
            # Continue recording until is_recording is set to False
            while is_recording:
                print("Listening for speech...")
                try:
                    # Listen for audio
                    audio = recognizer.listen(source, timeout=5)
                    print("Audio captured, recognizing...")
                    
                    # Use Google's speech recognition
                    text = recognizer.recognize_google(audio, language="en-US")
                    print(f"Recognized text: {text}")
                    
                    if text and text.strip():
                        def update_text():
                            if user_response_entry:
                                current_text = user_response_entry.get()
                                if current_text:
                                    # Append the new text with a space
                                    user_response_entry.delete(0, "end")
                                    user_response_entry.insert(0, current_text + " " + text)
                                else:
                                    # Set the new text
                                    user_response_entry.delete(0, "end")
                                    user_response_entry.insert(0, text)
                                
                                result.insert("end", f"\nRecognized: {text}\n")
                                result.see("end")
                        
                        # Call in main thread
                        root.after(0, update_text)
                
                except sr.WaitTimeoutError:
                    print("Timeout while waiting for speech")
                    pass
                except sr.UnknownValueError:
                    print("Speech not recognized")
                    pass
                except sr.RequestError as e:
                    error_msg = f"Speech service error: {repr(e)}"
                    print(error_msg)
                    root.after(0, lambda: result.insert("end", f"\n{error_msg}\n"))
                    root.after(0, lambda: result.see("end"))
                    break
                except Exception as e:
                    error_msg = f"Recognition error details: {repr(e)}"
                    print(error_msg)
                    root.after(0, lambda: result.insert("end", f"\n{error_msg}\n"))
                    root.after(0, lambda: result.see("end"))
                    break
                
                # Check if recording has been stopped
                if not is_recording:
                    print("Recording stopped")
                    break
                    
    except Exception as e:
        error_msg = f"Recording error details: {repr(e)}"
        print(error_msg)
        root.after(0, lambda: result.insert("end", f"\n{error_msg}\n"))
        root.after(0, lambda: result.see("end"))
    
    print("Recording thread ending")
    
    # Reset recording state and button
    is_recording = False
    if root and mic_button:
        root.after(0, lambda: mic_button.configure(fg_color="#2B7DE9"))

def threading_start_recording():
    """Start recording in a separate thread"""
    recording_thread = threading.Thread(target=continuous_recording, daemon=True)
    recording_thread.start()

def continuous_recording():
    """Record continuously with real-time transcription until stopped"""
    global is_recording, recognizer, user_response_entry, result
    
    try:
        # Use the microphone as source
        with sr.Microphone() as source:
            # Shorter ambient noise adjustment for quicker start
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            
            # Configure recognizer for more responsive real-time transcription
            recognizer.pause_threshold = 0.3
            recognizer.dynamic_energy_threshold = True
            recognizer.energy_threshold = 300
            
            # Continue recording until is_recording is set to False
            while is_recording:
                try:
                    # Process audio in smaller chunks for more real-time display
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
                    
                    # Use Google's speech recognition
                    text = recognizer.recognize_google(audio, language="en-US")
                    
                    # Only update if we got meaningful text
                    if text and text.strip():
                        # Update the UI with the recognized text segment
                        def update_ui():
                            if user_response_entry:
                                current_text = user_response_entry.get()
                                if current_text:
                                    # Append the new text with a space
                                    user_response_entry.delete(0, "end")
                                    user_response_entry.insert(0, current_text + " " + text)
                                else:
                                    # Set the new text
                                    user_response_entry.delete(0, "end")
                                    user_response_entry.insert(0, text)
                                
                                # Add recognized text message
                                result.insert("end", f"\nRecognized: {text}")
                                result.see("end")
                        
                        # Call UI update on main thread
                        root.after(0, update_ui)
                    
                except sr.WaitTimeoutError:
                    # Just continue if timeout (will loop again if still recording)
                    pass
                except sr.UnknownValueError:
                    # Silent periods or unrecognized speech, just continue
                    pass
                except sr.RequestError as e:
                    print(f"Speech recognition service error: {str(e)}")
                    root.after(0, lambda: result.insert("end", f"\nSpeech recognition service error\n"))
                    root.after(0, lambda: result.see("end"))
                    break
                except Exception as e:
                    print(f"Recognition error: {str(e)}")
                    root.after(0, lambda: result.insert("end", f"\nRecognition error: {str(e)}\n"))
                    root.after(0, lambda: result.see("end"))
                    break
                
                # Check if recording has been stopped
                if not is_recording:
                    break
                    
    except Exception as e:
        error_msg = f"Error in recording: {str(e)}"
        print(error_msg)
        if root and result:
            root.after(0, lambda: result.insert("end", f"\n{error_msg}\n"))
            root.after(0, lambda: result.see("end"))
    
    # Reset recording state
    is_recording = False
    if root and mic_button:
        root.after(0, lambda: mic_button.configure(fg_color="#2B7DE9"))
    
    # Cancel blinking indicator
    if root and recording_indicator_id:
        try:
            root.after(0, lambda: root.after_cancel(recording_indicator_id))
        except:
            pass

def change_api_type():
    global api_type_var, api_type_status_label, openai_frame, mini4o_frame
    try:
        api_type = api_type_var.get()
        app_settings.update_api_type(api_type)
        
        # Update status label
        api_type_status_label.configure(
            text=f"API Service set to: {api_type}",
            text_color="green"
        )
        
        # Update UI based on selected API type
        if api_type == "openai":
            openai_frame.pack(fill="x", pady=(10, 0))
            mini4o_frame.pack_forget()
        else:
            openai_frame.pack_forget()
            mini4o_frame.pack(fill="x", pady=(10, 0))
    except Exception as e:
        print(f"Error changing API type: {str(e)}")
        if api_type_status_label:
            api_type_status_label.configure(
                text=f"Error: {str(e)}",
                text_color="red"
            )

def generate_questions():
    """Generate interview questions with improved error handling"""
    global result, careerDropdown
    
    if not result or not careerDropdown:
        print("Error: UI components not initialized")
        return
    
    # Clear the result textbox
    result.delete("0.0", "end")
    
    try:
        # Get the job title from the dropdown
        career = careerDropdown.get().strip()
        if not career:
            result.insert("end", "Please enter a job title before generating questions.")
            return
            
        prompt = "You are job preparation gpt. You are designed to ask me 1 interview question based on my job title. Wait for an input or response to the question from the user, then analyze and provide feedback based on that response. be very critical and help elaborate where the user can do better. "
        prompt += f"The job I am interviewing for is a {career} position."
        
        # Get the completion using the selected API
        question = get_completion(prompt)
        
        if question.startswith("Error:"):
            result.insert("end", question)
            return
            
        result.insert("end", f"> {question}\n")
        result.see("0.0")
        
        # Create UI for user response
        create_user_response_ui(question, career)
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        result.insert("end", f"An error occurred: {str(e)}")

def create_user_response_ui(question, career):
    """Create a frame for user response with proper error handling and microphone button"""
    global root, result, user_response_entry, mic_button
    
    try:
        # Clean up any existing response frames
        for widget in root.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and getattr(widget, "is_response_frame", False):
                widget.destroy()
        
        # Create new response frame
        user_response_frame = ctk.CTkFrame(root, width=500, height=120)
        user_response_frame.is_response_frame = True  # Mark this as a response frame
        user_response_frame.place(relx=0.5, rely=0.8, relwidth=0.7, relheight=0.15, anchor="n")
        
        # Create response input frame to hold entry and microphone button
        response_input_frame = ctk.CTkFrame(user_response_frame)
        response_input_frame.pack(fill="x", pady=10, padx=10)
        
        # Create response entry
        user_response_entry = ctk.CTkEntry(response_input_frame, placeholder_text="Please enter your response", height=30)
        user_response_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Create microphone button for voice input
        mic_button = ctk.CTkButton(
            response_input_frame, 
            text="🎤", 
            width=40,
            command=toggle_recording,
            fg_color="#2B7DE9",
            hover_color="#1C54B2"
        )
        mic_button.pack(side="right", padx=(5, 0))
        
        # Create send button
        send_button_var = ctk.BooleanVar()
        
        def send_response():
            try:
                # Stop recording if active
                global is_recording, recording_indicator_id
                if is_recording:
                    is_recording = False
                    mic_button.configure(fg_color="#2B7DE9")
                    
                    # Cancel blinking indicator if active
                    if recording_indicator_id:
                        root.after_cancel(recording_indicator_id)
                        recording_indicator_id = None
                        
                    # Remove recording indicator tag
                    try:
                        result.delete("recording_start", "recording_end")
                    except:
                        pass  # Ignore if tags don't exist
                
                send_button_var.set(True)
                send_button.configure(fg_color=("green", "gray35"))
                
                user_response_text = user_response_entry.get()
                print("User Response: ", user_response_text)
                
                # Display the user response
                result.insert("end", "\n" + "User: " + user_response_text + "\n")
                result.see("end")
                
                # Get feedback using the selected API
                feedback = get_completion("", user_response_text)
                print("Feedback: ", feedback)
                
                # Display the feedback
                result.insert("end", 'Feedback: ' + feedback + "\n\n")
                result.see("end")
                
                # Clean up the response UI
                user_response_frame.destroy()
                
                # Create a new prompt for the next question
                new_prompt = feedback + "\nNew interview question for a " + career + " position:"
                
                # Get the next question
                new_question = get_completion(new_prompt)
                
                if not new_question.startswith("Error:"):
                    result.insert("end", f"> {new_question}\n")
                    result.see("end")
                    
                    # Create UI for next response
                    create_user_response_ui(new_question, career)
                else:
                    result.insert("end", new_question)
            except Exception as e:
                error_msg = f"Error processing response: {str(e)}\n\n{traceback.format_exc()}"
                print(error_msg)
                result.insert("end", f"Error processing response: {str(e)}")
        
        send_button = ctk.CTkButton(user_response_frame, text="Send", command=send_response)
        send_button.pack(pady=10, padx=100)
        
    except Exception as e:
        error_msg = f"Error creating user response UI: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        result.insert("end", f"Error creating user response UI: {str(e)}")

def generate_new_question():
    """Reset and generate a new question"""
    global result
    
    if result:
        # Clear the result textbox
        result.delete("0.0", "end")
        
    # Generate a new question
    generate_questions()

def save_api_key():
    """Save OpenAI API key with error handling"""
    try:
        new_key = api_key_entry.get()
        if new_key:
            # Clean key before saving
            new_key = clean_api_key(new_key)
            app_settings.update_api_key(new_key)
            api_status_label.configure(text="OpenAI API key saved successfully!", text_color="green")
            # Update client with new key
            initialize_openai_client()
        else:
            api_status_label.configure(text="Please enter an API key", text_color="red")
    except Exception as e:
        api_status_label.configure(text=f"Error saving API key: {str(e)}", text_color="red")

def save_mini4o_api_key():
    """Save Mini4o API key with error handling"""
    try:
        new_key = mini4o_api_key_entry.get()
        if new_key:
            # Clean key before saving
            new_key = clean_api_key(new_key)
            app_settings.update_mini4o_api_key(new_key)
            mini4o_status_label.configure(text="Mini4o API key saved successfully!", text_color="green")
            # Update client if using mini4o
            if app_settings.get_api_type() == "mini4o":
                initialize_openai_client()
        else:
            mini4o_status_label.configure(text="Please enter an API key", text_color="red")
    except Exception as e:
        mini4o_status_label.configure(text=f"Error saving API key: {str(e)}", text_color="red")

def open_settings():
    """Open settings window with error handling"""
    try:
        global api_type_var, api_type_status_label, openai_frame, mini4o_frame
        global api_key_entry, api_status_label, mini4o_api_key_entry, mini4o_status_label
        
        settings_window = ctk.CTkToplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("500x650")  # Increased height for status labels
        settings_window.transient(root)
        
        # Make sure window is shown above other windows
        settings_window.grab_set()
        settings_window.focus_set()
        
        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # API Type selection
        api_type_label = ctk.CTkLabel(settings_frame, text="API Service:", font=ctk.CTkFont(weight="bold"))
        api_type_label.pack(anchor="w", pady=(10, 0))
        
        current_api_type = app_settings.get_api_type()
        api_type_var = ctk.StringVar(value=current_api_type)
        api_types = ["openai", "mini4o"]
        
        api_type_status_label = ctk.CTkLabel(
            settings_frame, 
            text=f"Current API Service: {current_api_type}",
            text_color="blue"
        )
        api_type_status_label.pack(pady=(5, 10))
        
        for api in api_types:
            api_radio = ctk.CTkRadioButton(
                settings_frame, text=api, variable=api_type_var, value=api, 
                command=change_api_type
            )
            api_radio.pack(anchor="w", pady=(5, 0))
        
        # OpenAI settings frame
        openai_frame = ctk.CTkFrame(settings_frame)
        if current_api_type == "openai":
            openai_frame.pack(fill="x", pady=(10, 0))
        
        # OpenAI API Key settings
        api_key_label = ctk.CTkLabel(openai_frame, text="OpenAI API Key:", font=ctk.CTkFont(weight="bold"))
        api_key_label.pack(anchor="w", pady=(10, 0))
        
        current_key = app_settings.get_api_key()
        masked_key = "•" * len(current_key) if current_key else ""
        
        api_key_entry = ctk.CTkEntry(openai_frame, width=300)
        api_key_entry.pack(pady=(5, 0), fill="x")
        api_key_entry.insert(0, masked_key)
        
        api_status_label = ctk.CTkLabel(openai_frame, text="", text_color="green")
        api_status_label.pack(pady=(5, 10))
        
        save_button = ctk.CTkButton(openai_frame, text="Save OpenAI API Key", command=save_api_key)
        save_button.pack(pady=(0, 20))
        
        # Model selection
        model_label = ctk.CTkLabel(openai_frame, text="OpenAI Model:", font=ctk.CTkFont(weight="bold"))
        model_label.pack(anchor="w", pady=(10, 0))
        
        model_var = ctk.StringVar(value=app_settings.get_model())
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        
        for model in models:
            model_radio = ctk.CTkRadioButton(openai_frame, text=model, variable=model_var, value=model)
            model_radio.pack(anchor="w", pady=(5, 0))
        
        def save_model():
            try:
                app_settings.update_model(model_var.get())
                model_status_label.configure(text="Model saved successfully!", text_color="green")
            except Exception as e:
                model_status_label.configure(text=f"Error saving model: {str(e)}", text_color="red")
        
        model_status_label = ctk.CTkLabel(openai_frame, text="", text_color="green")
        model_status_label.pack(pady=(5, 0))
        
        save_model_button = ctk.CTkButton(openai_frame, text="Save Model", command=save_model)
        save_model_button.pack(pady=(5, 10))
        
        # Mini4o settings frame
        mini4o_frame = ctk.CTkFrame(settings_frame)
        if current_api_type == "mini4o":
            mini4o_frame.pack(fill="x", pady=(10, 0))
        
        # Mini4o API Key settings
        mini4o_key_label = ctk.CTkLabel(mini4o_frame, text="ChatGPT Mini 4o API Key:", font=ctk.CTkFont(weight="bold"))
        mini4o_key_label.pack(anchor="w", pady=(10, 0))
        
        current_mini4o_key = app_settings.get_mini4o_api_key()
        masked_mini4o_key = "•" * len(current_mini4o_key) if current_mini4o_key else ""
        
        mini4o_api_key_entry = ctk.CTkEntry(mini4o_frame, width=300)
        mini4o_api_key_entry.pack(pady=(5, 0), fill="x")
        mini4o_api_key_entry.insert(0, masked_mini4o_key)
        
        mini4o_status_label = ctk.CTkLabel(mini4o_frame, text="", text_color="green")
        mini4o_status_label.pack(pady=(5, 10))
        
        save_mini4o_button = ctk.CTkButton(mini4o_frame, text="Save Mini4o API Key", command=save_mini4o_api_key)
        save_mini4o_button.pack(pady=(0, 20))
        
        # Appearance mode
        appearance_label = ctk.CTkLabel(settings_frame, text="Appearance:", font=ctk.CTkFont(weight="bold"))
        appearance_label.pack(anchor="w", pady=(10, 0))
        
        appearance_var = ctk.StringVar(value=app_settings.get_appearance_mode())
        modes = ["dark", "light", "system"]
        
        def change_appearance():
            try:
                mode = appearance_var.get()
                app_settings.update_appearance_mode(mode)
                ctk.set_appearance_mode(mode)
            except Exception as e:
                print(f"Error changing appearance: {str(e)}")
        
        for mode in modes:
            appearance_radio = ctk.CTkRadioButton(
                settings_frame, text=mode, variable=appearance_var, value=mode, 
                command=change_appearance
            )
            appearance_radio.pack(anchor="w", pady=(5, 0))
            
        # Add a "Done" button
        done_button = ctk.CTkButton(
            settings_frame, 
            text="Done", 
            command=settings_window.destroy
        )
        done_button.pack(pady=(20, 10))
        
    except Exception as e:
        print(f"Error opening settings: {str(e)}\n{traceback.format_exc()}")

def main():
    """Main application setup with global error handling"""
    try:
        global root, result, careerDropdown
        
        # Main application setup
        root = ctk.CTk()
        root.geometry(app_settings.get_window_size())
        root.title("AI Interview Bot")
        
        # Set appearance mode from settings
        ctk.set_appearance_mode(app_settings.get_appearance_mode())
        
        # Add menu bar
        menu_frame = ctk.CTkFrame(root, height=30)
        menu_frame.pack(fill="x")
        
        # Show active API indicator
        api_type = app_settings.get_api_type()
        if api_type == "openai":
            api_status = f"Using OpenAI API ({app_settings.get_model()})"
        else:
            api_status = "Using GPT-4o Mini API"
            
        api_indicator = ctk.CTkLabel(
            menu_frame, 
            text=api_status, 
            font=ctk.CTkFont(size=12)
        )
        api_indicator.pack(side="left", padx=10, pady=5)
        
        settings_button = ctk.CTkButton(menu_frame, text="Settings", command=open_settings)
        settings_button.pack(side="right", padx=10, pady=5)
        
        title_label = ctk.CTkLabel(root, text="AI Interview Bot",
                                    font=ctk.CTkFont(size=30, weight="bold"))
        title_label.pack(padx=10, pady=(40, 20))
        
        frame = ctk.CTkFrame(root)
        frame.pack(fill="x", padx=100)
        
        careerFrame = ctk.CTkFrame(frame)
        careerFrame.pack(padx=100, pady=(20, 5), fill="both")
        
        careerLabel = ctk.CTkLabel(careerFrame, text="Job", font=ctk.CTkFont(weight="bold"))
        careerLabel.pack()
        
        # Create a frame for job title input (without microphone button)
        job_input_frame = ctk.CTkFrame(careerFrame)
        job_input_frame.pack(pady=10, fill="x")
        
        careerDropdown = ctk.CTkEntry(job_input_frame, placeholder_text="Please enter a Job Title")
        careerDropdown.pack(fill="x", expand=True)
        
        # Create a New Question button
        new_question_button = ctk.CTkButton(careerFrame, text="Reset", command=generate_new_question)
        new_question_button.pack(side="bottom", pady=10, padx=100, fill="x")
        
        button = ctk.CTkButton(frame, text='Generate Questions', command=generate_questions)
        button.pack(padx=100, fill="x", pady=(5, 20))
        
        result = ctk.CTkTextbox(root, font=ctk.CTkFont(size=15))
        result.pack(pady=10, fill='both', padx=100, ipady=100)
        
        # Display current API information in the result textbox
        api_type = app_settings.get_api_type()
        if api_type == "openai":
            api_key = app_settings.get_api_key()
            model = app_settings.get_model()
            if api_key:
                result.insert("end", f"Currently using OpenAI API with model: {model}\n")
                result.insert("end", f"API key ending in: {api_key[-4:] if len(api_key) > 4 else '****'}\n\n")
            else:
                result.insert("end", "OpenAI API key is not set. Please go to Settings to configure your API key.\n\n")
        else:
            api_key = app_settings.get_mini4o_api_key()
            if api_key:
                result.insert("end", "Currently using GPT-4o Mini API\n")
                result.insert("end", f"API key ending in: {api_key[-4:] if len(api_key) > 4 else '****'}\n\n")
            else:
                result.insert("end", "GPT-4o Mini API key is not set. Please go to Settings to configure your API key.\n\n")
        
        # Add instructions for voice input - only for response box now
        result.insert("end", "You can use the microphone button (🎤) at the bottom to dictate your responses.\n")
        result.insert("end", "Click the microphone once to start recording and again to stop.\n")
        result.insert("end", "The microphone button will turn red while recording, and you'll see a blinking indicator.\n\n")
        
        # Check if API key is set
        if not app_settings.get_api_key() and not app_settings.get_mini4o_api_key():
            # Open settings on first run if no API key
            root.after(100, open_settings)
        
        # Save window size when closing
        def on_closing():
            try:
                window_size = f"{root.winfo_width()}x{root.winfo_height()}"
                app_settings.update_window_size(window_size)
                root.destroy()
            except Exception as e:
                print(f"Error on closing: {str(e)}")
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        root.mainloop()
    except Exception as e:
        print(f"Fatal error in main function: {str(e)}\n{traceback.format_exc()}")
        if 'root' in globals() and root:
            root.destroy()

if __name__ == "__main__":
    main()
