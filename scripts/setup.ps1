param(
    [ValidateSet('gemini', 'ollama')]
    [string]$Provider = 'gemini',
    [string]$AdminEmail = 'svarsha.t@gmail.com',
    [string]$CircularUrl = 'https://fci.gov.in/circular',
    [switch]$ApiKeyLater
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    Write-Host 'Existing .env preserved. Edit it to change providers or credentials.'
    exit 0
}

function New-RandomSecret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

$apiKey = ''
if ($Provider -eq 'gemini' -and -not $ApiKeyLater) {
    $secureKey = Read-Host 'Gemini API key (hidden; use a project with billing disabled)' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try { $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    if ($apiKey -notmatch '^[A-Za-z0-9_-]+$') { throw 'A valid Gemini API key is required for Gemini mode.' }
}
$adminEmail = $AdminEmail
if ($adminEmail -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$') { throw 'Enter a valid email address.' }
$circularUrl = $CircularUrl
if (-not $circularUrl) { $circularUrl = 'https://fci.gov.in/' }
$parsedUrl = [Uri]$circularUrl
if ($parsedUrl.Scheme -ne 'https' -or ($parsedUrl.Host -ne 'fci.gov.in' -and -not $parsedUrl.Host.EndsWith('.fci.gov.in'))) {
    throw 'Use an HTTPS URL on fci.gov.in.'
}
$values = @(
    "POSTGRES_PASSWORD=$(New-RandomSecret)",
    "JWT_SECRET=$(New-RandomSecret)",
    "LLM_PROVIDER=$Provider",
    "GEMINI_API_KEY=$apiKey",
    'GEMINI_MODEL=gemini-2.5-flash',
    'OLLAMA_MODEL=qwen3:4b',
    "CRAWLER_ADMIN_EMAILS=$adminEmail",
    "FCI_CIRCULAR_URLS=$circularUrl"
)
[IO.File]::WriteAllLines($envPath, $values, (New-Object Text.UTF8Encoding($false)))
$apiKey = $null
Write-Host 'Configuration ready. Secrets are stored only in the ignored root .env file.'
Write-Host 'Start: docker compose up --build -d'
if ($Provider -eq 'ollama') {
    Write-Host 'Also start local AI: docker compose --profile local-ai up -d ollama'
    Write-Host 'Download the model: docker compose exec ollama ollama pull qwen3:4b'
}
