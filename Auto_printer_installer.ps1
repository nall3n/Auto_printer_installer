
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$printer_driver = "Generic / Text Only"
$port_number = 9100

$test_array = @(
    @{ö
        "Name" = "Sky bar"
        "Port_name" = "Sky_bar"
        "Ip" = "192.168.0.37"
    },
    @{
        "Name" = "Sky kök"
        "Port_name" = "Sky_kok"
        "Ip" = "192.168.0.38"
    },
    @{
        "Name" = "Nilssons Kök"
        "Port_name" = "nilssons_kok"
        "Ip" = "192.168.0.50"
    },
    @{
        "Name" = "Percys Kök"
        "Port_name" = "Percys_kok"
        "Ip" = "192.168.0.123"
    },
    @{
        "Name" = "Percys Bar"
        "Port_name" = "Percys_Bar"
        "Ip" = "192.168.0.100"
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
