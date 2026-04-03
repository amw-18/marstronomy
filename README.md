# Mars Sky POC

This repo contains a no-dependency Python proof of concept for rendering the bright-star sky from Olympus Mons on Mars, plus a timeline scene that adds the Sun, Phobos, and Deimos.

## Run The Stars-Only Snapshot

```bash
python3 scripts/mars_star_poc.py
```

That generates:

- `out/olympus_mons_visible_stars.json`
- `out/olympus_mons_sky.svg`

## Run The Sun + Moons Timeline

```bash
python3 scripts/mars_scene_poc.py
```

That generates:

- `out/olympus_mons_scene_timeline.json`
- `out/olympus_mons_scene_keyframes/keyframe_00.svg`
- `out/olympus_mons_scene_keyframes/keyframe_01.svg`
- `out/olympus_mons_scene_keyframes/keyframe_02.svg`
- `out/olympus_mons_scene_keyframes/keyframe_03.svg`
- `out/olympus_mons_scene_keyframes/keyframe_04.svg`
- `out/olympus_mons_scene_keyframes/keyframe_05.svg`

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- The observer defaults to Olympus Mons at `18.65°N, 226.2°E`.
- The local `bsc5.json` catalog variant contains fields such as `RA`, `Dec`, `Vmag`, `K`, and `HR`, so star labels still fall back to `HR ####` identifiers.
- No third-party Python packages are required.
- Mars orientation uses the standard IAU/NAIF pole and prime-meridian model.
- The Sun uses NASA Mars24 equations for seasonal and daily motion.
- Phobos and Deimos use lightweight circular Mars-body-frame orbits with topocentric parallax, tuned for visual feel rather than extreme ephemeris accuracy.
- Daylight dims stars strongly but does not remove them entirely, so the timeline stays readable for later web playback.
