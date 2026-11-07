# Architecture

Target: Raspberry Pi Zero 2 W, Waveshare 7.5" e-paper, 800x480, 1-bit,
landscape only. Language German, time zone Europe/Berlin.

## Principles

- One long-running process (systemd, `Restart=always`), about 30-40 MB RAM.
- Dependencies: Pillow only (plus the vendor Waveshare driver, installed
  separately). HTTP via `urllib`, time via `zoneinfo`, ICS parsed in-house.
- Sources, rendering and display are separate layers. A failure in one source
  or panel never blanks the screen.
- All secrets come from `.env` (git-ignored). Nothing personal in the repo.

## Data flow

```
scheduler -> hub.refresh() -> sources/* -> models
          -> render.compose.render(data) -> PIL "1" image 800x480
          -> display.show(image)  (Waveshare or PNG preview)
```

## Modules (`dashboard/`)

| Module | Role |
|---|---|
| `config.py` | `.env` loader, typed `Config`, display size constants |
| `models.py` | dataclasses: Observation, Forecast, Energy, Event, Match |
| `net.py` | small stdlib HTTP helpers |
| `sources/` | `netatmo`, `meteoswiss`, `solarmanager`, `calendar_ics`, `arsenal` |
| `hub.py` | calls all sources, keeps last good value, flags stale data |
| `render/` | `compose` (page grid), panels `weather`, `energy`, `calendar`, helpers `util`, `fonts` |
| `display/` | `waveshare` (init -> display -> sleep), `preview` (PNG), `get_display()` |
| `scheduler.py` | clock-aligned loop (:00/:30), sleep window, boot clock wait |
| `demo.py` | sample data for layout work without APIs |

## Layout (800x480)

```
header: date, time                              0-40
Draussen | Solar & Batterie | Heute              40-236
Prognose 48 h (chart)        | Aussichten (5 d)  236-424
Arsenal countdown                                424-480
```

No icons: text, numbers and one chart. Fonts 15-56 px, bold for key values.

## Reliability

- Per-source error isolation. Stale data stays visible, marked `Stand HH:MM`
  (or `keine Daten`).
- Per-panel `try/except` in `compose`.
- Update-cycle errors are logged and the loop continues.
- Boot: waits up to 2 min for a valid system clock (no RTC on the Pi).
- Waits use short naps, so NTP clock jumps are harmless.
- The panel is put in deep sleep after every refresh.
- Sleep mode 00:00-06:00: one "Ruhemodus" screen, no updates, and a full
  clear when waking to avoid ghosting.

## Refresh strategy

Full refresh every 30 minutes (`FULL_REFRESH_MINUTES`). Partial refresh is
not enabled. The Waveshare V2 partial mode has not been tested on this
hardware, and 30-minute updates do not need it. A later extension could
refresh only the clock box.

## Adding information

1. Add a dataclass to `models.py`.
2. Add `sources/<name>.py` with `fetch(cfg)`.
3. Register it in `hub.SOURCES`.
4. Add a panel function in `render/` and call it from `compose.render`.

## External APIs and assumptions

- MeteoSwiss: unofficial app endpoint `plzDetail`. It may change without notice.
- Netatmo: OAuth refresh-token flow. The rotating token is stored in `data/`.
- Solar Manager: `SOLARMANAGER_URL` must point to the endpoint that returns
  live values. Field names are matched in `sources/solarmanager.py`. This
  could not be verified offline, so confirm it against your installation.
- Calendar: Google "secret iCal address". Recurrence support is limited to
  simple daily/weekly rules.
- Arsenal: football-data.org free token (`FOOTBALL_DATA_TOKEN`).
