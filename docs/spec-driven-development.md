# Spec-Driven Development

## Product intent

Build a Windows desktop utility in Python that gives the user a real,
independent way to make and receive their iPhone calls from a PC, and that
is honest about what is and is not technically possible along the way.

## Investigation history (read before proposing "just remove Phone Link")

This project went through three rounds of live, on-hardware investigation
before landing on the current architecture. Each round is recorded here so
the same infeasible request does not get re-attempted blind in the future.

1. **Bluetooth Hands-Free (HFP) AT channel.** Windows claims this channel
   for its own in-box driver (`BTAGService`, surfaced in Device Manager as
   `iPhone Hands-Free HF`) the moment a phone is paired, before any
   third-party app -- including Phone Link -- ever runs. A third-party app
   cannot open its own RFCOMM session to the same profile without disabling
   that system driver, which would also kill the existing Hands-Free audio
   endpoints.
2. **BLE ANCS (Apple Notification Center Service).** This is a public,
   documented Apple accessory protocol (used by generic Bluetooth
   smartwatches to show/accept/decline calls), so it looked promising.
   Tested twice on real hardware: once against an iPhone paired through
   Phone Link's own flow, and once again after a full unpair/re-pair done
   entirely through Windows Settings with Phone Link never opened. Both
   times, the ANCS service was invisible to a generic third-party BLE GATT
   client (confirmed via direct service discovery). Windows Registry
   evidence (`Microsoft.YourPhone_8wekyb3d8bbwe!YourPhoneNotifications_com.apple.mobilephone`)
   confirms Phone Link is registered as the exclusive first-party consumer
   of this channel at the OS level, regardless of who performed the pairing.
