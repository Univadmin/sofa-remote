# Run as the current user after installing dependencies. No administrator required.
$project = Split-Path $PSScriptRoot -Parent
$python = Join-Path $project '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Once scripts/start-windows.cmd dosyasini calistirin.' }
$startup = [Environment]::GetFolderPath('Startup')
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $startup 'Sofa Remote.lnk'))
$shortcut.TargetPath = $python
$shortcut.Arguments = '-m server.app'
$shortcut.WorkingDirectory = $project
$shortcut.Save()
Write-Host 'Otomatik baslatma acildi. Kaldirmak icin Baslangic klasorundeki Sofa Remote kisayolunu silin.'
