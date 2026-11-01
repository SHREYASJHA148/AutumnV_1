# Autumn — opening and hands-free listening

Version 0.7.2 prepares recognition and the female voice during startup, keeps the same speech model, uses faster CPU decoding, and speaks shorter confirmations while retaining full verification details onscreen. The default **Quick replies** timing responds sooner after you stop speaking. If it ends a sentence too early, pause listening and choose **Voice setup → Response timing → Natural pauses** or **Longer pauses**, then save.

Double-click **Autumn** in `C:\adu`. That shortcut opens the updated desktop app and starts the installed local Ollama server if needed. Autumn verifies and warms the pinned qwen3:1.7b brain automatically. The UI shows its progress; the first cold load can take longer than later launches. The app refreshes the warm model while running unless memory saver is selected.

Your requested personal profile enables app discovery and hands-free listening on normal launches. Installed Start Menu apps, packaged Windows apps and App Paths entries become available without approving each newly found app. Previously imported unreviewed entries are enabled by the broad permission; an explicitly reviewed disabled app remains disabled. Common folders are added. Everything runs under your existing Windows account's permissions.

Say **“Autumn, open Spotify”**, **“Autumn, open Calculator”**, or **“Autumn, open Downloads”** in one utterance. Use the exact discovered app name. For another local folder or a supported document, use `open C:\your\complete\path` in the text box, or speak a path that recognition can transcribe exactly. A path is resolved by local application code and passed to the action system as an ID. Supported documents open with their normal Windows application. This opening permission does not implement arbitrary generated scripts or commands.

Minimizing hides the window into the notification area while listening keeps its current setting. Look near the Windows clock, including the overflow arrow. Green means microphone capture is active; amber indicates it is closed while processing, speaking, paused or off. Hover for the exact status. Click the icon to open Autumn; right-click it for Hands-free listening, Stop, Microphone off and Quit.

Hands-free mode processes short English recordings locally and accepts commands addressed to Autumn. Unaddressed speech is discarded without being shown in conversation or saved. Recognition and spoken responses briefly pause listening. Audio is kept in memory; this mode uses more CPU than the separate ONNX wake detector. It is experimental and still needs your microphone/speaker and false-activation trials. The older calibrated “hey jarvis” mode remains separate.

**Stop / Ctrl+Alt+Backspace** pauses hands-free listening and discards unfinished work. **Microphone off** also disables voice. Turn it back on with Hands-free in the header or tray. Lock, sleep and Quit close the microphone; resume does not automatically rearm it. Closing the window follows your existing tray/quit choice.

In **Wake and desktop**, pause listening to edit the launch preferences: start local brain, broad opening permission, and start hands-free listening. Optional Windows login startup is separate, remains opt-in, and its new launcher uses `--login` to keep the microphone off. The shared Ollama service and already-open apps remain running after Autumn quits.

If an app is missing, use Import installed apps or add its exact executable in Apps and folders. Shortcut command-line arguments, network/reparse targets and unsupported file types may be refused. Ambiguous app names require a unique alias. If the brain is unavailable, exact commands remain usable; Check local brain retries without downloading or replacing the pinned model.