3. **macOS Continuity Calls over Wi-Fi.** Investigated with a full
   multi-source research pass (100+ sub-queries, adversarial source
   verification). Verdict: not feasible for a third party, with
   medium-to-high confidence. Continuity Calls' signaling (ringing,
   pickup/hangup) is delivered through Apple's APNs/IDS push
   infrastructure -- an Apple ID-authenticated, Apple-server-validated
   channel -- before any Wi-Fi peer-to-peer audio starts. No academic paper
   or open-source project has reimplemented this relay; the one academic
   reference that reverse-engineered other Continuity protocols in depth
   (TU Darmstadt SEEMOO, USENIX Security '21) explicitly scoped Calls out of
   its work. Everywhere Apple's Continuity trust model has been broken open,
   participation required Apple-signed long-term keys or credentials
   extracted from a genuine, already-authenticated Apple device -- never
   independently generated ones.

Conclusion: on Windows, neither Bluetooth (HFP or BLE/ANCS) nor a Wi-Fi
replica of Apple's private relay gives a third-party app a supported way to
carry real iPhone calls. The one mechanism that is genuinely open, documented,
and does not depend on Apple or Microsoft at all is standards-based
SIP/VoIP telephony -- which is what this app now implements.

## Core constraint (superset of the original one)

- Apple's native Continuity calling flow is private to the Apple ecosystem,
  authenticated through Apple's own push infrastructure. Windows does not
  expose a supported API for a third-party program to participate in it,
  and no known research has changed that.
- Windows does not expose the Bluetooth Hands-Free AT channel or the BLE
  ANCS channel for a paired iPhone to third-party applications either --
  both are claimed by the OS/Phone Link's first-party integration
  regardless of how the device was paired.

That makes the following non-goals, permanently:

- Re-implement Apple's private Mac call relay (Continuity Calls) on Windows.
- Read or control iPhone call state through the Bluetooth HFP AT channel or
  BLE ANCS without Microsoft's first-party OS integration.

## Supported scope

### SIP/VoIP softphone (`applecalls/voip.py`) -- the independent path

- Register a real SIP (RFC 3261) account against any standard SIP/VoIP
  provider the user chooses (server, port, username, password, display
  number).
- Detect and surface incoming calls (caller number from the SIP `From`
  header), with answer/decline actions.
- Place outbound calls to a dialed number.
- Bridge real two-way audio (G.711 PCMU/PCMA at 8kHz) between the call and
  the PC's microphone/speakers.
- Never block the Tkinter main thread: SIP registration, call signaling,
  and the audio bridge all run on background threads and report back
  through the same queue+`after()` polling idiom used by the diagnostics
  panel.
- Store the SIP password only in the OS credential store (Windows
  Credential Manager via `keyring`), never in the on-disk JSON account
  config, never logged.
- Best-effort, idempotent, silent Windows Firewall rule creation for the
  SIP/RTP ports so incoming calls are not silently dropped.
- Only ever track one call at a time; a second incoming call while one is
  already active is answered with SIP busy rather than silently orphaning
  the first one.

Known, accepted limitation: the SIP library in use (`pyVoIP` 1.6.8) can only
*receive* DTMF tones, not send them during an active call. There is no
in-call touch-tone keypad; the numeric entry is for composing the number
before dialing only.

Real-world setup this assumes: the user forwards their real iPhone number
(via their carrier's call-forwarding feature) to their SIP/VoIP account's
DID number. This app does not configure carrier-side call forwarding --
that is done through the carrier or VoIP provider directly.

### Phone Link diagnostics (legacy, still supported, unchanged)

- Diagnose whether the Windows-supported Phone Link path is available.
- Inspect Windows version, Phone Link, Bluetooth, and local network state.
- Inspect whether Phone Link already exposes its local Calls entry point
  for the connected iPhone.
- Distinguish generic Bluetooth availability from the hands-free profile
  required for call control.
- Detect external Bluetooth audio devices that can prevent Phone Link from
  presenting an answer-call UI.
- Explain the technical limitation clearly.
- Provide a stable GUI that does not freeze during diagnostics.
- Produce a reproducible Windows `.exe`.

This panel is kept for users who still want the Phone Link path; it is not
required for and does not interact with the SIP softphone.

## Quality requirements

- Keep current features working -- the SIP softphone is additive, the
  Phone Link diagnostics panel must keep working exactly as before.
- Avoid blocking the GUI thread with shell diagnostics, SIP registration,
  SIP signaling, firewall rule setup, or audio I/O. Every one of these runs
  on a background thread and reports back through a queue polled via
  `self.after(...)`.
- Keep PowerShell, netsh, and winget helpers silent when launched from the
  GUI (`applecalls.process_utils.merge_hidden_process_kwargs`).
- Fail gracefully when PowerShell or netsh commands return incomplete data,
  when the SIP server is unreachable, when no audio device is available, or
  when the OS credential store is unavailable (e.g. headless CI).
- Never persist the SIP password outside the OS credential store; never log
  it, never let it reach an exception message shown to the user.
- Keep version strings aligned between source, README, build artifact, tag,
  and commit.
- Any new runtime dependency must be declared in `requirements.txt` and
  justified in `docs/dependencies.md` (see the "no runtime deps unless
  clearly needed" policy there -- SIP/RTP protocol handling, audio device
  I/O, and secure credential storage are the accepted exceptions).

## Acceptance criteria

- The GUI launches without crashing on Windows 11, including with the new
  `pyVoIP`/`sounddevice`/`keyring` imports bundled into the frozen `.exe`
  (verified: PyInstaller's `sounddevice` hook and the Windows `keyring`
  backend are both picked up automatically, no manual `--hidden-import`
  needed).
- Running diagnostics keeps the window responsive.
- Saving a SIP account and connecting never freezes the window, even while
  the firewall rules are being created or the SIP server is slow/unreachable.
- An incoming SIP call is announced (caller number, window raised, audible
  cue) and can be answered or declined from the GUI.
- An outbound SIP call can be placed and hung up from the GUI.
- Closing the window during an active call/registration tears things down
  within a bounded time and never hangs indefinitely.
- The report includes Windows, Phone Link, Bluetooth, and network details.
- The report includes whether Phone Link exposes the Calls view and whether
  a Bluetooth hands-free profile is present.
- The report identifies external Bluetooth audio blockers when they are
  likely to interfere with incoming-call handling.
- The app explicitly states that same-Wi-Fi alone does not unlock
  Mac-style Continuity calling on Windows, and that Bluetooth (HFP/ANCS)
  does not either.
- The GUI can open Phone Link directly into the Calls experience when
  Windows exposes that route.
- Background shell helpers do not flash visible CMD or PowerShell windows.
- The project can generate an `.exe` in the project root using the local
  `.ico`.
