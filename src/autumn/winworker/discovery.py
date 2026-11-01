"""Bounded installed-program metadata and common-folder discovery."""
import hashlib
import os
from pathlib import Path

from autumn.actions.catalog import AppEntry, FolderEntry, validate_app


def app_paths(checkpoint):
    import winreg
    result=[]
    key_name=r'Software\Microsoft\Windows\CurrentVersion\App Paths'
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive,key_name,0,winreg.KEY_READ|view) as root:
                    for index in range(min(winreg.QueryInfoKey(root)[0],500)):
                        if not checkpoint():
                            raise InterruptedError()
                        name=winreg.EnumKey(root,index)
                        try:
                            with winreg.OpenKey(root,name) as item:
                                target=winreg.QueryValueEx(item,'')[0]
                            target=os.path.expandvars(target.strip('"'))
                            entry=validate_app(AppEntry(id='x-'+hashlib.sha256(target.casefold().encode()).hexdigest()[:20],name=Path(name).stem[:80],kind='executable',target=target))
                            result.append(entry)
                        except (OSError,ValueError,AttributeError):
                            continue
            except OSError:
                continue
    return tuple(result)


def common_folders(existing):
    values=list(existing)
    paths={f.path.casefold() for f in values}
    home=Path.home()
    choices=[('desktop','Desktop',home/'Desktop'),('pictures','Pictures',home/'Pictures'),
             ('music','Music',home/'Music'),('videos','Videos',home/'Videos'),
             ('home','Home',home),('c-drive','C drive',Path(os.environ.get('SystemDrive','C:')+'\\'))]
    for identifier,name,path in choices:
        if len(values)>=8:
            break
        if str(path).casefold() not in paths and path.is_dir() and 'auto-'+identifier not in {f.id for f in values}:
            values.append(FolderEntry(id='auto-'+identifier,name=name,path=str(path)))
            paths.add(str(path).casefold())
    return tuple(values)
