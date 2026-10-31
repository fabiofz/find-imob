$ErrorActionPreference = "Stop"

$identidade = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identidade)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Abra o PowerShell como administrador e execute este script novamente."
}

$saidaWsl = & wsl.exe -d Ubuntu -- hostname -I
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível consultar o IP atual do WSL."
}
$ipWsl = ($saidaWsl -split "\s+" | Where-Object { $_ -match '^\d{1,3}(?:\.\d{1,3}){3}$' } | Select-Object -First 1)
if (-not $ipWsl) {
    throw "O WSL não retornou um endereço IPv4 válido."
}

netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8501 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8501 connectaddress=$ipWsl connectport=8501
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível encaminhar a porta 8501 para $ipWsl."
}

Get-NetFirewallRule -DisplayName "Find Imob Streamlit 8501" -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
New-NetFirewallRule `
    -DisplayName "Find Imob Streamlit 8501" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 8501 `
    -Profile Private `
    -RemoteAddress LocalSubnet | Out-Null

$ipHospedeiro = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -eq "Wi-Fi" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1 -ExpandProperty IPAddress

Write-Host "Encaminhamento ativo na porta 8501 para o IP WSL $ipWsl"
Write-Host "Acesso com HTTPS: https://findimob.local:8501"
if ($ipHospedeiro) { Write-Host "IPv4 deste computador: $ipHospedeiro" }
Write-Host "Para celulares, configure o DNS local para findimob.local apontar para o IPv4 deste PC e instale a CA .tls/findimob-root-ca.crt."
Write-Host "Se o WSL reiniciar e trocar de IP, execute este script novamente."
