Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted


$printer_driver = "Generic / Text Only"
$port_number = 9100


$test_array = @(
    @{
        "Name" = "Skybar"
        "Port_name" = "Skybar"
        "Ip" = "10.2.64.102"
    },
    @{
        "Name" = "Skybar kök"
        "Port_name" = "Skybar_kok"
        "Ip" = "10.2.64.100"
    },
    @{
        "Name" = "Nilssons Kök"
        "Port_name" = "Nilssons_Kok"
        "Ip" = "10.2.64.101"
    },
    @{
        "Name" = "Percys Kök"
        "Port_name" = "Percys_kok"
        "Ip" = "10.1.64.98"
    },
    @{
        "Name" = "Percys Bar"
        "Port_name" = "Percys_Bar"
        "Ip" = "10.1.64.99"
    },
    # ------------------
    @{
        "Name" = "Loge Vattentornet"
        "Port_name" = "Loge_Vattentornet"
        "Ip" = "10.1.64.97"
    },
    @{
        "Name" = "Loge Emporia"
        "Port_name" = "Loge_Emporia"
        "Ip" = "10.1.65.96"
    },
    @{
        "Name" = "Lounge 4 S bar"
        "Port_name" = "Lounge_4_S_bar"
        "Ip" = "10.1.64.95"
    },
    @{
        "Name" = "Lounge 4 L Bar"
        "Port_name" = "Lounge_4_L_Bar"
        "Ip" = "10.1.65.94"
    },
    @{
        "Name" = "Lounge 4 Kök"
        "Port_name" = "Lounge_4_Kök"
        "Ip" = "10.1.64.93"
    }
)


foreach ($item in $test_array){
    
    $p = Get-Printer -Name $item["Name"]

    if ($p) {
        Write-Output "printer exists"
        $Port = Get-PrinterPort -Name $p.PortName
        if ($Port.PrinterHostAddress -ne $item["Ip"]){
            Write-Output $Port.PrinterHostAddress
            Set-Printer -Name $item["Name"] -PortName "COM1:" # Changes port to remove old network port
            Remove-PrinterPort -Name $p.PortName
            Add-PrinterPort -Name $item["Port_name"] -PrinterHostAddress $item["Ip"] -PortNumber $port_number
            Set-Printer -Name $item["Name"] -PortName $item["Port_name"]
            Write-Output $item["Ip"]
        }
    } else {
        Write-Output "Adding Printer" 
        Add-PrinterPort -Name $item["Port_name"] -PrinterHostAddress $item["Ip"] -PortNumber $port_number
        Add-Printer -DriverName $printer_driver -Name $item["Name"] -PortName $item["Port_name"]
    }
}
