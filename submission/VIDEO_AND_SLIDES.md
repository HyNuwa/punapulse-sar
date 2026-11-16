# 30-second demo video + 7-slide alternative

The official limit, per secondary copies of the 2026 guide, is **≤ 30 s of video OR ≤ 7 slides**, in English or with English subtitles. Check it on the live site. Going over the limit can make the project ineligible for global judging.

## Video script (30 s, screen recording of the live app)

| Time | On screen | Voice-over (EN) | Subtítulo / versión ES |
|---|---|---|---|
| 0:00–0:07 | Globe → zoom to Jujuy → salar outline over optical imagery | "High in Argentina's Puna, lithium brine is evaporated in huge ponds. How fast is the surface changing, and how can anyone check?" | "En la Puna jujeña, la salmuera de litio se evapora en piletas enormes. ¿Qué tan rápido cambia la superficie y cómo puede verificarlo cualquiera?" |
| 0:07–0:17 | Turn on NISAR composite, drag the swipe from first to last date; zone card shows hectares | "PunaPulse SAR uses NASA-ISRO NISAR radar, through cloud and dust. In one year, the salar's wet surface swelled by a third with the summer rains, and the southern pond field ended the dry season with 378 more dark hectares." | "PunaPulse SAR usa el radar NISAR de NASA e ISRO, a través de nubes y polvo. En un año, la superficie húmeda del salar creció un tercio con las lluvias de verano, y el campo de piletas del sur terminó la época seca con 378 hectáreas oscuras más." |
| 0:17–0:25 | Change map on; chart with dark area vs rain | "Change maps and rain context help separate industrial change from the climate. Every layer is labelled: observed, derived or hypothesis." | "Los mapas de cambio y la lluvia ayudan a separar el cambio industrial del clima. Cada capa dice si es observación, derivado o hipótesis." |
| 0:25–0:30 | Draw a zone; GitHub + URL card | "Open source: draw your own zone, for any salar. PunaPulse SAR." | "Código abierto: dibujá tu zona, en cualquier salar." |

Tips:
- Record at 1080p.
- Use real numbers from `manifest.json`; if a number is not ready, cut that sentence rather than guess.
- If the video contains SI-generated voice or imagery, the rules ask for a visible watermark or label. Recording your own voice avoids that.

## 7-slide alternative

1. **Title**: PunaPulse SAR · team · Space Apps 2026 · *Dancing with the SARs*.
2. **Problem**: lithium brine ponds in a fragile, very dry high-Andean basin; communities and regulators lack open, repeatable surface data. Map of the salar.
3. **Why NISAR**: L-band, every 12 days, day/night and all-weather. Roughness and moisture. Calm brine = dark. One annotated image.
4. **How it works**: ASF search → consistent stack → GCOV HH/HV → mask, change map, hectares per zone → static web app.
5. **Results**: swipe screenshot plus the numbers `[ha change]`, `[dates]`, chart against rain.
6. **Honest limits and hypotheses**: smooth crust vs brine; one interferogram ≠ subsidence rate; data maturity; evidence labels.
7. **Impact and next steps**: open monitoring for communities and regulators, InSAR time series, SAOCOM, field validation. Links to the app and repo.
