# Eurocase

A local-first euro coin collection tracker built for static GitHub Pages hosting.

## What is included

- A data-driven catalogue grouped by issuing country.
- All eight denominations shown in rows, with regular design variants and €2 commemorative issues grouped separately.
- Coin-image toggles, clear collected states, and an information view for each variant.
- Automatic browser-local collection storage under `euro-coins.collection.v1`.
- Portable JSON backup/import and a confirmed reset action.
- A GitHub Pages deployment workflow for pushes to `main`.

The bundled catalogue contains 895 circulation-coin issues from all 25 euro-issuing countries: 311 regular denomination/design variants through the 2026 Luxembourg and Vatican series, plus 584 €2 commemorative issues through 2025. Images and reference information come from the official [European Central Bank](https://www.ecb.europa.eu/euro/coins/html/index.en.html) catalogue, with official issuing-authority sources filling current ECB gaps and image placeholders. The original files are bundled locally so the deployed app does not depend on those sites at runtime.

The catalogue is intentionally variant-based, not mint-year/mint-mark-based. For example, Germany's five mint marks do not become five separate cards unless their national-side design differs.

## Local development

```sh
npm install
npm run dev
```

## Validation

```sh
npm test
npm run lint
npm run build
```

## Refreshing the official catalogue

The generated catalogue and bundled images can be refreshed from the official sources with:

```sh
python scripts/import-ecb-catalog.py
```

The importer requires Python, `requests`, and `beautifulsoup4`. Existing stable IDs are preserved by the generated naming scheme, so an updated catalogue does not discard locally collected coins.

## GitHub Pages

Create a GitHub repository, push this project to its `main` branch, and select **GitHub Actions** as the Pages source in the repository settings. The included workflow builds and deploys `dist/`.
