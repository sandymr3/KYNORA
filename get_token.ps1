# Firebase Token Generator - PowerShell Script
# Usage: .\get_token.ps1 [admin|user|custom] [options]

param(
    [string]$Type = "admin",
    [string]$Uid = "",
    [string]$Email = "",
    [string]$Role = "user",
    [string]$Claims = "",
    [string]$Output = "",
    [string]$Verify = "",
    [switch]$Help
)

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Firebase Authentication Token Generator" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

if ($Help) {
    Write-Host "Usage Examples:" -ForegroundColor Yellow
    Write-Host "  .\get_token.ps1                                    - Generate admin token"
    Write-Host "  .\get_token.ps1 -Type admin                        - Generate admin token"
    Write-Host "  .\get_token.ps1 -Type user -Uid user123            - Generate user token"
    Write-Host "  .\get_token.ps1 -Type custom -Uid custom123        - Generate custom token"
    Write-Host "  .\get_token.ps1 -Verify 'your-token-here'          - Verify a token"
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -Type       : Token type (admin, user, custom)"
    Write-Host "  -Uid        : User ID"
    Write-Host "  -Email      : Email address"
    Write-Host "  -Role       : User role (default: user)"
    Write-Host "  -Claims     : Additional claims as JSON string"
    Write-Host "  -Output     : Output file to save token"
    Write-Host "  -Verify     : Token to verify"
    Write-Host "  -Help       : Show this help message"
    Write-Host ""
    exit
}

# Build command arguments
$args = @("utils\get_token.py")

if ($Verify) {
    $args += "--verify", $Verify
} else {
    $args += "--type", $Type
    
    if ($Uid) { $args += "--uid", $Uid }
    if ($Email) { $args += "--email", $Email }
    if ($Role -and $Type -eq "user") { $args += "--role", $Role }
    if ($Claims) { $args += "--claims", $Claims }
    if ($Output) { $args += "--output", $Output }
}

# Execute the Python script
try {
    Write-Host "Executing: python $($args -join ' ')" -ForegroundColor Gray
    Write-Host ""
    
    & python @args
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Token generation completed successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Token generation failed!" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error executing token generator: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
