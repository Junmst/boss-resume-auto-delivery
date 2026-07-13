@echo off
chcp 65001 >nul
set "VBS_FILE=%~dp0启动配置页面.vbs"
set "SHORTCUT_NAME=BOSS自动投递-配置页面"

:: 获取桌面路径
for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul') do set "DESKTOP=%%b"
if not defined DESKTOP set "DESKTOP=%USERPROFILE%\Desktop"

:: 创建快捷方式
powershell -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%.lnk'); $s.TargetPath = '%VBS_FILE%'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = 'shell32.dll,130'; $s.Description = 'BOSS直聘自动投递工具 - 配置管理'; $s.Save()"

echo.
echo ✅ 桌面快捷方式已创建！
echo    名称: %SHORTCUT_NAME%
echo    位置: %DESKTOP%
echo.
echo 双击桌面上的快捷方式即可打开配置页面。
echo.
pause
