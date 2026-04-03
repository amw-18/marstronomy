# Mars Sky POC

This repo now contains a Python proof of concept for rendering the bright-star sky as seen from Olympus Mons on Mars.

## Run

```bash
python3 scripts/mars_star_poc.py
```

That generates:

- `out/olympus_mons_visible_stars.json`
- `out/olympus_mons_sky.svg`

## Notes

- The observer defaults to Olympus Mons at `18.65°N, 226.2°E`.
- The script uses the local `bsc5.json` catalog and infers its usable schema at runtime.
- This local catalog variant contains core fields such as `RA`, `Dec`, `Vmag`, `K`, and `HR`, so labels currently fall back to `HR ####` identifiers.
- No third-party Python packages are required.
- Mars orientation uses the standard IAU/NAIF pole and prime-meridian model.
- This is a stars-only POC, so it does not yet dim or hide stars for daylight conditions.
