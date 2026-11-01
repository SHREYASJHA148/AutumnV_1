"""Fast native matches for ordinary phrasing in explicitly enabled general mode."""
import re

from autumn.actions.router import route


def native_route(text, settings):
    direct = route(text,settings)
    if direct.plan is not None or not settings.master_control:
        return direct
    # Only remove bounded courtesy/addressing wrappers, never arbitrary trailing instructions.
    command = text.strip()
    command = re.sub(r'(?i)^(?:hey[\s,]+)?autumn\b[\s,:-]+','',command)
    command = re.sub(r'(?i)^(?:(?:please|can you|could you|would you|will you|i want you to|i need you to)\s+)+','',command)
    command = re.sub(r'(?i)(?:[,\s]+(?:please|for me|now))+[.?!]*$','',command).strip().rstrip('.?!')
    # The frozen router still validates the COMPLETE remaining command and exact unique target.
    result = route(command,settings)
    if result.plan is not None:
        return result
    launch = re.fullmatch(r'(?i)(open|launch|start)\s+(?:the|my)\s+(.+)',command)
    return route(launch[1]+' '+launch[2],settings) if launch else direct
