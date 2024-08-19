$driverName = "Your Printer Driver"
$printerIP = "x.x.x.x"
$deviceName = "Your Printer Name"
$pauseInterval = "3"
Invoke-Command {pnputil.exe -a "C:\path_to_driver\printer.inf" }

Add-PrinterDriver -Name $driverName

Start-Sleep $pauseInterval

Add-PrinterPort -Name $printerIP -PrinterHostAddress $printerIP

Start-Sleep $pauseInterval

Add-Printer -DriverName $driverName -Name $deviceName -PortName $printerIP

Start-Sleep $pauseInterval

get-printer |Out-Printer -Name $deviceName