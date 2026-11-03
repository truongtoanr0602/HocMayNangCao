param([switch]$OpenBrowser)

$ErrorActionPreference = 'Stop'
$neo4jHome = Join-Path $env:LOCALAPPDATA 'Programs/Neo4j/neo4j-community-5.26.32'
$neo4jScript = Join-Path $neo4jHome 'bin/neo4j.ps1'
$browserUrl = 'http://localhost:7474/browser/'

if (-not (Test-Path -LiteralPath $neo4jScript)) {
    throw "Neo4j is not installed at $neo4jHome"
}

function Test-Neo4jReady {
    try {
        # Check IPv4 directly: Windows PowerShell can time out on localhost's IPv6 address.
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:7474/browser/' -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

if (-not (Test-Neo4jReady)) {
    $env:NEO4J_HOME = $neo4jHome
    $neo4jArguments = @('-NoProfile', '-NonInteractive', '-File', ('"{0}"' -f $neo4jScript), 'console')
    Start-Process -FilePath 'powershell.exe' -ArgumentList $neo4jArguments `
        -WorkingDirectory $neo4jHome -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $neo4jHome 'logs/console-output.log') `
        -RedirectStandardError (Join-Path $neo4jHome 'logs/console-error.log') | Out-Null

    $neo4jDeadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $neo4jDeadline -and -not (Test-Neo4jReady)) {
        Start-Sleep -Seconds 1
    }
    if (-not (Test-Neo4jReady)) {
        throw "Neo4j is not ready. Check $neo4jHome/logs/console-error.log"
    }
}

Write-Output "Neo4j Browser: $browserUrl"
Write-Output 'Connect to bolt://localhost:7687, user neo4j. Password: NEO4J_PASSWORD in the project .env.'
if ($OpenBrowser) {
    Start-Process $browserUrl
}
