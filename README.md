# Smart Oil Gauge for Home Assistant

Custom integration for the Connected Consumer Fuel **Smart Oil Gauge**. It reads your tank
from the same account as app.smartoilgauge.com (cloud polling, hourly, no paid API).

Fork of [bergb91-coder/ha-smartoilgauge](https://github.com/bergb91-coder/ha-smartoilgauge) with fixes:

- HACS-compliant layout (`custom_components/` at the repo root).
- Uses its own HTTP session, which fixes `could not find login nonce` on setup.
- Clear "invalid login" vs "cannot connect" errors, plus a re-authentication flow.
- Proper sensor types: volume (gal), percent, battery (diagnostic), last reading (timestamp).

## Install

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/jmullally/ha-smartoilgauge`, type **Integration**.
2. Download **Smart Oil Gauge**, then restart Home Assistant.
3. Settings → Devices & services → **Add integration** → Smart Oil Gauge, and sign in.

## Entities (per tank)

| Entity | Notes |
| --- | --- |
| Oil level | Gallons remaining; attribute `tank_capacity_gal` |
| Oil percent | Gallons ÷ fillable capacity (e.g. 251 of a 275 gal tank) |
| Gallons to fill | Fillable capacity − gallons; handy when ordering oil |
| Battery | `good` / `ok` / `poor` |
| Last reading | When the gauge last reported |

## Testing outside Home Assistant

`python tools/test_login.py` prompts for your login and prints the raw tank data.

## License

MIT
