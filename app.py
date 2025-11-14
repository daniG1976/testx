import os
import json
from flask import Flask, request, jsonify, render_template_string
import httpx
import base64

# Initialisiere die Flask App
app = Flask(__name__)

# --- API Konfiguration ---
# SICHERE VERSION: Lese den API Key aus den Umgebungsvariablen von Render
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Überprüfung: Ist der Key vorhanden (nicht None) und nicht leer
API_KEY_VALID = GOOGLE_API_KEY is not None and GOOGLE_API_KEY.strip() != ""

# HILFSVARIABLE: Berechne den String-Status für JavaScript-Injektion
JS_API_KEY_STATUS = 'true' if API_KEY_VALID else 'false'

# API Endpunkt (wird nur verwendet, wenn der Key gültig ist)
GOOGLE_STT_ENDPOINT = f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_API_KEY}"
# --- Ende Konfiguration ---

# WICHTIG: Logging, um den Status des API-Keys zu prüfen
if API_KEY_VALID:
    app.logger.info("✅ GOOGLE_API_KEY aus Umgebungsvariablen geladen.")
else:
    app.logger.error("❌ GOOGLE_API_KEY NICHT gefunden oder leer.")


# Wir embedden den HTML/JS-Inhalt direkt.
HTML_CONTENT = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebRTC Audio Recorder & Transcriber</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
    </style>
