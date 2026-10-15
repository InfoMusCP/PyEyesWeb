# Local docs build against a development core. Usage (from anywhere):
#   .\docs\build.ps1            build with warnings as errors, open the result
#   .\docs\build.ps1 -Live      rebuild and reload in the browser on every save (needs sphinx-autobuild)
# The core folder defaults to ..\EyesWebCore\build\Release next to this repository; override it with -Core.
param(
    [string]$Core = (Join-Path $PSScriptRoot "..\..\EyesWebCore\build\Release"),
    [switch]$Live
)
$root = Join-Path $PSScriptRoot ".."
$python = Join-Path $root "..\.venv\Scripts\python.exe"
$env:EYESWEB_CORE_PATH = (Resolve-Path $Core).Path
$env:PYTHONPATH = "$($env:EYESWEB_CORE_PATH);$((Resolve-Path $root).Path)"
$source = Join-Path $PSScriptRoot "."
$out = Join-Path $PSScriptRoot "_build\html"
if ($Live) {
    & $python -m sphinx_autobuild $source $out --open-browser
} else {
    & $python -m sphinx -b html -W --keep-going $source $out
    if ($LASTEXITCODE -eq 0) { Start-Process (Join-Path $out "index.html") }
}
