# miscan

Python script to Scan for Bluetooth Low Energy (BLE) temperature and humidity sensors and report the metrics to an MQTT broker.

This script can be used with the Xiaomi Mijia LYWSDCGQ (round with LCD) readily, because this sensor transmits its metrics unencrypted.
Many other sensors, such as the Xiaomi Mijia YWSD03MMC (square with LCD) transmit their metrics encrypted over BLE. To use this script with those 
devices, a custom firmware needs to be flashed: [https://github.com/pvvx/ATC_MiThermometer]

While many other implementations establish connections, this script listens to the BLE messages that are advertised by the sensor at regular timings. 
This significantly extends the life of the battery. In addition, when using the ATC firmware, it is possible to optimize the battery life even more: 
[https://github.com/pvvx/ATC_MiThermometer/issues/23]


## Running in a development environment

Creating the environment:

```shell
python -m venv miscan_env       # creates the environment
source miscan_env/bin/activate  # activate the environment
pip install -r requirements.txt
```

Activating an existing environment:

```shell
source miscan_env/bin/activate  # activate the environment
```


Deactivate the environment:

```shell
`deactivate`
```