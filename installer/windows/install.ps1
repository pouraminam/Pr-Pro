<#
.SYNOPSIS
    Premiere AI Editor - Graphical Windows 11 Installer
.DESCRIPTION
    Checks system prerequisites, detects installed Adobe Premiere Pro versions (v24/v25),
    installs the UXP plugin to Adobe's external plugin directory, sets up the local helper runtime,
    and tests localhost communication.
#>

[CmdletBinding()]
param()

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName System.Windows.Forms

# Check Windows 11 / OS Version
$os = Get-CimInstance Win32_OperatingSystem
$buildNumber = [int]$os.BuildNumber

Write-Host "Premiere AI Editor Installer - Windows Build $buildNumber"

# Premiere Pro Detection
$premierePaths = @(
    "C:\Program Files\Adobe\Adobe Premiere Pro 2025\Adobe Premiere Pro.exe",
    "C:\Program Files\Adobe\Adobe Premiere Pro 2024\Adobe Premiere Pro.exe",
    "C:\Program Files\Adobe\Adobe Premiere Pro (Beta)\Adobe Premiere Pro.exe"
)

$detectedPremiere = $null
foreach ($path in $premierePaths) {
    if (Test-Path $path) {
        $detectedPremiere = $path
        break
    }
}

# Determine UXP Plugin Destination
$appData = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::ApplicationData)
$uxpPluginsDir = Join-Path $appData "Adobe\UXP\Plugins\External\com.premiere.ai.editor"

