[CmdletBinding()]
param (
  [ValidateSet('frontend', 'backend', 'all')]
  [string]$Scope = 'all'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendDirectory = Join-Path (Join-Path $repositoryRoot 'fuego') 'fuego-frontend'
$manageScript = Join-Path (Join-Path $repositoryRoot 'fuego') 'manage.py'

if ($env:OS -eq 'Windows_NT') {
  $python = Join-Path (Join-Path (Join-Path $repositoryRoot '.venv') 'Scripts') 'python.exe'
} else {
  $python = Join-Path (Join-Path $repositoryRoot '.venv') 'bin/python'
}

function Invoke-Check {
  param (
    [string]$Name,
    [scriptblock]$Command
  )

  Write-Host "`n== $Name =="
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE."
  }
}

if ($Scope -eq 'frontend' -or $Scope -eq 'all') {
  Invoke-Check 'Frontend tests' { npm --prefix $frontendDirectory test }
  Invoke-Check 'Frontend type check and production build' { npm --prefix $frontendDirectory run build }
}

if ($Scope -eq 'backend' -or $Scope -eq 'all') {
  if (-not (Test-Path $python)) {
    throw "Project virtual-environment Python was not found at '$python'."
  }

  Invoke-Check 'Django system checks' { & $python $manageScript check }
  Invoke-Check 'Django migration consistency' { & $python $manageScript makemigrations --check --dry-run }
  Invoke-Check 'Django chat and community tests' {
    & $python $manageScript test chat community
  }
}

Invoke-Check 'Git whitespace check' { git -C $repositoryRoot diff --check }
Write-Host "`nFuego validation passed for scope '$Scope'."
