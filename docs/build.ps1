# Local docs build against a development core. Usage (from anywhere):
#   .\docs\build.ps1 -Core <core build>          build with warnings as errors, open the result
#   .\docs\build.ps1 -Core <core build> -Live    rebuild and reload in the browser on every save (needs sphinx-autobuild)
# <core build> is the folder of a development build of the compiled core; without -Core, EYESWEB_CORE_PATH is used.
# Python is the virtual environment next to the repository (..\.venv), else the python on the PATH.
param(
    [string]$Core = $env:EYESWEB_CORE_PATH,
    [switch]$Live
)
if (-not $Core) { throw "Give the folder of a development build of the core with -Core (or set EYESWEB_CORE_PATH)." }
$root = Join-Path $PSScriptRoot ".."
$python = Join-Path $root "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
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
