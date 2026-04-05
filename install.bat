@echo off
chcp 65001 >nul
title Process Cloner v1.0.3 — Instalador

echo.
echo   ██████╗ ██╗      ██████╗ ███╗  ██╗███████╗██████╗
echo  ██╔════╝ ██║     ██╔═══██╗████╗ ██║██╔════╝██╔══██╗
echo  ██║      ██║     ██║   ██║██╔██╗██║█████╗  ██████╔╝
echo  ██║      ██║     ██║   ██║██║╚████║██╔══╝  ██╔══██╗
echo  ╚██████╗ ███████╗╚██████╔╝██║ ╚███║███████╗██║  ██║
echo   ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚══╝╚══════╝╚═╝  ╚═╝
echo.
echo   Process Cloner v1.0.5 — Instalador Windows
echo   -------------------------------------------
echo.

:: ── Verifica se é instalação limpa (Bootstrap) ──
IF NOT EXIST "cloner.py" (
    echo [0/5] Preparando diretorio oculto de instalacao...
    IF NOT EXIST "%USERPROFILE%\.chatburguer" mkdir "%USERPROFILE%\.chatburguer"
    cd /d "%USERPROFILE%\.chatburguer"

    echo [1/5] Baixando Process Cloner do Servidor Oficial...
    curl -fsSL "https://github.com/Nilsonbarbozza/chatburguer-app/releases/latest/download/process-cloner.zip" -o cloner.zip
    IF EXIST "cloner.zip" (
        powershell -Command "Expand-Archive cloner.zip -DestinationPath . -Force"
        del cloner.zip
        echo   OK: Arquivos extraidos com sucesso na pasta .chatburguer.
    ) ELSE (
        echo   ERRO: Falha ao baixar o arquivo ZIP da versao 1.0.5.
        pause
        exit /b 1
    )
    echo.
)

:: ── Verifica Python ──
echo [1/4] Verificando Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo  ERRO: Python nao encontrado.
    echo  Instale em: https://www.python.org/downloads/
    echo  IMPORTANTE: Marque "Add Python to PATH" durante instalacao!
    pause
    exit /b 1
)
FOR /F "tokens=*" %%i IN ('python --version') DO echo   OK: %%i

:: ── Instala dependências Python ──
echo.
echo [2/4] Instalando dependencias Python...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
IF %ERRORLEVEL% EQU 0 (
    echo   OK: Dependencias instaladas
) ELSE (
    echo   AVISO: Algumas dependencias falharam. Verifique manualmente.
)

:: ── Verifica Node.js ──
echo.
echo [3/4] Verificando ferramentas Node.js ^(opcionais^)...
node --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    FOR /F "tokens=*" %%i IN ('node --version') DO echo   OK: Node.js %%i

    call npm install -g prettier >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (echo   OK: prettier instalado) ELSE (echo   AVISO: prettier nao instalado)

    call npm install -g lightningcss >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (echo   OK: lightningcss instalado) ELSE (echo   AVISO: lightningcss nao instalado)

    call npm install -g purgecss >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (echo   OK: purgecss instalado) ELSE (echo   AVISO: purgecss nao instalado)
) ELSE (
    echo   AVISO: Node.js nao encontrado. Otimizacoes CSS serao puladas.
    echo   Instale em: https://nodejs.org
)

:: ── Cria .env ──
echo.
echo [4/4] Configurando ambiente...
IF NOT EXIST ".env" (
    copy .env.example .env >nul
    echo   OK: Arquivo .env criado
) ELSE (
    echo   OK: .env ja existe
)

:: ── Cria pastas ──
IF NOT EXIST "output" mkdir output
IF NOT EXIST "logs"   mkdir logs

:: ── Atalho Global ──
echo.
echo [5/5] Configurando comando global 'cloner'...
IF EXIST "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps" (
    echo @python "%cd%\cloner.py" %%* > "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\cloner.bat"
    echo   OK: Comando global criado com sucesso!
) ELSE (
    echo   AVISO: Pasta WindowsApps nao encontrada. Adicione \%cd\% ao seu PATH.
)

:: ── Finalização ──
echo.
echo ==========================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ==========================================
echo.
echo   Para usar, execute no terminal em qualquer lugar:
echo     cloner
echo.
echo   Ou arraste um arquivo HTML para o terminal:
echo     cloner --file seu_arquivo.html
echo.
pause



