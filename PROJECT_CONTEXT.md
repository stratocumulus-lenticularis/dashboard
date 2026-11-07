# Dashboard Project

## Purpose

Personal dashboard running on a Raspberry Pi Zero 2 WH.

The dashboard shall:
- display weather observations from own netatmo station
- display the local weather forecasts from MeteoSwiss
- display PV production information from own installation 
- display calendar items for today of family google calendar
- display countdown to next arsenal soccer game
- be optimized for a waveshare 800x480 e-ink b/w display
- run unattended for months
- target lay people

## Hardware

Target hardware:
- Raspberry Pi Zero 2 WH
- Raspberry Pi OS
- WLAN connection

Constraints:
- limited CPU
- limited RAM
- low power consumption


## Display

- Waveshare 7.5" e-Paper
- Refresh is slow compared to LCD screens
- Resolution: 800 × 480 pixels
- Black and white
- Physical orientation: Landscape (horizontal)
- Width: 800 px
- Height: 480 px

The display will always be mounted and operated in landscape orientation.
Do not design for portrait mode.


## Design Constraints

- Optimize layout for 800x480 pixels
- Avoid animations
- Avoid frequent screen refreshes
- Favor static dashboards
- Dashboard updates every 5-15 minutes
- High readability is more important than visual effects

Display refresh target:
- Full refresh every 30 minutes
- Partial updates where possible


Dashboard layout:
- Clock and Date
- Current weather
- Weather Forecast
- PV production
- Battery state
- Calendar entries
- Arsenal countdown


## UI Requirements

- Optimize all layouts for 800x480 landscape orientation.
- Use the full display width.
- Prefer multi-column layouts.
- No portrait layouts.

The display is wall-mounted and viewed from several meters away.
- Large, high-contrast typography suitable for e-paper displays.
- no graphics but only text and numbers

Prioritize:
1. Readability
2. Information density
3. Reliability
4. Visual design



## Information sources
- netatmo
- MeteoSwiss
- Solar Manager
- google

## Target location:
- User configurable

## Development Workflow

Development:
- Windows 10
- VS Code
- Cline agent
- Python 3

Source Code:
- GitHub repository https://github.com/stratocumulus-lenticularis/dashboard.git

Deployment:
- Raspberry Pi pulls code from GitHub
- No direct development on Raspberry Pi

## Technical Requirements

Preferred stack:
- Python

Avoid:
- Docker
- Kubernetes
- complex cloud dependencies

## Coding Principles

- Keep dependencies minimal
- Easy maintenance
- Readable code
- Modular architecture
- allow for additional information on dashboard in the future


## Security Requirements

Never store:
- API keys
- Passwords
- Personal addresses
- Personal names
- Personal locations

Use:
- .env files
- environment variables

The repository must be safe to publish publicly on GitHub.
Store secrets exclusively in .env files which are excluded via .gitignore.

