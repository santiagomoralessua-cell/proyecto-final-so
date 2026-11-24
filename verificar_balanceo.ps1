# Envía 30 peticiones a Nginx y cuenta qué servidor respondió cada una.
# Uso (PowerShell, dentro de la carpeta del proyecto):  .\verificar_balanceo.ps1
# Si Windows lo bloquea: powershell -ExecutionPolicy Bypass -File .\verificar_balanceo.ps1
1..30 | ForEach-Object {
    (curl.exe -sI http://localhost:8080/ | Select-String '^X-Backend').Line.Trim()
} | Group-Object | Select-Object Count, Name | Format-Table -AutoSize
