"""Lightweight translations for the AppleCalls GUI."""

from __future__ import annotations


TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "app_title": "AppleCalls",
        "app_subtitle": (
            "Diagnostico para saber si tu PC con Windows puede usar las llamadas "
            "de tu iPhone por la via soportada y para dejar claro por que no "
            "puede replicar el modo nativo de la Mac por Wi-Fi."
        ),
        "language": "Idioma",
        "status_loading": "Ejecutando diagnostico",
        "status_installing": "Preparando Phone Link",
        "status_ready": "Ruta soportada disponible",
        "status_partial": "Posible, pero falta configuracion",
        "status_blocked": "No esta listo",
        "summary_loading": (
            "Comprobando Windows, Phone Link, Bluetooth y red. La interfaz sigue "
            "respondiendo mientras termina el diagnostico."
        ),
        "summary_installing": (
            "Intentando abrir o reparar Phone Link sin mostrar el instalador "
            "interactivo."
        ),
        "summary_ready": (
            "Tu equipo cumple con lo basico para usar llamadas del iPhone en "
            "Windows mediante Microsoft Phone Link. Eso no equivale al relay "
            "nativo de llamadas de la Mac."
        ),
        "summary_install_phone_link": (
            "La integracion puede funcionar, pero primero debes instalar o "
            "actualizar Microsoft Phone Link."
        ),
        "summary_external_bluetooth_audio": (
            "Phone Link esta conectado, pero Windows aun detecta audio Bluetooth "
            "externo en la PC y eso puede bloquear el popup para contestar llamadas."
        ),
        "summary_missing_calling_profile": (
            "Phone Link esta instalado, pero Windows no expone todavia el "
            "perfil Bluetooth de manos libres necesario para llamadas."
        ),
        "summary_calls_not_exposed": (
            "Phone Link esta instalado, pero su estado local no expone aun la "
            "pantalla de llamadas para este iPhone."
        ),
        "summary_missing_bluetooth": (
            "Sin Bluetooth activo no podras hacer ni recibir llamadas del iPhone "
            "en Windows."
        ),
        "summary_old_windows": (
            "La version de Windows es demasiado antigua para la ruta soportada de "
            "Phone Link."
        ),
        "summary_non_windows": (
            "Esta app diagnostica la ruta de Windows. La funcion nativa de Apple "
            "para llamadas sigue siendo exclusiva del ecosistema Apple."
        ),
        "note_direct_api": (
            "Python no puede replicar por si solo la funcion de Continuity de Mac "
            "porque Apple no expone esa API privada en Windows."
        ),
        "note_ios_requirement": (
            "Phone Link para iPhone requiere iOS 15 o superior y permisos de "
            "Bluetooth habilitados."
        ),
        "note_mac_scope": (
            "En Apple, las llamadas por Continuity siguen ligadas a Mac, iPad y "
            "Vision Pro con la misma Apple Account y la misma red."
        ),
        "note_forwarding_option": (
            "Si quieres una solucion mas independiente, la alternativa real es "
            "desviar llamadas a un numero VoIP o SIP."
        ),
        "note_calls_button": (
            "Si el iPhone ya aparece conectado, prueba abrir la vista "
            "Llamadas directamente desde este diagnostico para validar el flujo real."
        ),
        "note_disconnect_bt_headset": (
            "Desconecta o apaga en la PC cualquier audifono o headset Bluetooth "
            "externo y deja como audio de comunicaciones los altavoces y microfono locales."
        ),
        "note_same_network_not_enough": (
            "Aunque iPhone y PC esten en la misma red Wi-Fi, Windows no puede "
            "recibir llamadas al estilo Mac porque Apple no publica ese relay "
            "para Windows."
        ),
        "note_bt_required": (
            "Windows necesita Bluetooth operativo para que Phone Link pueda tomar "
            "y hacer llamadas."
        ),
        "note_windows_requirement": (
            "Microsoft documenta que Phone Link necesita al menos Windows 10 May "
            "2019 Update o una version mas reciente."
        ),
        "refresh": "Ejecutar diagnostico",
        "open_phone_link": "Abrir Phone Link",
        "open_calls": "Abrir llamadas",
        "install_phone_link": "Instalar o actualizar Phone Link",
        "open_bluetooth": "Abrir Bluetooth",
        "open_ms_guide": "Guia Microsoft",
        "open_apple_guide": "Guia Apple",
        "copy_report": "Copiar reporte",
        "donate": "Comprame una cerveza",
        "diagnostic_panel": "Reporte tecnico",
        "actions_panel": "Acciones rapidas",
        "guide_panel": "Pasos sugeridos",
        "limitations_panel": "Limites reales",
        "copied_title": "Reporte copiado",
        "copied_message": "El reporte fue copiado al portapapeles.",
        "error_title": "No se pudo completar la accion",
        "install_title": "Instalacion de Phone Link",
        "install_success": (
            "Phone Link quedo disponible. La app intentara abrirse ahora."
        ),
        "install_in_progress": (
            "La instalacion o actualizacion de Phone Link ya esta en curso."
        ),
        "install_failed": (
            "No se pudo instalar o actualizar Phone Link automaticamente."
        ),
        "open_after_install_failed": (
            "Phone Link quedo instalado o actualizado, pero no se pudo abrir automaticamente."
        ),
        "launcher_not_ready": (
            "El lanzador directo de Phone Link todavia no esta disponible."
        ),
        "install_details": "Detalle tecnico",
        "loading_notes": (
            "- Consultando version de Windows.\n\n"
            "- Revisando Phone Link.\n\n"
            "- Enumerando Bluetooth y red."
        ),
        "installing_notes": (
            "- Intentando abrir el ejecutable real de Phone Link.\n\n"
            "- Si falla, se ejecuta winget en modo silencioso.\n\n"
            "- Al terminar, se vuelve a comprobar la instalacion."
        ),
        "loading_report": "Generando reporte tecnico...",
        "installing_report": "Trabajando con Phone Link...",
        "guide_text": (
            "1. Si quieres la ruta soportada en Windows, empareja el iPhone con "
            "la PC por Bluetooth.\n"
            "2. Abre Microsoft Phone Link en la PC.\n"
            "3. Sigue el asistente para conectar iPhone.\n"
            "4. En el iPhone, permite acceso a Bluetooth y sincronizacion de "
            "contactos.\n"
            "5. Usa el boton Abrir llamadas para ir directo al panel que debe "
            "permitir contestar o iniciar llamadas.\n"
            "6. Si tu objetivo es un flujo por Wi-Fi sin Bluetooth, la opcion "
            "real no es Apple Continuity en Windows sino desvio de llamadas a "
            "VoIP/SIP.\n"
            "7. Si Phone Link falla, actualizalo desde Microsoft Store."
        ),
        "limitations_text": (
            "- Esto no clona la funcion privada de llamadas de macOS.\n"
            "- La ruta soportada en Windows depende de Phone Link y Bluetooth.\n"
            "- Estar en la misma Wi-Fi no desbloquea Continuity en Windows.\n"
            "- La calidad y estabilidad dependen del adaptador Bluetooth, del "
            "estado del iPhone y de la app de Microsoft.\n"
            "- Para una experiencia totalmente separada del iPhone, tendrias que "
            "usar desvio de llamadas a VoIP."
        ),
        "status_label": "Resultado",
        "notes_label": "Notas clave",
        "phone_link_missing": (
            "Phone Link no parece instalado. Instalala primero desde Microsoft "
            "Store."
        ),
        "voip_section_title": "Telefono SIP (independiente)",
        "voip_section_intro": (
            "Alternativa independiente a Phone Link: registra una cuenta SIP/VoIP "
            "real (por ejemplo, con desvio de llamadas desde tu iPhone) y haz o "
            "recibe llamadas directamente desde Windows por el estandar SIP, sin "
            "Bluetooth y sin depender de Microsoft ni de Apple."
        ),
        "voip_field_server": "Servidor SIP",
        "voip_field_port": "Puerto del servidor",
        "voip_field_username": "Usuario",
        "voip_field_password": "Contrasena",
        "voip_field_display_number": "Numero a mostrar",
        "voip_save_connect": "Guardar y conectar",
        "voip_disconnect": "Desconectar",
        "voip_connect_missing_fields": (
            "Completa al menos servidor, usuario y contrasena antes de conectar."
        ),
        "voip_status_label": "Estado del registro SIP",
        "voip_status_inactive": "Sin conexion",
        "voip_status_registering": "Registrando cuenta SIP...",
        "voip_status_registered": "Cuenta SIP registrada",
        "voip_status_deregistering": "Cerrando el registro SIP...",
        "voip_status_failed": "El registro SIP fallo",
        "voip_call_state_label": "Llamada",
        "voip_call_state_idle": "Sin llamada activa",
        "voip_call_state_dialing": "Marcando...",
        "voip_call_state_ringing": "Timbrando",
        "voip_call_state_answered": "En llamada",
        "voip_call_state_ended": "Llamada finalizada",
        "voip_dial_label": "Numero a llamar",
        "voip_call_button": "Llamar",
        "voip_hangup_button": "Colgar",
        "voip_active_call_label": "Llamada activa",
        "voip_call_duration_label": "Duracion",
        "voip_incoming_call_title": "Llamada entrante",
        "voip_incoming_call_from": "Numero entrante",
        "voip_answer": "Contestar",
        "voip_decline": "Rechazar",
        "voip_no_dtmf_note": (
            "Esta version solo puede recibir tonos DTMF, no enviarlos durante la "
            "llamada. El teclado numerico sirve para componer el numero antes de "
            "llamar, no como teclado de tonos en vivo."
        ),
        "voip_error_title": "Telefono SIP",
        "voip_error_not_connected": "Conecta la cuenta SIP antes de marcar.",
        "voip_password_store_failed": (
            "No se pudo guardar la contrasena en el almacen seguro de Windows. "
            "La conexion puede continuar, pero tendras que escribirla de nuevo la "
            "proxima vez."
        ),
        "voip_credential_store_unavailable": (
            "El almacen de credenciales de Windows no esta disponible en este "
            "equipo."
        ),
        "voip_saved_notice": "Datos de la cuenta SIP guardados.",
    },
    "en": {
        "app_title": "AppleCalls",
        "app_subtitle": (
            "Diagnostic utility to check whether your Windows PC can use your "
            "iPhone calls through the supported path and to explain why it "
            "cannot replicate the Mac Wi-Fi relay behavior."
        ),
        "language": "Language",
        "status_loading": "Running diagnostics",
        "status_installing": "Preparing Phone Link",
        "status_ready": "Supported path available",
        "status_partial": "Possible, but setup is incomplete",
        "status_blocked": "Not ready",
        "summary_loading": (
            "Checking Windows, Phone Link, Bluetooth, and network status. The UI "
            "stays responsive while diagnostics are running."
        ),
        "summary_installing": (
            "Trying to open or repair Phone Link without showing the interactive "
            "installer."
        ),
        "summary_ready": (
            "Your system meets the basic requirements to use iPhone calls on "
            "Windows through Microsoft Phone Link. That is still not the same as "
            "the native Mac call relay."
        ),
        "summary_install_phone_link": (
            "The integration can work, but you first need to install or update "
            "Microsoft Phone Link."
        ),
        "summary_external_bluetooth_audio": (
            "Phone Link is connected, but Windows still detects external "
            "Bluetooth audio on the PC and that can block the incoming-call answer popup."
        ),
        "summary_missing_calling_profile": (
            "Phone Link is installed, but Windows is not exposing the "
            "hands-free Bluetooth profile required for calls yet."
        ),
        "summary_calls_not_exposed": (
            "Phone Link is installed, but its local runtime state is not yet "
            "exposing the calls screen for this iPhone."
        ),
        "summary_missing_bluetooth": (
            "Without active Bluetooth, you will not be able to make or receive "
            "iPhone calls on Windows."
        ),
        "summary_old_windows": (
            "Your Windows version is too old for the supported Phone Link path."
        ),
        "summary_non_windows": (
            "This app diagnoses the Windows path. Apple's native calling relay "
            "still belongs to the Apple ecosystem."
        ),
        "note_direct_api": (
            "Python cannot reproduce Mac Continuity calling on its own because "
            "Apple does not expose that private API on Windows."
        ),
        "note_ios_requirement": (
            "Phone Link for iPhone requires iOS 15 or newer and Bluetooth "
            "permissions enabled."
        ),
        "note_mac_scope": (
            "On Apple's side, Continuity calling still targets Mac, iPad, and "
            "Vision Pro on the same Apple Account and network."
        ),
        "note_forwarding_option": (
            "If you need a more independent desktop solution, the practical "
            "alternative is call forwarding to a VoIP or SIP number."
        ),
        "note_calls_button": (
            "If the iPhone already shows as connected, try opening the Calls "
            "view directly from this diagnostic app to validate the real flow."
        ),
        "note_disconnect_bt_headset": (
            "Disconnect or power off any external Bluetooth headset on the PC and "
            "leave local speakers and microphone as the communications audio path."
        ),
        "note_same_network_not_enough": (
            "Even if the iPhone and PC are on the same Wi-Fi network, Windows "
            "cannot receive Continuity calls like a Mac because Apple does not "
            "publish that relay for Windows."
        ),
        "note_bt_required": (
            "Windows needs working Bluetooth so Phone Link can place and receive "
            "calls."
        ),
        "note_windows_requirement": (
            "Microsoft documents that Phone Link needs at least Windows 10 May "
            "2019 Update or something newer."
        ),
        "refresh": "Run diagnostics",
        "open_phone_link": "Open Phone Link",
        "open_calls": "Open calls",
        "install_phone_link": "Install or update Phone Link",
        "open_bluetooth": "Open Bluetooth",
        "open_ms_guide": "Microsoft guide",
        "open_apple_guide": "Apple guide",
        "copy_report": "Copy report",
        "donate": "Buy me a beer",
        "diagnostic_panel": "Technical report",
        "actions_panel": "Quick actions",
        "guide_panel": "Suggested steps",
        "limitations_panel": "Real limitations",
        "copied_title": "Report copied",
        "copied_message": "The report was copied to the clipboard.",
        "error_title": "The action could not be completed",
        "install_title": "Phone Link installation",
        "install_success": (
            "Phone Link is now available. The app will try to open it now."
        ),
        "install_in_progress": (
            "The Phone Link installation or upgrade is already running."
        ),
        "install_failed": (
            "Phone Link could not be installed or upgraded automatically."
        ),
        "open_after_install_failed": (
            "Phone Link was installed or updated, but it could not be opened automatically."
        ),
        "launcher_not_ready": (
            "The direct Phone Link launcher is not available yet."
        ),
        "install_details": "Technical details",
        "loading_notes": (
            "- Checking the Windows version.\n\n"
            "- Inspecting Phone Link.\n\n"
            "- Enumerating Bluetooth and network state."
        ),
        "installing_notes": (
            "- Trying the real Phone Link launcher first.\n\n"
            "- If that fails, winget runs in silent mode.\n\n"
            "- When it finishes, the app checks installation state again."
        ),
        "loading_report": "Generating technical report...",
        "installing_report": "Working on Phone Link...",
        "guide_text": (
            "1. If you want the supported Windows path, pair the iPhone with the "
            "PC over Bluetooth.\n"
            "2. Open Microsoft Phone Link on the PC.\n"
            "3. Follow the assistant to connect your iPhone.\n"
            "4. On the iPhone, allow Bluetooth access and contact sync.\n"
            "5. Use the Open calls button to jump directly to the panel that "
            "should allow answering or starting calls.\n"
            "6. If your target is a Wi-Fi-only flow without Bluetooth, the real "
            "option is call forwarding to VoIP/SIP rather than Apple Continuity "
            "on Windows.\n"
            "7. If Phone Link fails, update it from Microsoft Store."
        ),
        "limitations_text": (
            "- This does not clone the private macOS calling feature.\n"
            "- The supported Windows path depends on Phone Link and Bluetooth.\n"
            "- Being on the same Wi-Fi does not unlock Continuity on Windows.\n"
            "- Call quality and stability depend on the Bluetooth adapter, the "
            "iPhone state, and the Microsoft app.\n"
            "- For a fully independent desktop calling flow, you would need call "
            "forwarding to VoIP."
        ),
        "status_label": "Result",
        "notes_label": "Key notes",
        "phone_link_missing": (
            "Phone Link does not appear to be installed. Install it from the "
            "Microsoft Store first."
        ),
        "voip_section_title": "SIP phone (independent)",
        "voip_section_intro": (
            "An independent alternative to Phone Link: register a real SIP/VoIP "
            "account (for example, with call forwarding from your iPhone) and make "
            "or receive calls straight from Windows over the SIP standard, with no "
            "Bluetooth and no dependency on Microsoft or Apple."
        ),
        "voip_field_server": "SIP server",
        "voip_field_port": "Server port",
        "voip_field_username": "Username",
        "voip_field_password": "Password",
        "voip_field_display_number": "Display number",
        "voip_save_connect": "Save and connect",
        "voip_disconnect": "Disconnect",
        "voip_connect_missing_fields": (
            "Fill in at least the server, username, and password before connecting."
        ),
        "voip_status_label": "SIP registration status",
        "voip_status_inactive": "Not connected",
        "voip_status_registering": "Registering the SIP account...",
        "voip_status_registered": "SIP account registered",
        "voip_status_deregistering": "Closing the SIP registration...",
        "voip_status_failed": "SIP registration failed",
        "voip_call_state_label": "Call",
        "voip_call_state_idle": "No active call",
        "voip_call_state_dialing": "Dialing...",
        "voip_call_state_ringing": "Ringing",
        "voip_call_state_answered": "On call",
        "voip_call_state_ended": "Call ended",
        "voip_dial_label": "Number to call",
        "voip_call_button": "Call",
        "voip_hangup_button": "Hang up",
        "voip_active_call_label": "Active call",
        "voip_call_duration_label": "Duration",
        "voip_incoming_call_title": "Incoming call",
        "voip_incoming_call_from": "Incoming number",
        "voip_answer": "Answer",
        "voip_decline": "Decline",
        "voip_no_dtmf_note": (
            "This version can only receive DTMF tones, not send them during a "
            "call. The number pad is for composing the number before you call, "
            "not a live in-call touch-tone keypad."
        ),
        "voip_error_title": "SIP phone",
        "voip_error_not_connected": "Connect the SIP account before dialing.",
        "voip_password_store_failed": (
            "The password could not be saved to the Windows secure credential "
            "store. The connection can still proceed, but you will need to type "
            "it again next time."
        ),
        "voip_credential_store_unavailable": (
            "The Windows credential store is not available on this machine."
        ),
        "voip_saved_notice": "SIP account details saved.",
    },
}


def get_text(language: str, key: str) -> str:
    """Returns a translated string with English fallback."""

    if language in TRANSLATIONS and key in TRANSLATIONS[language]:
        return TRANSLATIONS[language][key]
    return TRANSLATIONS["en"].get(key, key)
