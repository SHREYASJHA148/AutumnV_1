"""Owner-authorized discovery and explicit local paths; model arguments remain IDs."""
import hashlib
import re
from pathlib import Path

from autumn.actions.catalog import AppEntry, FolderEntry, no_reparse, validate_app
from autumn.actions.router import Routing
from autumn.actions.schemas import AppArgs, FolderArgs, OpenApp, OpenFolder, Plan

DOCUMENT_EXTENSIONS = frozenset('.txt .pdf .png .jpg .jpeg .gif .bmp .webp .mp3 .mp4 .wav .mkv .avi .mov .flac .doc .docx .xls .xlsx .ppt .pptx .csv .rtf .odt .ods .odp .md .html .htm .zip'.split())


def authorize_discovered(previous, discovered, enabled):
    result={entry.id:entry for entry in previous}
    names={entry.name.casefold() for entry in previous}
    for entry in discovered:
        # Explicit per-app disable still wins after the broad initial permission.
        if enabled and entry.id in result:
            previous_entry=result[entry.id]
            if (not previous_entry.reviewed or previous_entry.enabled) and previous_entry.target.casefold()==entry.target.casefold():
                result[entry.id]=entry.model_copy(update={'enabled':True,'reviewed':True,'name':previous_entry.name,'aliases':previous_entry.aliases})
        if entry.id not in result and entry.name.casefold() not in names:
            result[entry.id]=entry.model_copy(update={'enabled':True,'reviewed':True}) if enabled else entry
            names.add(entry.name.casefold())
    return tuple(result.values())[:500]


def direct_open(text,settings):
    """Compile an entire explicit local path, never a fragment of generated output."""
    if not settings.broad_open_access:
        return None,settings
    match=re.fullmatch(r'(?i)(?:open|launch|start)\s+(.+)',text.strip())
    if not match:
        return None,settings
    target=match[1].strip()
    if len(target)>=2 and target[0]==target[-1]=='"':
        target=target[1:-1]
    if not re.match(r'^[A-Za-z]:[\\/]',target):
        return None,settings
    if any(ord(c)<32 for c in target) or any(c in target for c in '|<>`'):
        return Routing(message='Use one complete local path without extra instructions.'),settings
    try:
        path=no_reparse(Path(target))
        identifier='direct-'+hashlib.sha256(str(path).encode()).hexdigest()[:20]
        if path.is_dir():
            entry=FolderEntry(id=identifier,name=path.name or path.anchor,path=str(path))
            compiled=settings.model_copy(update={'folders':(*settings.folders,entry)})
            action=OpenFolder(arguments=FolderArgs(folder_id=identifier))
        else:
            entry=validate_app(AppEntry(id=identifier,name=(path.name[:80] or 'Local file'),kind='executable' if path.suffix.casefold()=='.exe' else 'file',target=str(path),enabled=True,reviewed=True))
            compiled=settings.model_copy(update={'apps':(*settings.apps,entry)})
            action=OpenApp(arguments=AppArgs(app_id=identifier))
        if action.skill not in settings.enabled_skills:
            return Routing(message='This opening capability is disabled in Settings.'),settings
        return Routing(plan=Plan(steps=(action,)),message=''),compiled
    except (OSError,ValueError):
        return Routing(message='That local target is missing, inaccessible or unsupported. Check the exact path.'),settings
