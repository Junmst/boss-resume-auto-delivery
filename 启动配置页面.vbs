' BOSS Auto Delivery configuration page launcher
Option Explicit

Dim shell, fso, scriptDir, pythonw, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = scriptDir & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(pythonw) Then
    MsgBox "Project virtual environment was not found. Create .venv and install requirements.txt first.", 16, "BOSS Auto Delivery"
    WScript.Quit 1
End If

command = Chr(34) & pythonw & Chr(34) & " " & Chr(34) & scriptDir & "\gui.py" & Chr(34)
shell.Run command, 0, False
