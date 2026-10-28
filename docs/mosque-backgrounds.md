# Mosque photograph backgrounds

**Current implementation: 0.9.18 on `main`.** The 20 locally bundled WebP
photographs and their verified credits were reviewed during development and
are included in the integration. See [the source and photographer credits](mosque-background-credits.md)
and the [dashboard guide](dashboard.md#optional-mosque-photograph-backgrounds).

## What the card does

- **Show mosque background** is enabled by default; users can disable it per
  card. **Mosque background** defaults to a deterministic daily rotation, or
  may be set to one of the 20 bundled images (or `none`).
- Rotation is keyed to the mosque-local published date. It cycles through the
  bundled photographs without repeating until the cycle has been exhausted.
  The photograph is decorative: it does not identify the configured mosque or
  influence its timetable, Ramadan calculations or sensors.
- The full-strength photograph is served locally. There is **no global photo
  opacity/tint overlay and no background-opacity editor control**. The removed
  `mosque_background_opacity` option is ignored and discarded during card
  configuration normalisation for older saved dashboards.
- The card covers its allocated dashboard width and at least the available
  viewport height, so Yesterday/Tomorrow do not expose an empty black canvas
  when their countdowns disappear. The inner summary and timetable remain
  centred (up to 1160px) and top-aligned. This intentionally reserves viewport
  height when other dashboard cards are stacked below.
- A consistent **CSS-first liquid-glass** style applies to both the summary
  and timetable: 84–88% HA-theme-aware surfaces, frosted blur, subdued edge
  highlights and readable text. There is no external shader or image service.
  Higher-contrast/reduced-transparency preferences disable the photo and
  use opaque panels; browsers without backdrop-filter support also receive
  opaque panels.
- Background sizing is insulated from small card-width changes caused by
  scrollbars and date-tab switching; genuine dashboard resizing may reframe
  the photograph. The card clips the image and blur rim to its rounded edge,
  and displays the attribution link.

## Asset rights and additions

The bundled images were sourced from reviewed **free Unsplash** photographs
under the applicable Unsplash License. The card does not download images or
fetch licensing metadata while running. See
[credits and source pages](mosque-background-credits.md) and the
[machine-readable provenance inventory](asset-provenance.json). Additional
photographs require individual attribution, source and redistribution-rights
review before bundling; a search-result licence label is insufficient.

The research alternatives remain:

- [Unsplash License](https://unsplash.com/license): use only permitted free
  photos; exclude paid/Unsplash+ items and competing standalone image libraries.
- [Wikimedia Commons reuse guidance](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia):
  verify each image's individual rights and satisfy attribution/share-alike
  requirements where applicable.
- [Pixabay terms](https://pixabay.com/service/terms/): do not assume that every
  current free item is CC0. The project's conservative legacy-CC0 review
  requires verifiable publication **before 9 January 2019**.
- [Pexels terms](https://help.pexels.com/hc/en-us/articles/900005880463-What-are-the-Terms-and-Conditions):
  additional redistribution review is needed before bundling standalone files.

Always distinguish the Al-Qibli Mosque from the wider Al-Aqsa compound when
naming images, and never imply a pictured mosque supplies the selected prayer
times.

## Validation

The 0.9.18 card and its photo-framing/accessibility tests passed
[PR #88 Validate](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012961)
and [CodeQL](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012733).
These are code and live Home Assistant acceptance checks, not an independent
legal opinion or certification of every physical device.
