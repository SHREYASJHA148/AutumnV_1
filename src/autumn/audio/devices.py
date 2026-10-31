"""Read-only device metadata. Names/API hashes are stable when the driver exposes them."""

import hashlib


def enumerate_devices():
    import sounddevice as sd

    apis = sd.query_hostapis()
    rows = []
    for index, device in enumerate(sd.query_devices()):
        api = apis[device["hostapi"]]["name"]
        for kind, key in (("input", "max_input_channels"), ("output", "max_output_channels")):
            if device[key] < 1:
                continue
            fingerprint = f"{kind}|{api}|{device['name']}"
            token = hashlib.sha256(fingerprint.encode()).hexdigest()[:24]
            rows.append(
                {
                    "id": token,
                    "index": index,
                    "name": device["name"],
                    "api": api,
                    "kind": kind,
                    "label": device["name"] + " · " + api,
                    "rate": int(device["default_samplerate"]),
                }
            )
    return rows


def resolve_device(token, kind):
    import sounddevice as sd

    rows = enumerate_devices()
    if not token:
        index = int(sd.default.device[0 if kind == "input" else 1])
        matches = [row for row in rows if row["kind"] == kind and row["index"] == index]
    else:
        matches = [row for row in rows if row["kind"] == kind and row["id"] == token]
    if len(matches) != 1:
        raise ValueError("Device missing or ambiguous; select again")
    return matches[0]


def default_endpoint(kind):
    try:
        from pycaw.pycaw import AudioUtilities

        return (
            AudioUtilities.GetMicrophone() if kind == "input" else AudioUtilities.GetSpeakers()
        ).id
    except Exception:
        return None