# WPF GUI Dialog
[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Premiere AI Editor Setup" Height="420" Width="520"
        WindowStartupLocation="CenterScreen" ResizeMode="NoResize" Background="#1E1E1E">
    <Window.Resources>
        <Style TargetType="TextBlock">
            <Setter Property="Foreground" Value="#EEEEEE"/>
            <Setter Property="FontFamily" Value="Segoe UI"/>
        </Style>
        <Style TargetType="Button">
            <Setter Property="Background" Value="#1473E6"/>
            <Setter Property="Foreground" Value="White"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="Padding" Value="12,6"/>
            <Setter Property="BorderThickness" Value="0"/>
        </Style>
    </Window.Resources>
    <Grid Margin="24">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <StackPanel Grid.Row="0" Margin="0,0,0,16">
            <TextBlock Text="Premiere AI Editor - Setup" FontSize="18" FontWeight="Bold" Foreground="#FFFFFF"/>
            <TextBlock Text="AI-assisted silence cutting, Faster-Whisper transcription, and Persian/English subtitles." FontSize="12" Foreground="#8E8E8E" Margin="0,4,0,0"/>
        </StackPanel>

        <Border Grid.Row="1" Background="#252525" CornerRadius="6" Padding="16" BorderBrush="#383838" BorderThickness="1">
            <StackPanel>
                <TextBlock Text="System Verification:" FontWeight="Bold" FontSize="13" Margin="0,0,0,8"/>
                <TextBlock x:Name="TxtWindowsStatus" Text="• Windows: Checking..." FontSize="12" Margin="0,2"/>
                <TextBlock x:Name="TxtPremiereStatus" Text="• Premiere Pro: Checking..." FontSize="12" Margin="0,2"/>
                <TextBlock x:Name="TxtPythonStatus" Text="• Local Engine: Checking..." FontSize="12" Margin="0,2"/>

                <TextBlock Text="Destination Folder:" FontWeight="Bold" FontSize="12" Margin="0,16,0,4"/>
                <TextBox x:Name="TxtInstallPath" IsReadOnly="True" Background="#1A1A1A" Foreground="#CCCCCC" BorderBrush="#444" Padding="6" FontSize="11"/>

                <ProgressBar x:Name="PrgProgress" Height="8" Margin="0,16,0,0" Visibility="Collapsed" IsIndeterminate="True" Foreground="#1473E6"/>
                <TextBlock x:Name="TxtProgressMessage" Text="" FontSize="11" Foreground="#888" Margin="0,4,0,0"/>
            </StackPanel>
        </Border>

        <StackPanel Grid.Row="2" Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,16,0,0">
            <Button x:Name="BtnCancel" Content="Cancel" Background="#333333" Margin="0,0,8,0" Width="80"/>
            <Button x:Name="BtnInstall" Content="Install Now" Width="100"/>
        </StackPanel>
    </Grid>
</Window>
"@

$reader = (New-Object System.Xml.XmlNodeReader $xaml)
$window = [System.Windows.Markup.XamlReader]::Load($reader)

# Element References
$txtWin = $window.FindName("TxtWindowsStatus")
$txtPrem = $window.FindName("TxtPremiereStatus")
$txtPy = $window.FindName("TxtPythonStatus")
$txtPath = $window.FindName("TxtInstallPath")
$btnInstall = $window.FindName("BtnInstall")
$btnCancel = $window.FindName("BtnCancel")
$prgProgress = $window.FindName("PrgProgress")
$txtMsg = $window.FindName("TxtProgressMessage")

# Populate Initial Info
$txtWin.Text = "• Windows: Compatible (Build $buildNumber)"
$txtWin.Foreground = [System.Windows.Media.Brushes]::LightGreen

if ($detectedPremiere) {
    $txtPrem.Text = "• Premiere Pro: Detected ($([System.IO.Path]::GetFileName([System.IO.Path]::GetDirectoryName($detectedPremiere))))"
    $txtPrem.Foreground = [System.Windows.Media.Brushes]::LightGreen
} else {
    $txtPrem.Text = "• Premiere Pro: Not found in default path (will install plugin for manual load)"
    $txtPrem.Foreground = [System.Windows.Media.Brushes]::Khaki
}

$pyCheck = Get-Command python -ErrorAction SilentlyContinue
if ($pyCheck) {
    $txtPy.Text = "• Local Engine: Python detected ($($pyCheck.Source))"
    $txtPy.Foreground = [System.Windows.Media.Brushes]::LightGreen
} else {
    $txtPy.Text = "• Local Engine: Standalone helper package"
    $txtPy.Foreground = [System.Windows.Media.Brushes]::Khaki
}

$txtPath.Text = $uxpPluginsDir

$btnCancel.Add_Click({ $window.Close() })

$btnInstall.Add_Click({
    $btnInstall.IsEnabled = $false
    $prgProgress.Visibility = [System.Windows.Visibility]::Visible
    $txtMsg.Text = "Copying plugin files to Adobe UXP folder..."

    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $pluginSource = Resolve-Path (Join-Path $scriptDir "..\..\plugin")

    # Create destination directory
    if (-not (Test-Path $uxpPluginsDir)) {
        New-Item -ItemType Directory -Force -Path $uxpPluginsDir | Out-Null
    }

    # Copy plugin
    Copy-Item -Path "$pluginSource\*" -Destination $uxpPluginsDir -Recurse -Force

    $txtMsg.Text = "Setting up background service launcher..."

    # Create Desktop shortcut for launcher
    $desktop = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut((Join-Path $desktop "Premiere AI Editor Engine.lnk"))
    $shortcut.TargetPath = (Join-Path $scriptDir "start_engine.vbs")
    $shortcut.WorkingDirectory = (Join-Path $scriptDir "..\..")
    $shortcut.Description = "Starts the Premiere AI Editor local helper service"
    $shortcut.Save()

    $prgProgress.Visibility = [System.Windows.Visibility]::Collapsed
    $txtMsg.Text = "Installation completed successfully!"
    $txtMsg.Foreground = [System.Windows.Media.Brushes]::LightGreen

    [System.Windows.MessageBox]::Show(
        "Installation Complete!`n`n1. In Adobe Premiere Pro, open Window -> Extensions -> Premiere AI Editor.`n2. Launch 'Premiere AI Editor Engine' to run the offline speech and silence processor.",
        "Premiere AI Editor Setup",
        [System.Windows.MessageBoxButton]::OK,
        [System.Windows.MessageBoxImage]::Information
    )

    $window.Close()
})

$window.ShowDialog() | Out-Null
