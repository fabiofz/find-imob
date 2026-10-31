$ErrorActionPreference = "Stop"
$identidade = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identidade)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw "Abra o PowerShell como administrador e execute novamente." }
$raiz = $PSScriptRoot
$iniciador = Join-Path $raiz "iniciar_findimob_windows.ps1"
if (-not (Test-Path -LiteralPath $iniciador)) { throw "Arquivo nao encontrado: $iniciador" }
$nomeTarefa = "Find Imob - iniciar painel e rede"
$acao = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $iniciador" -WorkingDirectory $raiz
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User $identidade.Name
$configuracao = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
$conta = New-ScheduledTaskPrincipal -UserId $identidade.Name -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName $nomeTarefa -Action $acao -Trigger $gatilho -Settings $configuracao -Principal $conta -Description "Inicia o Find Imob no WSL e atualiza o acesso pela rede local ao entrar no Windows." -Force | Out-Null
$arquivoHosts = Join-Path $env:WINDIR "System32\drivers\etc\hosts"
$conteudoHosts = Get-Content -LiteralPath $arquivoHosts -Raw
if ($conteudoHosts -notmatch '(?im)^\s*127\.0\.0\.1\s+findimob\.local(?:\s|$)') { Add-Content -LiteralPath $arquivoHosts -Value ([Environment]::NewLine + "127.0.0.1 findimob.local") -Encoding ascii }
Write-Host "Inicializacao automatica instalada para $($identidade.Name)."
Write-Host "No computador: https://findimob.local:8501"
Write-Host "Em celulares, findimob.local exige DNS/mDNS configurado na rede."
