# Dashboard

Wall-mounted e-paper dashboard (German UI) for a Raspberry Pi Zero 2 W with a
Waveshare 7.5" 800x480 black/white display, landscape only.

Shows: own Netatmo weather, MeteoSwiss forecast (48 h chart + 5 days),
PV/battery (Solar Manager), today's family calendar and an Arsenal countdown.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

## Development (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # fill in values
$env:DISPLAY_DRIVER = "preview"
python -m dashboard --demo  # sample data -> data\preview.png
python -m dashboard --once  # real data   -> data\preview.png
```

## Raspberry Pi

```bash
sudo apt install -y python3-venv python3-pil fonts-dejavu-core git
git clone https://github.com/stratocumulus-lenticularis/dashboard.git ~/dashboard
cd ~/dashboard && python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env
sudo raspi-config nonint do_spi 0           # enable SPI
```

The Waveshare driver is not part of this repo. Copy `waveshare_epd/`
(`epd7in5_V2.py`, `epdconfig.py`) from
https://github.com/waveshareteam/e-Paper (RaspberryPi_JetsonNano/python/lib)
to the Pi and set `WAVESHARE_LIB_DIR` in `.env`. It needs `spidev` and
`gpiozero` (`sudo apt install python3-spidev python3-gpiozero`).

Run as a service:

```bash
sudo cp deploy/dashboard.service /etc/systemd/system/
sudo systemctl enable --now dashboard
journalctl -u dashboard -f
```

Update: `cd ~/dashboard && git pull && sudo systemctl restart dashboard`

## License

MIT
