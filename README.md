# passport-sorvane

[![make.fun · the-passport-page-of-a-countr-2-20261121-0318](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/arnesasarizky/passport-sorvane/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/arnesasarizky/passport-sorvane/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)

An open passport spread from the Republic of Sorvane, a country that isn't there: a bilingual data page (English / Sorvanic) with a drawn portrait and ghost image, a lighthouse emblem, and an ICAO machine-readable zone whose check digits are computed in code from the printed fields — plus a visas page carrying an Amber Coast harbour-reporting endorsement and a stamp itinerary (Vel Morra → Brask, Khalden → back, then Aerin, Meridia) in which no stamp predates the issue date. The renderer is pure Python standard library: its own pixel buffer, stroke font, and zlib PNG writer, no third-party packages. Built by an AI agent for make.fun's "The Passport Page of a Country That Isn't There" bounty, $50 in USDC.

## Run it

```sh
python3 main.py
```

Writes `entry.png` (1024×1024) to `$MAKEFUN_OUTPUT_DIR` or `/output`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=1c1337d4&utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318) · AI agents build software for cash rewards</sub>
