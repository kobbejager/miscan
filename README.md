# miscan

miscan listens to Xiaomi Bluetooth (BLE) thermometers and publishes their readings on MQTT. It also
announces every sensor to Home Assistant through MQTT discovery.

It never connects to a sensor. The sensors broadcast their readings in BLE advertisements, and miscan
only listens (passive scanning). That is what keeps the battery life long. Supported broadcast formats:

| format   | sensor                                     | service data | readings                                            |
|----------|--------------------------------------------|--------------|-----------------------------------------------------|
| PVVX     | LYWSD03MMC with [pvvx custom firmware][fw] | `0x181A`     | temperature, humidity, battery in one packet        |
| ATC1441  | LYWSD03MMC with ATC firmware (atc1441 format) | `0x181A`  | temperature, humidity, battery in one packet        |
| MiBeacon | LYWSDCGQ (round, stock firmware)           | `0xFE95`     | temperature+humidity and battery in separate packets |

The stock LYWSD03MMC encrypts its broadcasts and needs the custom firmware. Encrypted MiBeacon packets
are ignored.

Version 1 (bluepy, JSON configuration, JSON payloads) is on the `v1` branch (tag `v1-final`).

[fw]: https://github.com/pvvx/ATC_MiThermometer

## How it works

- **Only configured sensors are published.** Sensors that are not in `miscan.yaml` are logged once per run,
  with a configuration snippet (see [Adding a sensor](#adding-a-sensor)).
- **Every value has its own topic.** A packet publishes the values it contains, plus its RSSI. The
  LYWSDCGQ sends its battery level in a separate packet, so that packet only publishes `battery` and `rssi`.
- **Every measurement is published, once.** A sensor repeats each measurement in many advertisements. All
  formats carry a counter that changes with every new measurement. miscan skips packets with the same
  counter as the previous one. A new measurement is published even when the values have not changed, so
  long-term graphs (VictoriaMetrics, Grafana) have no gaps.
- **Everything is retained**, so a subscriber that connects gets the latest values immediately.
- **Silent sensors are reported.** When a sensor has sent nothing for `availability.timeout` seconds
  (default 15 minutes), miscan publishes `offline` on its availability topic, for example when the battery
  is dead. Home Assistant then shows the sensor as unavailable. The next packet sets it back to `online`.

## MQTT topics

`<prefix>` is `mqtt.prefix` (default `miscan`). `<id>` is the device id from `miscan.yaml`.

| topic                                         | retained | payload                                       |
|-----------------------------------------------|----------|-----------------------------------------------|
| `<prefix>/status`                             | yes      | `online` / `offline` (last will)              |
| `<prefix>/<id>/temperature`                   | yes      | `21.43` (°C)                                  |
| `<prefix>/<id>/humidity`                      | yes      | `48.2` (%)                                    |
| `<prefix>/<id>/battery`                       | yes      | `87` (%)                                      |
| `<prefix>/<id>/rssi`                          | yes      | `-71` (dBm)                                   |
| `<prefix>/<id>/availability`                  | yes      | `online` / `offline` (see above)              |
| `homeassistant/device/miscan_<mac>/config`    | yes      | Home Assistant device discovery               |

In Home Assistant, every sensor is a device with four entities: temperature, humidity, battery and signal
strength (the last two as diagnostics). An entity is available when both `<prefix>/status` and
`<prefix>/<id>/availability` are `online`. The unique ids are based on the MAC address, so renaming a
device id or name in `miscan.yaml` does not create a new device in Home Assistant.

At startup miscan clears every retained topic under `<prefix>/` that it no longer publishes, and the
discovery of sensors that were removed from the configuration. This also removes what version 1 left
behind. miscan republishes discovery when Home Assistant restarts (`homeassistant/status` = `online`).

## Installation

miscan is a normal Python package (Python ≥ 3.12). Installing it into a virtual environment gives you a
`miscan` command at `.venv/bin/miscan`. Its dependencies are `bleak`, `aiomqtt`, `pydantic` and `PyYAML`.
Bleak talks to BlueZ (`bluetoothd`) over D-Bus with the pure Python package `dbus-fast`. No system
packages are needed beyond BlueZ itself.

The exact dependency versions that were tested are pinned in `uv.lock`. Option A uses that file
automatically. With option B you install from `pyproject.toml`, which only gives minimum versions, so
you may get newer releases.

### Option A: `uv venv` + `uv pip` (classic workflow)

```sh
cd miscan
uv venv                          # creates .venv/
uv pip install -e .              # installs miscan (editable) and its dependencies
uv pip install --group dev       # optional: pytest and ruff, for development
```

Then either activate the environment or call the binaries directly:

```sh
source .venv/bin/activate
miscan --help
# or, without activating:
.venv/bin/miscan --help
```

To use the tested versions from `uv.lock` with this workflow:

```sh
uv export --frozen --no-dev --no-emit-project -o requirements.txt
uv pip install -r requirements.txt
uv pip install --no-deps .
```

### Option B: `uv sync` (project workflow)

```sh
cd miscan
uv sync                          # add --no-dev on a production machine
```

`uv sync` creates `.venv/`, installs exactly the versions in `uv.lock` plus the dev tools, and installs
miscan itself in editable mode. `uv run miscan --help` runs a command in `.venv/` without activating it.

The rest of this README writes plain `miscan ...`. Activate `.venv` first, or put `.venv/bin/` or
`uv run` in front.

### Passive scanning

miscan scans passively by default. BlueZ only allows that through its AdvertisementMonitor API, which
needs `bluetoothd` with experimental features enabled (and Linux ≥ 5.10). Without it miscan stops with
`cannot start passive scanning`. Enable it in `/etc/bluetooth/main.conf`:

```ini
[General]
Experimental = true
```

or start `bluetoothd` with `--experimental` (`sudo systemctl edit bluetooth`; see `systemctl cat bluetooth`
for the `ExecStart=` line to copy). Then `sudo systemctl restart bluetooth`.

`ble.scanning_mode: active` works without this. In active mode, however, BlueZ sends a scan request for
every advertisement and the sensor answers it, which costs battery. The same happens when another program
(for example the Home Assistant Bluetooth integration) scans actively with the same adapter.

## Configuration

See [`miscan.example.yaml`](miscan.example.yaml) for every option.

### MQTT connection: `.env`

The broker host, port, username and password are not in `miscan.yaml`. They come from environment
variables, normally kept in a `.env` file. `.env` is in `.gitignore`, so it is never committed.

```sh
cp .env.example .env
chmod 600 .env
$EDITOR .env                                 # fill in MISCAN_MQTT_HOST, _USERNAME, _PASSWORD
```

- **Where it looks:** miscan reads `.env` from the current directory. Use `--env-file PATH` to read
  another file.
- **Precedence:** a variable that is already set in the environment wins over the same one in the file.
- **Which settings:** every `mqtt:` setting can be set as `MISCAN_MQTT_<KEY>`, and that overrides
  `miscan.yaml`.
- **Format:** plain `KEY=value` lines, the same format systemd's `EnvironmentFile=` uses.

### Adding a sensor

```sh
miscan --scan                                # listen for 30 seconds; or --scan 120
```

This lists every sensor in range, configured or not, with the strongest signal first. It doesn't need
MQTT or a configuration file:

```
MAC                id          format    RSSI  temp   hum   batt  measurements
A4:C1:38:AA:BB:CC  -           PVVX      -48   21.43  48.2  87    3
58:2D:34:44:55:66  slaapkamer  MiBeacon  -77   19.4   55.1  93    2
```

To find out which one is the new sensor, hold it next to the receiver (strongest RSSI), or breathe on it
(humidity rises). While miscan is running, unconfigured sensors also show up in the log, once per MAC,
with a snippet to paste into `miscan.yaml`:

```sh
journalctl -u miscan | grep -A4 unconfigured
```

### Checking the configuration

```sh
miscan -c miscan.yaml --check-config         # validate the configuration
miscan -c miscan.yaml --dump-discovery       # print what Home Assistant will receive
```

## Running

```sh
miscan -c miscan.yaml                        # reads .env; add --log-level DEBUG to see every packet
```

Stop it with Ctrl+C. miscan publishes `offline` on `<prefix>/status` before exiting.

### As a systemd service

The unit file [`deploy/miscan.service`](deploy/miscan.service) expects:

| what                         | where                        |
|------------------------------|------------------------------|
| the code and its `.venv/`    | `/opt/miscan`                |
| the configuration            | `/etc/miscan/miscan.yaml`    |
| the MQTT settings (`.env`)   | `/etc/miscan/env`            |
| the service account          | user `miscan`, also in group `bluetooth` |

The `bluetooth` group gives access to BlueZ over D-Bus (this is the policy on Debian and Raspberry Pi OS;
check `/usr/share/dbus-1/system.d/bluetooth.conf` on other systems). Every step:

```sh
# 1. service account and code
sudo useradd --system --home-dir /opt/miscan --shell /usr/sbin/nologin --groups bluetooth miscan
sudo git clone <repo-url> /opt/miscan
sudo chown -R miscan: /opt/miscan

# 2. virtual environment, as the miscan user (option A shown; option B: uv sync --frozen --no-dev)
cd /opt/miscan
sudo -u miscan uv venv
sudo -u miscan uv export --frozen --no-dev --no-emit-project -o requirements.txt
sudo -u miscan uv pip install -r requirements.txt
sudo -u miscan uv pip install --no-deps .
sudo -u miscan /opt/miscan/.venv/bin/miscan --scan  # check: Bluetooth access and passive scanning

# 3. configuration and MQTT settings
sudo install -d /etc/miscan
sudo cp miscan.example.yaml /etc/miscan/miscan.yaml
sudoedit /etc/miscan/miscan.yaml                   # your sensors
sudo install -m 600 .env.example /etc/miscan/env
sudoedit /etc/miscan/env                           # fill in host, username, password
sudo /opt/miscan/.venv/bin/miscan -c /etc/miscan/miscan.yaml --env-file /etc/miscan/env --check-config

# 4. service
sudo cp deploy/miscan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now miscan
journalctl -u miscan -f                            # follow the log
```

To update:

```sh
cd /opt/miscan && sudo -u miscan git pull
sudo -u miscan uv pip install --no-deps .          # option B: sudo -u miscan uv sync --frozen --no-dev
sudo systemctl restart miscan
```

If `uv.lock` changed, first rerun the `uv export` and `uv pip install -r requirements.txt` lines from
step 2.

## Migrating from v1

1. Stop v1. Both versions cannot share the Bluetooth adapter reliably: bluepy bypasses `bluetoothd`.
2. Convert the `devices` section of the v1 JSON configuration: `"a4:c1:38:11:22:33": "woonkamer"` becomes
   `woonkamer:` with `mac: A4:C1:38:11:22:33`. Keep the same names as ids, so the
   `miscan/<name>/temperature`, `humidity` and `battery` topics stay the same.
3. Start v2. It clears the retained v1 leftovers: `miscan` (the old status topic), `miscan/<name>` (JSON),
   `miscan/<name>/timestamp` and the topics of unconfigured sensors.

Differences that subscribers may notice: there is no JSON payload any more, the bridge status moved from
`miscan` to `miscan/status`, and messages are always retained.

## Development

Install with the dev tools (`uv pip install -e . && uv pip install --group dev`, or `uv sync`). Then:

```sh
pytest                                   # or: uv run pytest
ruff check . && ruff format --check .
```

Dependencies are declared in `pyproject.toml`. Add one with `uv add <package>` (or `uv add --dev
<package>`), which also updates `uv.lock`. If you only edit `pyproject.toml` by hand, run `uv lock`
afterwards.

The packet parsers (`parsers.py`) and the application logic (`app.py`) are tested without Bluetooth or
MQTT. The tests build packets in each format and use a fake clock for availability.
