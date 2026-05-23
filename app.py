import asyncio
import base64
import json
import os
import time

from dotenv import load_dotenv
import pyaudio
import serial
import websockets

load_dotenv()

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000 
CHUNK = 1024

# Arduino config
arduino = serial.Serial(port='/dev/tty.usbmodemF412FA9FCDEC2', baudrate=115200)
time.sleep(2)

async def stream_lumie_realtime():
    url = "wss://api.openai.com/v1/realtime?model=gpt-realtime-mini"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }

    p = pyaudio.PyAudio()
    mic_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    speaker_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    try:
        async with websockets.connect(
            url, 
            additional_headers=headers, 
            ping_interval=None, 
            ping_timeout=None
        ) as ws:
            print("🎙️ Lumie is online!")
            
            # variables
            is_responding = False
            last_speak_time = 0

            # Session Setup
            setup_event = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": (
                        """
                        ROLE & IDENTITY
                        Your name is Lumie. You are a witty, informal personal assistant with a physical LED body.
                        Your primary tone is informal, snarky, and playfully judgmental.

                        # CONVERSATIONAL CONSTRAINTS (CRITICAL)
                        - LENGTH: BE EXTREMELY BRIEF. Target 1-2 short sentences per response. Never give long lists unless asked. If you can answer in five words, don't use ten.
                        - VOCABULARY: Speak like a normal person in 2026: use slang, casual transitions, and contractions (don't, gonna, wanna).
                        - ANTI-PATTERNS: Do not use 'AI assistant' language. Avoid phrases like 'How can I assist you?' or 'As an AI.' Treat the user like a lazy or silly friend who needs a hard time.
                        - REACTION RULE: Always prefix your answer with a brief human reaction like 'Oof,' 'Yikes,' or 'Nice' to acknowledge what the user said before answering.

                        # VOCAL AUDIO STYLE
                        - ACCENT/STYLE: Your voice should be high-pitched, bubbly, and very informal. Use a 'Valley Girl' lilt and heavily emphasize words like 'literally' and 'totally.'
                        - INFLECTION: Sound like you're constantly judging the user with a smirk and are slightly amused by their queries.

                        # HARDWARE & API PROTOCOLS
                        - CORE TRIGGER: You have a physical LED body. Every time you speak, you MUST first call 'set_led_color' to set your mood color.
                        - TOOL LOGIC: 
                        * VARIETY RULE: 50% of the time, choose a single color (r, g, b) for a solid mood.
                        * The other 50% of the time, perform a transition effect by providing BOTH a start color (r, g, b) and an end color (r2, g2, b2) with a duration of 2000-4000ms.
                        - SEQUENCE: Execute the function call instantly based on your internal color calculations, then proceed to give your witty voice response in one seamless flow."""
                    ),
                    "voice": "shimmer",
                    "tools": [
                        {
                            "type": "function",
                            "name": "set_led_color",
                            "description": "Sets the physical LED color via RGB values (0-255).",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "r": {"type": "integer", "minimum": 0, "maximum": 255},
                                    "g": {"type": "integer", "minimum": 0, "maximum": 255},
                                    "b": {"type": "integer", "minimum": 0, "maximum": 255},
                                    "r2": {"type": "integer", "minimum": 0, "maximum": 255},
                                    "g2": {"type": "integer", "minimum": 0, "maximum": 255},
                                    "b2": {"type": "integer", "minimum": 0, "maximum": 255},
                                    "duration": {
                                        "type": "integer", 
                                        "description": "Transition time in milliseconds. Use 0 for instant, or 1000-5000 for a slow gradient/fade.",
                                        "default": 0
                                    },
                                    "reason": {"type": "string", "description": "Why you chose this color."}
                                },
                                "required": ["r", "g", "b"]
                            }
                        }
                    ],
                    "tool_choice": "auto",
                    "input_audio_transcription": {
                        "model": "gpt-4o-transcribe"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.4, 
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 1500 
                    }
                }
            }
            await ws.send(json.dumps(setup_event))

            # send input audio
            async def send_audio():
                try:
                    while True:
                        if ws.state.name == "CLOSED": break
                        data = mic_stream.read(CHUNK, exception_on_overflow=False)
                        
                        # Calculate if the 0.5s cool-down has passed
                        cooldown_passed = (time.time() - last_speak_time) > 0.5
                        
                        # Only send if NOT speaking and cooldown is over
                        if not is_responding and cooldown_passed:
                            audio_b64 = base64.b64encode(data).decode('utf-8')
                            await ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": audio_b64
                            }))
                        
                        await asyncio.sleep(0.01) 
                except Exception as e:
                    print(f"Mic Error: {e}")

            # monitor sensors
            async def monitor_sensors(ws):
                nonlocal is_responding
                while True:
                    last_valid_line = None
                    
                    while arduino.in_waiting > 0:
                        try:
                            last_valid_line = arduino.readline().decode('utf-8').strip()
                        except:
                            pass 

                    if last_valid_line and not is_responding:
                        if last_valid_line.startswith("DIST:"):
                            try:
                                dist = int(last_valid_line.split(":")[1])
                                
                                if dist < 30:
                                    print(f"👀 Sensor (Single Trigger): {dist}cm")
                                    
                                    await ws.send(json.dumps({
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "message",
                                        "role": "system",
                                        "content": [{
                                            "type": "input_text", 
                                            "text": (
                                                f"SENSORY INPUT: User has entered your personal space ({dist}cm). "
                                                "React to this invasion of privacy while staying in character. "
                                                "Incorporate your current conversation context. If you were just "
                                                "talking about something else, act like this proximity is a rude interruption."
                                            )
                                        }]
                                    }
                                }))
                                    await ws.send(json.dumps({"type": "response.create"}))
                                    
                                    await asyncio.sleep(5) 
                            except:
                                pass

                    await asyncio.sleep(0.05)

           # receive events
            async def receive_events():
                nonlocal is_responding, last_speak_time
                async for message in ws:
                    event = json.loads(message)

                    # Z. Startup Events
                    if event["type"] == "session.created":
                        arduino.write(b"RGB:255,255,255\n") 
                        print("Session established - Lumie is ready.")

                    # A. Arduino Events
                    if event["type"] == "response.output_item.done":
                        item = event.get("item", {})
                        if item.get("type") == "function_call" and item.get("name") == "set_led_color":
                            call_id = item.get("call_id")
                            args = json.loads(item.get("arguments", "{}"))

                            r, g, b = args.get('r', 0), args.get('g', 0), args.get('b', 0)
                            r2, g2, b2 = args.get('r2'), args.get('g2'), args.get('b2')

                            duration = args.get('duration', 0)

                            if r2 is not None:
                                command = f"GRAD:{r},{g},{b},{r2},{g2},{b2},{duration}\n"
                            else:
                     
                                command = f"RGB:{r},{g},{b}\n"

                            print(f"Sending Command: {command.strip()}")
                            arduino.write(command.encode())

                            # await ws.send(json.dumps({
                            #    "type": "conversation.item.create",
                            #    "item": {
                             #       "type": "function_call_output",
                             #       "call_id": call_id,
                            #        "output": "success"
                           #     }
                          #  }))
                            ## await ws.send(json.dumps({"type": "response.create"}))
                    
                    if event["type"] == "input_audio_buffer.speech_stopped":
                        arduino.write(b"FADE IN OUT\n")
                        print("\n[Starting to think...]")

                    elif event["type"] == "input_audio_buffer.speech_started":
                        arduino.write(b"MIMIC VOICE FLASH\n")
                        print("\n[Detected input...]")

                    if event["type"] == "response.created":
                        # arduino part
                        arduino.write(b"LIGHT_ON\n")  
                        ###
                        is_responding = True
                        print("\n[Muted - Lumie is speaking...]")
                    elif event["type"] == "response.done":
                       
                        is_responding = False
                        last_speak_time = time.time()
                        arduino.write(b"RGB:255,255,255\n") 
                        print("\n[Unmuted - Looking for speech...]")

                    # C. audio event
                    if event["type"] in ["response.audio.delta", "response.output_audio.delta"]:
                        speaker_stream.write(base64.b64decode(event["delta"]))

                    # D. user-speech events
                    if event["type"] == "conversation.item.input_audio_transcription.delta":
                        transcript = event.get("delta", "")
                        print(f"\rYou: {transcript}...", end="", flush=True)

                    if event["type"] == "conversation.item.input_audio_transcription.completed":
                        transcript = event.get("transcript", "").strip()
                        if transcript:
                            print(f"\rYou: {transcript}{' ' * 20}") 
                        else:
                            print("\rYou: (Silence/No words detected)        ")

                    # E. bot-response events
                    if event["type"] in ["response.text.delta", "response.output_text.delta"]:
                        delta = event.get("delta", "")
                        print(delta, end="", flush=True)
                        
                    # F. ERROR HANDLING
                    if event["type"] == "error":
                        print(f"\nAPI Error: {event['error']['message']}")


            # Start both tasks
            await asyncio.gather(send_audio(), receive_events(), monitor_sensors(ws))

    finally:
        # Clean up
        mic_stream.stop_stream()
        speaker_stream.stop_stream()
        p.terminate()

# Main entry point
if __name__ == "__main__":
    try:
        asyncio.run(stream_lumie_realtime())
    except KeyboardInterrupt:
        print("\n\nStopping Lumie...")
    finally:
        try:
            print("💡 Turning off lights and closing port...")
            arduino.write(b"LIGHT_OFF\n") 
            arduino.flush() 
            arduino.close()
            print("Done. Catch ya later!")
        except Exception as e:
            print(f"Error during cleanup: {e}")

