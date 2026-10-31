"""Conservative version 1 boundaries; ambiguous or unsupported input never dispatches."""
import re

from autumn.brain.contracts import Clarification, Unsupported


def capabilities_question(text: str) -> bool:
    return bool(re.search(r"\b(capabilities|abilities|features|help)\b|what.*(?:can.*you|you.*do)|which.*(?:actions|jobs|tasks|things)|what.*(?:actions|tasks|support)",text.casefold()))


def input_guard(text: str):
    value=text.casefold()
    if re.search(r"\b(delete|erase|wipe|rename|shutdown|reboot|restart|sleep|hibernate|install|uninstall|download|upload|email|send|compose|type|paste|click|scroll|drag|submit|buy|pay|purchase|schedule|remind|close|password|credentials|administrator|admin|elevated|powershell|terminal|shell|playlist|album|artist|weather|bluetooth|brightness|wallpaper)\b|\bwi-?fi\b|\bcmd(?:\.exe)?\b|[;`|]|\b(?:copy|move|edit|write|read|summari[sz]e|analy[sz]e)\b.*\b(?:files?|folders?|documents?|pdfs?|screen)\b",value):
        return Unsupported(message="That operation is outside the supported version 1 capabilities.")
    if re.search(r"\b(?:show|do|open|find)\b.*\b(?:that thing|this thing|something|that one|it)\b",value):
        return Clarification(message="Please name the registered target or give a filename fragment.",choices=())
    if re.search(r"\b(?:play|start|pause|resume|stop)\b.*\b(?:music|song|track|video|playback)\b",value) and not re.search(r"\b(toggle|next|previous|skip)\b|play[ /]pause",value):
        return Clarification(message="I can toggle the current media session. Use ‘play pause’, ‘next track’ or ‘previous track’.",choices=())
    if re.match(r"\s*(?:who|why|when|tell me|what is|what's)\b",value) and not capabilities_question(value):
        return Unsupported(message="General conversation and knowledge answers are not enabled.")
    return None