</head>
<body class="bg-gray-900 text-white min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-gray-800 rounded-xl shadow-2xl p-6 md:p-8">
        <h1 class="text-3xl font-bold text-center text-blue-400 mb-2">
            🎙️ Audio Recorder & Transcriber
        </h1>
        <p class="text-center text-gray-400 mb-6">
            Direkter Mikrofonzugriff (WebRTC) – **Backend in Python**.
        </p>
        <div id="status-container" class="mb-6 p-4 rounded-lg text-center font-mono transition duration-300 bg-gray-700">
            <!-- Leer gelassen, wird sofort von JS gefüllt -->
            <p id="status-text" class="text-lg text-green-400">...</p>
        </div>
        <div class="flex flex-col space-y-4">
            <button id="record-button" 
                    class="flex items-center justify-center space-x-2 px-6 py-3 text-lg font-semibold rounded-lg shadow-lg 
                           bg-green-600 hover:bg-green-700 transition duration-150"
                    disabled>
                <svg id="record-icon" class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
                </svg>
                <span id="record-label">Aufnahme starten</span>
            </button>
            <button id="stop-button" 
                    class="flex items-center justify-center space-x-2 px-6 py-3 text-lg font-semibold rounded-lg shadow-lg 
                           bg-red-600 hover:bg-red-700 transition duration-150 disabled:opacity-50"
                    disabled>
                <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M5 4a1 1 0 00-1 1v10a1 1 0 001 1h10a1 1 0 001-1V5a1 1 0 00-1-1H5z" />
                </svg>
                Aufnahme stoppen
            </button>
        </div>
        <div class="mt-8">
            <h2 class="text-xl font-semibold mb-3 text-gray-300">Transkriptionsergebnis</h2>
            <textarea id="result-text" readonly 
                      class="w-full h-40 p-3 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 resize-none 
                             focus:border-blue-500 transition duration-150"
                      placeholder="Transkription wird hier angezeigt..."></textarea>
            <p id="base64-size" class="text-xs text-gray-500 mt-2">Base64-Größe: 0 Bytes</p>
        </div>
    </div>
    <!-- *** Skript am Ende des Body für korrekte Element-Initialisierung (iOS-Fix) *** -->
    <script>
        // *** Frontend-Logik ***
        
        // Elemente sind GARANTIERT verfügbar
        const statusText = document.getElementById('status-text');
        const recordButton = document.getElementById('record-button');
        const stopButton = document.getElementById('stop-button');
        const resultText = document.getElementById('result-text');
        const base64Size = document.getElementById('base64-size');
        const statusContainer = document.getElementById('status-container');
        
        // HINWEIS: API-Status vom Python-Backend übernommen.
        const apiKeyValid = '{JS_API_KEY_STATUS}'; 

        let mediaRecorder = null;
        let audioChunks = [];
        let stream = null; 

        // Hilfsfunktionen 
        function stopStream(currentStream) {{
            if (currentStream) {{
                currentStream.getTracks().forEach(track => {{
                    track.stop();
                }});
            }}
        }}

        function updateStatus(message, colorClass = 'text-green-400', bgClass = 'bg-gray-700') {{
            statusText.textContent = message;
            statusContainer.className = `mb-6 p-4 rounded-lg text-center font-mono transition duration-300 ${{bgClass}}`;
            statusText.className = colorClass;
        }}
        
        // ** Initialisierung: NUR Listener binden und Status setzen **
        (function initApp() {{
            // 1. Listener binden 
            recordButton.addEventListener('click', startRecording);
            stopButton.addEventListener('click', stopRecording);
            
            // 2. Status prüfen und setzen
            if (apiKeyValid === 'false') {{
                updateStatus(
                    "API-SCHLÜSSEL FEHLT. Bitte in Render-Umgebungsvariablen prüfen.", 
                    'text-yellow-400', 
                    'bg-red-800'
                );
                recordButton.disabled = true;
            }} else {{
                 // Setzt den Zustand auf "Bereit" und aktiviert den Button
                 updateStatus("Bereit. Klicken Sie auf Aufnahme starten.", 'text-green-400', 'bg-gray-700');
                 recordButton.disabled = false; // EXPLIZIT Button freischalten
            }}
        }})();
        // ** ENDE Initialisierung **


        async function transcribeAudio(base64Audio) {{
            if (apiKeyValid === 'false') {{
                updateStatus("Transkription blockiert: API-Schlüssel fehlt.", 'text-red-500', 'bg-red-900');
                resultText.value = "Fehler: Der API-Schlüssel ist nicht im Backend hinterlegt.";
                recordButton.disabled = true; 
                return;
            }}
            
            updateStatus("Transkription läuft...", 'text-amber-400', 'bg-blue-900');
            resultText.value = "Sende Audio an Python-Backend zur Verarbeitung...";

            try {{
                const response = await fetch('/transcribe', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ audio_base64: base64Audio }})
                }});

                const data = await response.json();

                if (response.ok) {{
                    const transcript = data.transcript;
                    resultText.value = transcript;
                    updateStatus("Transkription abgeschlossen!", 'text-green-400', 'bg-green-900');
                }} else {{
                    const errorMessage = data.error || "Unbekannter Fehler im Python-Backend.";
                    resultText.value = `Fehler: ${{errorMessage}}`;
                    updateStatus("API-Fehler", 'text-red-500', 'bg-red-900');
                }}
                
            }} catch (error) {{
                resultText.value = `Netzwerkfehler: Konnte Python-Backend nicht erreichen. (${{error.message}})`;
                updateStatus("Netzwerkfehler", 'text-red-500', 'bg-red-900');
            }}
            
            // UI zurücksetzen und Button freigeben
            recordButton.disabled = false;
        }}

        async function startRecording() {{
            if (recordButton.disabled) return;
            
            recordButton.disabled = true;
            stopButton.disabled = true; 

            try {{
                updateStatus("Warten auf Mikrofon-Zugriff...", 'text-yellow-300', 'bg-gray-700');
                
                // *** WICHTIG: getUserMedia wird HIER (im Klick-Handler) aufgerufen, wie von iOS verlangt ***
                stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});

                // Recording-Logik
                mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'audio/webm' }});
                audioChunks = [];
                
                mediaRecorder.ondataavailable = event => {{ 
                    if (event.data.size > 0) {{
                        audioChunks.push(event.data); 
                    }}
                }};

                mediaRecorder.onstop = () => {{
                    // Sofort stream stoppen, wenn Aufnahme beendet ist
                    stopStream(stream);
                    stream = null; 
                    
                    if (audioChunks.length === 0) {{
                        updateStatus("Aufnahme zu kurz oder leer. Versuchen Sie es erneut.", 'text-red-500', 'bg-red-900');
                        recordButton.disabled = false;
                        return;
                    }}
                    const audioBlob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                    const reader = new FileReader();
                    
                    reader.onloadend = () => {{
                        const base64Audio = reader.result.split(',')[1];
                        base64Size.textContent = `Base64-Größe: ${{Math.round(base64Audio.length / 1024)}} KB (WebM/OPUS)`;
                        transcribeAudio(base64Audio);
                    }};
                    reader.readAsDataURL(audioBlob);
                }};

                mediaRecorder.start();
                updateStatus("Aufnahme läuft... (Klicken Sie auf Stopp)", 'text-red-500', 'bg-red-900');
                stopButton.disabled = false; 
                
            }} catch (err) {{
                // *** NEU: Protokolliert den genauen Fehlergrund im Browser-Protokoll ***
                console.error("Mikrofon Fehler (genaue Ursache): ", err); 
                
                stopStream(stream);
                stream = null; 
                
                let errorMessage = "Zugriff auf Mikrofon verweigert. Einstellungen prüfen!";
                // Wenn der Fehler ein spezifischer ist, zeigen wir dies an
                if (err.name === 'NotAllowedError') {{
                    errorMessage = "Zugriff verweigert (vom Nutzer oder OS). Bitte Browser-/Geräteeinstellungen prüfen!";
                }} else if (err.name === 'NotReadableError') {{
                    errorMessage = "Mikrofon ist belegt (von anderer App). Andere Apps schließen!";
                }} else if (err.name === 'NotSupportedError') {{
                    errorMessage = "Audioaufnahme nicht unterstützt. (Sehr unwahrscheinlich)";
                }}
                
                updateStatus(errorMessage, 'text-red-500', 'bg-red-900');
                recordButton.disabled = false; 
            }}
        }}

        function stopRecording() {{
            if (mediaRecorder && mediaRecorder.state === 'recording') {{
                mediaRecorder.stop();
            }}
            stopButton.disabled = true;
            updateStatus("Aufnahme beendet. Verarbeite...", 'text-yellow-300', 'bg-gray-700');
        }}

    </script>
