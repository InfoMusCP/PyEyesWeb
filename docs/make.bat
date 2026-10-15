@ECHO OFF
pushd %~dp0
if "%SPHINXBUILD%" == "" set SPHINXBUILD=python -m sphinx
if "%SPHINXOPTS%" == "" set SPHINXOPTS=-W --keep-going
if "%1" == "" goto help
%SPHINXBUILD% -M %1 . _build %SPHINXOPTS% %O%
goto end
:help
%SPHINXBUILD% -M help . _build %SPHINXOPTS% %O%
:end
popd
