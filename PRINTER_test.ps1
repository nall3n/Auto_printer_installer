

$ip = "192.168.0.37"
$port_name = "percyskök"
$printer_driver = "Generic / Text Only"
$printer_name = "percys kök"


# $printer_1 = @{
#     "Name" = "Percy food"
#     "Port_name " = "percy_food"
#     "Ip" = "192.168.0.37"
# }


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
        "Ip" = "192.168.0.37"
    }
)

foreach ($item in $test_array){
    Write-Output $item
    
    Get-Printer -Name $item["Name"]

    if (Get-Printer -Name $item["Name"]) {
        Write-Output "printer exists"
    } else {
        Write-Output "Adding Printer" 
        Add-PrinterPort -Name $item["Port_name"] -PrinterHostAddress $item["Ip"]
        Add-Printer -DriverName $printer_driver -Name $item["Name"] -PortName $item["Port_name"]
    }
}


# Add-PrinterPort -Name $port_name -PrinterHostAddress $ip
# Add-Printer -DriverName $printer_driver -Name $printer_name -PortName $port_name