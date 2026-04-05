$ErrorActionPreference = "Stop"

$checks = @(
  "http://127.0.0.1:8100/api/v1/health",
  "http://127.0.0.1:3300"
)

foreach ($url in $checks) {
  try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    Write-Output ("{0} -> {1}" -f $url, $response.StatusCode)
  } catch {
    Write-Warning ("{0} -> FAILED: {1}" -f $url, $_.Exception.Message)
  }
}
