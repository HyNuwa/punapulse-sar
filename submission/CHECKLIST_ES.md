# Checklist del equipo (hasta las 23:59)

## Ya (20 min)
- [ ] Crear el repo en GitHub (`punapulse-sar`, público) y subir todo este contenido.
- [ ] Settings → Pages → Deploy from branch → `main` / carpeta `/docs`. Abrir la URL y ver que carga el mapa.
- [ ] Generar el token en urs.earthdata.nasa.gov (Generate Token).

## Datos (60–90 min)
- [ ] Abrir `notebooks/PunaPulse_Colab.ipynb` en Colab y poner la URL del repo en la celda 1.
- [ ] Celda de búsqueda: anotar fechas, nivel de madurez (VALIDATED / PROVISIONAL / BETA) y tamaño.
  - Si hay menos de 2 fechas comparables: ampliar fechas (`--start 2026-06-01`) o aceptar PROVISIONAL.
  - Si no hay ninguna escena sobre el salar: avisar y cambiar de zona antes de seguir.
- [ ] Descargar con 2 o 3 escenas como máximo (pesan varios GB cada una).
- [ ] Procesar y mirar la vista previa. Si las piletas no aparecen en la máscara, probar `--dark-db -18` o `-16`.
- [ ] Dibujar 2 o 3 zonas en la app (campo de piletas, una vega, salar sin intervenir), pegarlas en `docs/data/zones.geojson` y volver a procesar.
- [ ] Bajar el zip de `docs/data` y subir su contenido al repo.

## Historia y entrega (60–90 min)
- [ ] Completar con números reales los `[ ]` de `submission/PROJECT_PAGE.md`.
- [ ] Grabar el video de ≤ 30 s (guion en `VIDEO_AND_SLIDES.md`), o armar ≤ 7 slides. En inglés o con subtítulos en inglés.
- [ ] Completar en el README y en el formulario cómo eligieron la idea (declaración de uso de SI).
- [ ] Enlaces públicos sin login: app, repo, video.
- [ ] Botón **Submit for Judging** antes de las 23:59 (hora del evento local). Apuntar a las 22:30.

## No hacer
- No mostrar datos simulados ni Sentinel-1 como si fueran NISAR.
- No decir "subsidencia de X mm" con un solo interferograma.
- No mezclar fechas BETA con VALIDATED en la misma comparación.
- No afirmar causas ("el bombeo secó la vega"): son hipótesis.
