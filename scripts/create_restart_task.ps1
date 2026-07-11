param(
    [int]$DelayMinutes = 60,
    [string]$TaskName = "AutoRestartTask"
)

$ErrorActionPreference = "Stop"

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " Windows Restart Task Creator" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "Project Path:" -ForegroundColor Yellow -NoNewline
    Write-Host " $PSScriptRoot"
    Write-Host "Task Name:" -ForegroundColor Yellow -NoNewline
    Write-Host " $TaskName"
    Write-Host "Delay Minutes:" -ForegroundColor Yellow -NoNewline
    Write-Host " $DelayMinutes"
    Write-Host ""

    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if ($null -ne $existingTask) {
        Write-Host "[INFO] Existing task found. Removing old task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Start-Sleep -Seconds 1
        Write-Host "[OK] Old task removed." -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] No existing task found." -ForegroundColor DarkGray
    }

    # Create trigger time
    $runAt = (Get-Date).AddMinutes($DelayMinutes)

    # Create task trigger and action
    $trigger = New-ScheduledTaskTrigger -Once -At $runAt
    $action = New-ScheduledTaskAction -Execute "shutdown.exe" -Argument "/r /t 30"

    # Register task
    Register-ScheduledTask -TaskName $TaskName -Trigger $trigger -Action $action -Force | Out-Null

    Write-Host ""
    Write-Host "[OK] Task created successfully." -ForegroundColor Green

    # Read task info
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

    Write-Host ""
    Write-Host "========== TASK INFO ==========" -ForegroundColor Cyan
    Write-Host ("Task Name      : {0}" -f $TaskName)
    Write-Host ("Next Run Time  : {0}" -f $taskInfo.NextRunTime)
    Write-Host ("Last Run Time  : {0}" -f $taskInfo.LastRunTime)
    Write-Host ("Last TaskResult: {0}" -f $taskInfo.LastTaskResult)
    Write-Host "Action         : shutdown.exe /r /t 30"
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "[WARNING] The computer will restart at the scheduled time." -ForegroundColor Magenta
    Write-Host "[NOTE] This version does NOT force close apps, but Windows may still ask to close open programs." -ForegroundColor Yellow
    Write-Host ""

    Write-Host "To remove the task manually, run:" -ForegroundColor Yellow
    Write-Host "Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false" -ForegroundColor White
}
catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to create restart task." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
