

$ip = "192.168.0.37"
$port_name = "percyskök"
$printer_name = "percys kök"


Add-PrinterPort -Name $port_name -PrinterHostAddress $ip
Add-Printer -DriverName "Generic / Text Only" -Name $printer_name -PortName $port_name