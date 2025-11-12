import flet as ft
from flet import colors # Expliziter Import des 'colors' Moduls, um Fehler zu beheben.
import httpx
import json
import base64
import os

# --- API Konfiguration ---
# Hinweis: Für ein echtes Produkt müssten Sie einen Google Cloud Speech-to-Text API Key 
# hinterlegen und die Authentifizierung korrekt implementieren. 
GOOGLE_API_KEY = "b14b1464c7591bc3a6d7d374c23d80cd971720d228.09.2025"
GOOGLE_STT_ENDPOINT = f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_API_KEY}"
# --- Ende Konfiguration ---

def main(page: ft.Page):
    page.title = "Flet STT Transcriber V20"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK
    
    # Sicherstellen, dass die App responsive ist
    page.window_width = 400
    page.window_height = 800

    def stt_from_base64(audio_base64: str) -> str:
        """
        Sendet die Base64-kodierte Audiodatei an die Google Speech-to-Text API.
        """
        
        headers = {"Content-Type": "application/json"}
        
        # Annahme: Datei ist WAV (LINEAR16) mit 44100 Hz Sample Rate (typisch für Browser-Aufnahme)
        request_data = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": 44100,
                "languageCode": "de-DE", # Deutsche Sprache erkennen
                "enableAutomaticPunctuation": True,
            },
            "audio": {
                "content": audio_base64
            }
        }

        try:
            # Synchrone API-Anfrage
            response = httpx.post(GOOGLE_STT_ENDPOINT, headers=headers, json=request_data, timeout=30)
            response.raise_for_status() # Löst Fehler bei 4xx/5xx Status aus

            result = response.json()
            
            if result and 'results' in result and result['results']:
                # Extrahiert das wahrscheinlichste Ergebnis
                transcript = result['results'][0]['alternatives'][0]['transcript']
                return transcript
            elif 'error' in result:
                # Zeigt API-Fehler an
                return f"API-Fehler: {result['error'].get('message', 'Unbekannt')}"
            else:
                return "Konnte keine Sprache erkennen (Zu leise oder zu kurz)."
            
        except httpx.RequestError as e:
            # Fehler bei der Verbindung oder beim Timeout
            return f"Verbindungsfehler zur Google API: {e}"
        except Exception as e:
            # Andere Fehler
            return f"Unerwarteter Fehler während der Transkription: {e}"


    def handle_upload_result(e: ft.FilePickerResultEvent):
        """Wird ausgelöst, wenn der Nutzer eine Datei ausgewählt oder eine Audioaufnahme beendet hat."""
        
        # Funktion zum Schließen des Banners
        def hide_banner(e):
            page.banner = None
            page.update()

        # 1. Loading State setzen
        status_text.value = "Transkription läuft... Bitte warten."
        status_text.color = colors.AMBER_400 # Korrigiert
        result_text.value = ""
        transcribe_button.disabled = True
        page.update()

        # 2. Datei verarbeiten
        if e.files:
            file_info = e.files[0]
            
            try:
                # Flet liest die Datei als Bytes ein
                with open(file_info.path, "rb") as audio_file:
                    audio_bytes = audio_file.read()

                # Konvertiert die Bytes in Base64 (erforderlich für Google API)
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                
                # 3. Transkription durchführen
                transcript = stt_from_base64(audio_base64)
                
                # 4. Ergebnis anzeigen
                result_text.value = transcript
                
                if "API-Fehler" in transcript or "Konnte keine Sprache erkennen" in transcript:
                    status_text.value = "Transkriptionsfehler"
                    status_text.color = colors.RED_500 # Korrigiert
                    # Fehlermeldung als Banner anzeigen
                    page.banner = ft.Banner(
                        content=ft.Text("Transkription fehlgeschlagen. Prüfen Sie den API-Schlüssel oder das Audioformat.", color=colors.WHITE), # Korrigiert
                        bgcolor=colors.RED_500, # Korrigiert
                        actions=[ft.TextButton("Schließen", on_click=hide_banner)]
                    )
                    page.open(page.banner)

                else:
                    status_text.value = "Transkription abgeschlossen!"
                    status_text.color = colors.GREEN_500 # Korrigiert
                    # Erfolgsmeldung als Banner anzeigen
                    page.banner = ft.Banner(
                        content=ft.Text("Erfolgreich transkribiert!", color=colors.WHITE), # Korrigiert
                        bgcolor=colors.GREEN_500, # Korrigiert
                        actions=[ft.TextButton("Schließen", on_click=hide_banner)]
                    )
                    page.open(page.banner)


            except Exception as ex:
                status_text.value = f"Fehler bei der Dateiverarbeitung: {ex}"
                status_text.color = colors.RED_500 # Korrigiert
                result_text.value = "Die Datei konnte nicht gelesen oder verarbeitet werden. Bitte prüfen Sie das Format."
                page.banner = ft.Banner(
                    content=ft.Text(f"Kritischer Fehler: {ex}", color=colors.WHITE), # Korrigiert
                    bgcolor=colors.RED_700, # Korrigiert
                    actions=[ft.TextButton("Schließen", on_click=hide_banner)]
                )
                page.open(page.banner)
            
        else:
            status_text.value = "Keine Datei oder Aufnahme ausgewählt."
            status_text.color = colors.YELLOW_500 # Korrigiert

        # 5. UI zurücksetzen
        transcribe_button.disabled = False
        page.update()


    # Dateiauswahl-Objekt initialisieren
    file_picker = ft.FilePicker(on_result=handle_upload_result)
    page.overlay.append(file_picker)
    
    # UI Elemente
    
    title_text = ft.Text(
        "STT für Flet (Render Fix)", 
        size=24, 
        weight=ft.FontWeight.BOLD
    )

    subtitle_text = ft.Text(
        "Nehmen Sie Audio auf oder wählen Sie eine Datei aus, um eine Transkription zu starten.", 
        color=colors.WHITE70 # Korrigiert
    )

    status_text = ft.Text(
        "Bereit zum Transkribieren", 
        color=colors.BLUE_400, # Korrigiert
        size=16,
        weight=ft.FontWeight.W_500
    )

    result_text = ft.TextField(
        multiline=True,
        min_lines=10,
        max_lines=20,
        read_only=True,
        value="",
        label="Transkriptionsergebnis",
        border_color=colors.BLUE_GREY_700, # Korrigiert
        bgcolor=colors.BLUE_GREY_900, # Korrigiert
        height=300
    )

    transcribe_button = ft.FilledButton(
        content=ft.Row([
            ft.Icon(ft.icons.MIC_SHARP, size=24),
            ft.Text("Audio auswählen oder Neu-Aufnahme", size=18)
        ]),
        on_click=lambda _: file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["mp3", "wav", "m4a"], # Erlaubte Audioformate
            # Wichtig: Mobile Browser ermöglichen hier die direkte Aufnahme
        ),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.all(15)
        )
    )

    # Hauptlayout
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    title_text,
                    subtitle_text,
                    ft.Divider(height=30, color=colors.WHITE10), # Korrigiert
                    transcribe_button,
                    ft.Divider(height=30, color=colors.WHITE10), # Korrigiert
                    status_text,
                    ft.Container(height=10),
                    result_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20
            ),
            padding=30,
            border_radius=ft.border_radius.all(15),
            bgcolor=colors.BLUE_GREY_800, # Korrigiert
            width=page.window_width if page.window_width > 400 else 400,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=colors.with_opacity(0.2, colors.BLUE_ACCENT_100), # Korrigiert
                offset=ft.Offset(0, 0),
            ),
        )
    )

# Stellen Sie sicher, dass Flet die App als Web-App startet
if __name__ == "__main__":
    # Render nutzt die Umgebungsvariable $PORT
    port = os.environ.get("PORT")
    ft.app(target=main, view=ft.WEB_BROWSER, port=port)