</body>
</html>
"""

def stt_from_base64(audio_base64: str) -> dict:
    """
    Sendet die Base64-kodierte Audiodatei an die Google Speech-to-Text API.
    """
    
    if not API_KEY_VALID:
        return {"error": "API Key nicht konfiguriert oder Platzhalterwert verwendet."}
    
    headers = {"Content-Type": "application/json"}
    
    # WEBM_OPUS ist das Standardformat, das MediaRecorder auf den meisten Browsern ausgibt.
    request_data = {
        "config": {
            "encoding": "WEBM_OPUS",
            "sampleRateHertz": 48000, 
            "languageCode": "de-DE", 
            "enableAutomaticPunctuation": True,
        },
        "audio": {
            "content": audio_base64
        }
    }

    try:
        # Synchrone API-Anfrage
        response = httpx.post(GOOGLE_STT_ENDPOINT, headers=headers, json=request_data, timeout=30)
        response.raise_for_status() 

        result = response.json()
        
        if result and 'results' in result and result['results']:
            transcript = result['results'][0]['alternatives'][0]['transcript']
            return {"transcript": transcript}
        elif 'error' in result:
            return {"error": f"Google API Fehler: {result['error'].get('message', 'Unbekannt')}"}
        else:
            return {"error": "Konnte keine Sprache erkennen (Zu leise oder zu kurz)."}
        
    except httpx.RequestError as e:
        return {"error": f"Verbindungsfehler zur Google API: {e}"}
    except Exception as e:
        return {"error": f"Unerwarteter Fehler während der Transkription: {e}"}


@app.route('/')
def index():
    """Liefert das HTML-Frontend mit der korrigierten WebRTC-Logik."""
    return render_template_string(HTML_CONTENT)

@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    """Endpunkt, der die Base64-Audiodaten vom Frontend empfängt."""
    try:
        data = request.get_json()
        if not data or 'audio_base64' not in data:
            return jsonify({"error": "Fehlende Base64-Audiodaten"}), 400
        
        audio_base64 = data['audio_base64']
        
        result = stt_from_base64(audio_base64)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        else:
            return jsonify({"transcript": result["transcript"]})

    except Exception as e:
        app.logger.error(f"Backend-Fehler: {e}")
        return jsonify({"error": "Interner Serverfehler während der Verarbeitung"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)