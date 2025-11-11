import flet as ft
import speech_recognition as sr
import os
import asyncio

# Globale Variablen
r = sr.Recognizer()

def main(page: ft.Page):
    # Deprecation Warnings ignorieren wir
    page.title = "Flet STT Transkriptor (Stabil)"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    # --- UI-Elemente ---
    # WICHTIG: KEINE ID MEHR hier, um den TypeError zu vermeiden
    status_text = ft.Text("Bereit für Audio-Verarbeitung.")
    result_text = ft.Text("Transkription erscheint hier.", color=ft.colors.BLUE_ACCENT_700)
    
    live_mic_button = ft.ElevatedButton(
        "🎧 Audio auswählen oder Neu-Aufnahme",
        icon=ft.icons.MIC,
        on_click=None, # Wird unten definiert
    )

    # --- Transkriptionslogik (Nimmt Controls als Argumente entgegen) ---
    async def transcribe_audio(file_path: str, button: ft.Control, status: ft.Text, result: ft.Text):
        
        # 1. UI auf Verarbeitung umstellen
        button.disabled = True
        status.value = "Verarbeite Audio. Bitte warten..."
        page.update()

        transcription = "..."
        try:
            # 2. Öffne die Audiodatei
            with sr.AudioFile(file_path) as source:
                status.value = f"Sende {os.path.basename(file_path)} zur Transkription..."
                page.update()
                
                # 3. Audio einlesen
                audio = r.record(source) 
                
                # 4. BLOCKIERENDEN AUFRUF in separaten Thread verschieben! (ASYNCHRON)
                transcription = await asyncio.to_thread(r.recognize_google, audio, language="de-DE")
        
        except sr.UnknownValueError:
            transcription = "Konnte das Audio nicht verstehen. Sprechen Sie bitte deutlicher."
        except sr.RequestError as error:
            transcription = f"Fehler bei der Verbindung zur Google API: {error}"
        except Exception as error:
            # Wenn MP4 ohne FFMPEG hochgeladen wird, kommt hier meist der Fehler
            transcription = f"Ein Fehler ist aufgetreten: {error}" 

        # 5. Ergebnis anzeigen und Zustand zurücksetzen
        button.disabled = False
        status.value = "Transkription abgeschlossen. Bereit für neue Verarbeitung."
        result.value = transcription
        page.update()
        
        # Optional: Lösche die temporäre Datei
        try:
            os.remove(file_path)
        except:
            pass
            
    # --- FilePicker Logik (Innerhalb von main, um die Controls zu sehen) ---
    def file_picker_result(e: ft.FilePickerResultEvent):
        # Der Button wird hier wieder aktiviert, falls die Auswahl abgebrochen wurde
        live_mic_button.disabled = False
        page.update()
        
        if e.files:
            # Starte die Transkription als asynchrone TASK
            # Wir übergeben die Controls direkt an die Funktion
            page.run_task(
                transcribe_audio(
                    file_path=e.files[0].path, 
                    button=live_mic_button, 
                    status=status_text, 
                    result=result_text
                )
            )
        else:
            # Auswahl abgebrochen
            status_text.value = "Auswahl/Aufnahme abgebrochen."
            page.update()


    file_picker = ft.FilePicker(on_result=file_picker_result)
    page.overlay.append(file_picker)

    def live_mic_click(e):
        # Deaktiviere den Button, solange der Dialog offen ist
        e.control.disabled = True
        page.update()
        
        file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["wav", "mp3", "ogg", "flac", "mp4"] 
        )
    
    # on_click des Buttons zuweisen, nachdem live_mic_click definiert ist
    live_mic_button.on_click = live_mic_click

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Flet STT Transkriptor", size=30, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text(
                        "Auf dem Handy öffnet dieser Button den Dateidialog, in dem Sie 'Audio aufnehmen' können.", 
                        color=ft.colors.RED_500, 
                        text_align=ft.TextAlign.CENTER
                    ),
                    status_text,
                    ft.Container(height=20),
                    live_mic_button,
                    ft.Container(height=40),
                    ft.Text("Ergebnis:", weight=ft.FontWeight.BOLD),
                    ft.Card(
                        content=ft.Container(
                            result_text, 
                            padding=15,
                            width=page.width * 0.8
                        ),
                        elevation=5
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=30,
            alignment=ft.alignment.center
        )
    )

# Startet die App automatisch im Browser (stabiler Modus für diese Funktion)
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8555)