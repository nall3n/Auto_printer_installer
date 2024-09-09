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
        "Name" = "Skybar k�k"
        "Port_name" = "Skybar_kok"
        "Ip" = "10.2.64.100"
    },
    @{
        "Name" = "Nilssons K�k"
        "Port_name" = "Nilssons_Kok"
        "Ip" = "10.2.64.101"
    },
    @{
        "Name" = "Percys K�k"
        "Port_name" = "Percys_kok"
        "Ip" = "10.1.64.98"
    },
    @{
        "Name" = "Percys Bar"
        "Port_name" = "Percys_Bar"
        "Ip" = "10.1.64.99"
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
