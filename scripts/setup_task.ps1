$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"D:\ai-signal\scripts\run_hidden.vbs`""
$trigger = New-ScheduledTaskTrigger -Daily -At "8:30AM"
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "MacroSignalAutoDigest" -Description "Auto generate and push Macro Signal digest at 8:30 AM" -Force
