# Mars Sky POC

This repo contains a no-dependency Python proof of concept for rendering the bright-star sky from Olympus Mons on Mars, plus a timeline scene that adds the Sun, Phobos, and Deimos with perceptual moon phases.

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

By default the scene timeline starts at `2026-04-06T00:00:00Z`, which gives a more representative demo window where Deimos appears in the keyframes.

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Run The Browser Viewer

```bash
cd web
npm install
npm run dev
```

The web app:

- exports a compact star vector catalog from Python into `web/public/data/stars.min.json`
- keeps the Mars sky math in TypeScript so time changes can run in real time in the browser
- provides a fullscreen observer view with drag-to-look, mouse-wheel FOV, a UTC time input, speed controls, and a moon-phase inset

You can also run:

```bash
cd web
npm run test
npm run build
```

## Notes

- The observer defaults to Olympus Mons at `18.65°N, 226.2°E`.
- The local `bsc5.json` catalog variant contains fields such as `RA`, `Dec`, `Vmag`, `K`, and `HR`, so star labels still fall back to `HR ####` identifiers.
- No third-party Python packages are required.
- The browser viewer uses `Vite + TypeScript + Canvas2D`.
- Mars orientation uses the standard IAU/NAIF pole and prime-meridian model.
- The Sun uses NASA Mars24 equations for seasonal and daily motion.
- Phobos and Deimos use lightweight circular Mars-body-frame orbits with topocentric parallax, tuned for visual feel rather than extreme ephemeris accuracy.
- Moon phases use synchronous-rotation lighting with SVG-clipped irregular silhouettes.
- The main sky keeps Phobos and Deimos close to naked-eye expectations, while the browser HUD and SVG keyframes also include a magnified moon-phase inset for inspection.
- Daylight dims stars strongly but does not remove them entirely, so the timeline stays readable for later web playback.
