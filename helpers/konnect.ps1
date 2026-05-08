# Retrieves and parses running Kathara devices
function kdevices {
    # docker ps --format json outputs one JSON object per line on modern Docker versions.
    $dockerOutput = docker ps -f "name=^kathara_.+$" --format json
    
    if ([string]::IsNullOrWhiteSpace($dockerOutput)) { return }

    $dockerOutput | ConvertFrom-Json | ForEach-Object {
        $deviceName = ""
        # PowerShell regex matching with named capture group
        if ($_.Names -match '^kathara_.*_(?<device>\w+)_.+$') {
            $deviceName = $Matches['device']
        }
        
        # Output a clean object mimicking the Nushell table row
        [PSCustomObject]@{
            ID      = $_.ID
            Command = $_.Command
            Image   = $_.Image
            Names   = $_.Names
            State   = $_.State
            device  = $deviceName
        }
    }
}

# Connects to a specific device's Docker container.
function konnect {
    <#
    .SYNOPSIS
    Connects to a specific device's Docker container.
    
    .DESCRIPTION
    This command searches for a running Docker container whose name 
    matches the pattern `_<device>_` and drops you into an interactive 
    bash session inside that container.
    #>
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true, Position=0)]
        [string]$device
    )

    # Build the regex filter string
    $filter = "name=^kathara_.+_${device}_.+$"
    $container = (docker ps -q -f $filter).Trim()

    if ([string]::IsNullOrWhiteSpace($container)) {
        Write-Host "Error: Device '$device' not found or container is not running." -ForegroundColor Red
    } else {
        # Execute interactive bash session
        docker exec -ti $container /bin/bash
    }
}

# Register the tab autocompletion for the 'konnect' command
Register-ArgumentCompleter -CommandName konnect -ParameterName device -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)

    # Fetch devices and filter them based on what the user has typed so far
    $devices = kdevices | Where-Object { $_.device -like "$wordToComplete*" }
    
    foreach ($row in $devices) {
        $description = "$($row.Command) in ($($row.Image))"
        
        # CompletionResult takes: CompletionText, ListItemText, ResultType, ToolTip
        [System.Management.Automation.CompletionResult]::new(
            $row.device,
            $row.device,
            'ParameterValue',
            $description
        )
    }
}