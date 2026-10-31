$ErrorActionPreference = "Stop"
$projetoWsl = "/home/fabiofz/projetos/find-imob"
$comandoLinux = "cd '$projetoWsl' && nohup ./start_app.sh >/tmp/findimob-streamlit.log 2>&1 </dev/null &"
& wsl.exe -d Ubuntu -- bash -lc $comandoLinux
if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel iniciar o painel no WSL." }
& "$PSScriptRoot\permitir_acesso_rede.ps1"
if ($LASTEXITCODE -ne 0) { throw "O painel iniciou, mas o encaminhamento de rede falhou." }
