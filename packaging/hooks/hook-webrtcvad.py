"""The installed binary wheel exposes webrtcvad but owns webrtcvad-wheels metadata."""
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("webrtcvad-wheels")
hiddenimports = ["_webrtcvad"]
