# Autumn preview — troubleshooting

| Symptom | What to do |
|---|---|
| Flexible requests unavailable | Open Ollama and use Check local brain. Only the pinned qwen3:1.7b digest on literal 127.0.0.1:11434 is accepted. Use exact commands while unavailable; there is no cloud fallback. |
| Model missing or verification fails | In Setup and release, check files, space and licenses. Resume the selected artifact or import the exact verified file. Existing unexpected files are preserved under `.replaced-*`; invalid owned partials are retained under `.invalid-*`. A checksum failure never becomes an active model. |
| Download interrupted or no range support | Check internet/free space, then resume. Servers that ignore an existing resume range are refused. Keep a partial for later or use Import from another local models folder. No proxy, HTTP downgrade or arbitrary URL is accepted. |
| No voice or recognition | Check the selected device and pinned model files in Voice setup, then explicitly test. Reconnect a missing device and reselect it. Text remains available; Windows Zira is the default-speaker fallback. Paths without a compatible Windows short name may be refused by the native speech component. |
| Wake cannot arm | Calibration is required: 50 attempts, two hours of household audio and a five-minute CPU window. Device/model/threshold changes invalidate the profile. Keep push-to-talk until it passes. |
| Dictation refused or partial | Check the exact supported non-elevated field and return focus to it before approving. Never automatically retry a partial/uncertain delivery. Inspect the field yourself; native foreground acceptance remains pending. |
| UI appears still | Reduced motion may be on, or the window is inactive. Focus it and check the header motion toggle. The Stop button never moves. Pages scroll when space is limited. |
| Worker interrupted | Stop discards stale work. The app restarts failed workers up to three times, then disables the failing worker. Quit/reopen after fixing the cause; never replay uncertain desktop actions automatically. |
| Settings recovered to defaults | The invalid settings file is preserved in a recovery copy under config. Review capabilities, devices and targets before enabling voice again. Startup always leaves the microphone off. |
| Setup fails or an upgrade leaves old files | Quit Autumn, check 12 GB free and folder permissions, then retry the trusted package. An unmanaged application folder is refused. Unknown or modified old files are retained for your review. Do not blindly delete the whole data folder. |

Stop works without the model or speech. If the UI is unresponsive, close Autumn using Task Manager; owned audio/setup workers are contained, and the action worker checks a pinned handle to its parent process. Review any effect already accepted by Windows before making another request.

The preview executables are not code-signed. Windows security warnings and Defender behavior on another account remain unverified. Verify the release SHA-256 against the local release record; do not disable security protection or add exclusions. A per-user isolated install test does not establish clean-account acceptance.

For support, use the redacted export preview and the recorded gate report. Do not attach recordings, dictated text, personal paths or screenshots containing private data. Full network-isolation, two-hour mixed hardware use, Narrator, physical sleep/resume and battery checks remain pending.
