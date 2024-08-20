
$printer_driver = "Generic / Text Only"

$test_array = @(
    @{
        "Name" = "Percy food"
        "Port_name" = "percy_food"
        "Ip" = "192.168.0.37"
    },
    @{
        "Name" = "Percy bar"
        "Port_name" = "percy_bar"
        "Ip" = "192.168.0.38"
    },
    @{
        "Name" = "Nilssons food"
        "Port_name" = "nilssons_food"
        "Ip" = "192.168.0.50"
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
            Add-PrinterPort -Name $item["Port_name"] -PrinterHostAddress $item["Ip"]
            Set-Printer -Name $item["Name"] -PortName $item["Port_name"]
            Write-Output $item["Ip"]
        }
    } else {
        Write-Output "Adding Printer" 
        Add-PrinterPort -Name $item["Port_name"] -PrinterHostAddress $item["Ip"]
        Add-Printer -DriverName $printer_driver -Name $item["Name"] -PortName $item["Port_name"]
    }
}
