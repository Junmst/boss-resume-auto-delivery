$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'BOSS_Auto_Delivery.lnk'
$s = $ws.CreateShortcut($shortcutPath)
$s.TargetPath = 'D:\apps\boss简历自动投递\启动配置页面.vbs'
$s.WorkingDirectory = 'D:\apps\boss简历自动投递'
$s.IconLocation = 'shell32.dll,130'
$s.Save()
Write-Output "Shortcut created: $shortcutPath"
