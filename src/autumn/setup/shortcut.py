"""Create a clickable native launcher and preserve any unrelated existing link."""
from pathlib import Path


def create_shortcut(executable,link,icon=None):
    from win32com.client.dynamic import Dispatch

    from autumn.actions.catalog import no_reparse

    executable=Path(executable).resolve(strict=True)
    link=Path(link)
    no_reparse(link.parent)
    if link.exists() or link.is_symlink():
        no_reparse(link)
    shell=Dispatch('WScript.Shell')
    if link.exists():
        old=shell.CreateShortcut(str(link))
        if Path(old.TargetPath).resolve()!=executable or old.Arguments.strip():
            raise ValueError('An unrelated launcher already exists')
    shortcut=shell.CreateShortcut(str(link))
    shortcut.TargetPath=str(executable)
    shortcut.WorkingDirectory=str(executable.parent)
    shortcut.IconLocation=str(icon or executable)+',0'
    shortcut.Description='Open Autumn, start her local brain and your saved hands-free mode'
    shortcut.Save()
    return link
