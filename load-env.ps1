# Usage: .\load-env.ps1  (from repo root)
Get-Content .\.env | ForEach-Object {
    if ($_ -match '^\s*#') { return }              
    if ($_ -match '^\s*$') { return }              
    $kv = $_ -split '=', 2
    $name = $kv[0].Trim()
    $value = $kv[1].Trim().Trim('"')
    Set-Item -Path "Env:$name" -Value $value
  }
  Write-Host "Loaded .env for this session."
  