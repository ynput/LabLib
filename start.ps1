# Receive first positional argument
$FunctionName=$ARGS[0]
$arguments=@()
if ($ARGS.Length -gt 1) {
    $arguments = $ARGS[1..($ARGS.Length - 1)]
}

$poetry_verbosity="-vv"

$current_dir = Get-Location
$repo_root_rel = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$repo_root = (Get-Item $repo_root_rel).FullName


function Default-Func {
    Write-Host ""
    Write-Host "LabLib library"
    Write-Host ""
    Write-Host "Usage: ./start.ps1 [target]"
    Write-Host ""
    Write-Host "Runtime targets:"
    Write-Host "  install                       Install Poetry and update venv by lock file."
    Write-Host "  set-env                        Set all env vars in .env file."
    Write-Host "  get-dependencies               Download and extract all dependencies into vendor folder."
    Write-Host ""
}

function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }
   Restore-Cwd
   exit $exitcode
}

function Install-Poetry() {
    Write-Host ">>> Installing Poetry ... "
    $python = "python"
    if (Get-Command "pyenv" -ErrorAction SilentlyContinue) {
        if (-not (Test-Path -PathType Leaf -Path "$($repo_root)\.python-version")) {
            $result = & pyenv global
            if ($result -eq "no global version configured") {
                Write-Host "!!! ", "Using pyenv but having no local or global version of Python set."
                Exit-WithCode 1
            }
        }
        $python = & pyenv which python
    }

    $env:POETRY_HOME="$repo_root\.poetry"
    $env:POETRY_VERSION="1.3.2"
    (Invoke-WebRequest -Uri https://install.python-poetry.org/ -UseBasicParsing).Content | & $($python) -
}

function Change-Cwd() {
    Set-Location -Path $repo_root
}

function Restore-Cwd() {
    Set-Location -Path $current_dir
}

function install {
    # install dependencies for tool
     if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
        Install-Poetry
    }

    Change-Cwd

    Write-Host ">>> ", "Poetry config ... "
    & "$env:POETRY_HOME\bin\poetry" install --no-interaction --no-root --ansi  $poetry_verbosity
}

function set_env {
    # set all env vars in .env file
    if ((Test-Path "$($repo_root)\.env")) {
        Write-Host "!!! ", ".env file must be prepared!" -ForegroundColor red
        $content = Get-Content -Path "$($repo_root)\.env" -Encoding UTF8 -Raw
        foreach($line in $content.split()) {
            if ($line){
                $parts = $line.split("=")
                $varName = $parts[0]
                $value = $parts[1]
                Write-Host "Setting $varName with $value"
                Set-Item "env:$varName" $value
            }
        }
        $env:PYTHONPATH=$repo_root
    }
}

function get_dependencies {
    $vendor_root = "$repo_root\vendor"
    if (-not (Test-Path -Path $vendor_root)) {
        New-Item -ItemType Directory -Path $vendor_root
    }

    # ensure OpenImageIO
    if (-not (Test-Path "$vendor_root\oiio\windows\oiiotool.exe")) {
        $oiio_url = "https://www.patreon.com/file?h=63609827&i=10247677"
        $oiio_zip = "$vendor_root\oiiotools2.3.10.zip"
        Invoke-WebRequest -Uri $oiio_url -OutFile $oiio_zip
        Expand-Archive -Path $oiio_zip -DestinationPath "$vendor_root\oiio\windows"
    }

    # ensure OpenColorIO Config
    if (-not (Test-Path "$vendor_root\ocioconfig")) {
        $ocio_url = "https://github.com/colour-science/OpenColorIO-Configs/releases/download/v1.2/OpenColorIO-Config-ACES-1.2.zip"
        $ocio_zip = "$vendor_root\OpenColorIO-Config-ACES-1.2.zip"
        Invoke-WebRequest -Uri $ocio_url -OutFile $ocio_zip
        Expand-Archive -Path $ocio_zip -DestinationPath "$vendor_root\ocioconfig"
    }

    # ensure FFMPEG
    if (-not (Test-Path "$vendor_root\ffmpeg")) {
        $ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/7.0.1/ffmpeg-7.0.1-full_build-shared.zip"
        $ffmpeg_zip = "$vendor_root\ffmpeg-7.0.1-full_build-shared.zip"
        Invoke-WebRequest -Uri $ffmpeg_url -OutFile $ffmpeg_zip
        Expand-Archive -Path $ffmpeg_zip -DestinationPath "$vendor_root\ffmpeg"
    }

    # ensure Source Code Pro font
    if (-not (Test-Path "$vendor_root\font")) {
        $font_url = "https://api.fontsource.org/v1/download/source-code-pro"
        $font_zip = "$vendor_root\source-code-pro.zip"
        Invoke-WebRequest -Uri $font_url -OutFile $font_zip
        Expand-Archive -Path $font_zip -DestinationPath "$vendor_root\font"
    }
}

function main {
    if ($FunctionName -eq $null)
    {
        Default-Func
        return
    }
    $FunctionName = $FunctionName.ToLower() -replace "\W"
    if ($FunctionName -eq "install") {
        Change-Cwd
        install
    } elseif ($FunctionName -eq "test") {
        Change-Cwd
        set_env
        & "$env:POETRY_HOME\bin\poetry" run pytest -x --capture=sys -W ignore::DeprecationWarning @arguments
    } elseif ($FunctionName -eq "setenv") {
        Change-Cwd
        set_env
    } elseif ($FunctionName -eq "getdependencies") {
        Change-Cwd
        get_dependencies
    }else {
        Write-Host "Unknown function \"$FunctionName\""
        Default-Func
    }
    Restore-Cwd
}

# Force POETRY_HOME to this directory
$env:POETRY_HOME = "$repo_root\.poetry"

main
