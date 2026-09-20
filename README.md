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

## Publishing

The site is live at <https://seardnaschmid.github.io/euro-coin-collection-tracker/>.

Every push to `main` runs `.github/workflows/deploy.yml`, which tests, builds, and deploys `dist/` to GitHub Pages. The Pages source is set to **GitHub Actions**, so no `gh-pages` branch is involved. Vite's `base` is `"./"`, which is what lets the same build work under the repository subpath.

## Releasing

Releases are independent of publishing: a tag cuts a release, a push to `main` updates the live site.

```sh
npm version minor   # writes package.json, commits, and creates the vX.Y.Z tag
git push --follow-tags
```

The `v*` tag triggers `.github/workflows/release.yml`, which rebuilds from the tag, attaches `eurocase-vX.Y.Z.zip` (the contents of `dist/`), and generates release notes from the commits since the previous tag. Edit the notes afterwards if the generated list needs prose.

Use `npm version patch`, `minor`, or `major` as appropriate. To re-run a release for a tag that already exists, trigger the workflow manually from the Actions tab and pass the tag name.
