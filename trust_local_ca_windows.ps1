$ErrorActionPreference = "Stop"
$certificado = Join-Path $PSScriptRoot ".tls\findimob-root-ca.crt"
if (-not (Test-Path -LiteralPath $certificado)) {
    throw "A CA ainda nao foi criada. Inicie o app uma vez e rode este script de novo."
}
$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($certificado)
if ($cert.Subject -ne $cert.Issuer) {
    throw "O certificado fornecido nao e uma CA raiz autoassinada."
}
Import-Certificate -FilePath $certificado -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
Write-Host "CA Find Imob confiada para este usuario do Windows."
Write-Host "Acesse https://findimob.local:8501 ou digite findimob.local:8501."
