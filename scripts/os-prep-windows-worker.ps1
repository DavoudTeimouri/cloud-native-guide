#requires -RunAsAdministrator
# OS preparation script — Windows Server worker node role
# Applies Windows-specific preparation for Kubernetes worker nodes
# Run from an elevated PowerShell prompt

$ErrorActionPreference = "Stop"
$LogFile = "C:\os-prep-windows-worker.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "o"
    "$timestamp | os-prep-windows-worker: $Message" | Tee-Object -FilePath $LogFile -Append
}

Write-Log "Starting Windows worker node preparation"

# ---------- 1. Windows Update from internal WSUS ----------
Write-Log "Configuring Windows Update from internal WSUS"
$wsusServer = "http://wsus.internal:8530"
$registryPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"
New-Item -Path $registryPath -ErrorAction SilentlyContinue
Set-ItemProperty -Path $registryPath -Name "WUServer" -Value $wsusServer
Set-ItemProperty -Path $registryPath -Name "WUStatusServer" -Value $wsusServer
Set-ItemProperty -Path $registryPath -Name "TargetGroupEnabled" -Value 1 -Type DWord
Set-ItemProperty -Path $registryPath -Name "TargetGroupName" -Value "KubernetesWorkers"

$auPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
New-Item -Path $auPath -ErrorAction SilentlyContinue
Set-ItemProperty -Path $auPath -Name "NoAutoUpdate" -Value 0 -Type DWord
Set-ItemProperty -Path $auPath -Name "AUOptions" -Value 4 -Type DWord  # Scheduled install
Set-ItemProperty -Path $auPath -Name "ScheduledInstallDay" -Value 0 -Type DWord  # Every day
Set-ItemProperty -Path $auPath -Name "ScheduledInstallTime" -Value 3 -Type DWord  # 3 AM

Write-Log "Windows Update configured"

# ---------- 2. Install containerd ----------
Write-Log "Installing containerd"
$containerdVersion = "1.7.0"
$containerdUrl = "https://github.com/containerd/containerd/releases/download/v${containerdVersion}/containerd-${containerdVersion}-windows-amd64.tar.gz"
$containerdDir = "C:\Program Files\containerd"

if (-not (Test-Path $containerdDir)) {
    New-Item -ItemType Directory -Path $containerdDir -Force
    Invoke-WebRequest -Uri $containerdUrl -OutFile "$env:TEMP\containerd.tar.gz"
    tar -xzf "$env:TEMP\containerd.tar.gz" -C $containerdDir
}

# Add containerd to PATH
$existingPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)
if (-not $existingPath.Contains("containerd")) {
    [Environment]::SetEnvironmentVariable("Path", "$existingPath;C:\Program Files\containerd\bin", [EnvironmentVariableTarget]::Machine)
}

# Configure containerd
$configPath = "C:\Program Files\containerd\config.toml"
if (-not (Test-Path $configPath)) {
    & containerd.exe config default | Out-File -FilePath $configPath -Encoding utf8
}

# Install containerd as service
& containerd.exe --install-service
Start-Service containerd

Write-Log "containerd installed and started"

# ---------- 3. Windows Firewall ----------
Write-Log "Configuring Windows Firewall"
$rules = @(
    @{Name="K8s-Kubelet"; DisplayName="Kubernetes Kubelet"; LocalPort=10250},
    @{Name="K8s-RDP"; DisplayName="Remote Desktop"; LocalPort=3389},
    @{Name="K8s-WinRM"; DisplayName="Windows Remote Management"; LocalPort=5985}
)

foreach ($rule in $rules) {
    New-NetFirewallRule -DisplayName $rule.DisplayName -Direction Inbound -Protocol TCP -LocalPort $rule.LocalPort -Action Allow -ErrorAction SilentlyContinue
}

Write-Log "Firewall rules configured"

# ---------- 4. Page file on dedicated volume ----------
Write-Log "Configuring page file"
$pageFileVolume = Get-Volume | Where-Object { $_.FileSystemLabel -eq "PageFile" } | Select-Object -First 1
if ($pageFileVolume) {
    $pageFilePath = "$($pageFileVolume.DriveLetter):\pagefile.sys"
    Set-CimInstance -Query "Select * from Win32_PageFileSetting" | Remove-CimInstance -ErrorAction SilentlyContinue
    New-CimInstance -ClassName Win32_PageFileSetting -Property @{
        Name = $pageFilePath
        InitialSize = 8192
        MaximumSize = 16384
    }
}

Write-Log "Page file configured"

# ---------- 5. BitLocker ----------
Write-Log "Enabling BitLocker"
try {
    Enable-BitLocker -MountPoint "C:" -EncryptionMethod XtsAes128 -UsedSpaceOnly -TpmProtector -RecoveryPasswordProtector
    Write-Log "BitLocker enabled on C:"
} catch {
    Write-Log "BitLocker enable failed: $_"
}

# ---------- 6. Domain join ----------
Write-Log "Joining domain"
$domain = "internal"
$ou = "OU=KubernetesWorkers,DC=internal,DC=local"
$credential = Get-Credential -Message "Enter domain admin credentials"
Add-Computer -DomainName $domain -OUPath $ou -Credential $credential -Restart -Force
# Note: Script does not continue past this line; system reboots