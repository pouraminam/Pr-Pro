' Premiere AI Editor - Silent Background Launcher for Windows
Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run Chr(34) & strPath & "\start_engine.bat" & Chr(34), 0, False
Set WshShell = Nothing
