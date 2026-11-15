# Tarea: filtros de cambios en la vista de análisis

## El problema

Un análisis puede devolver cientos o miles de polígonos. Muchos son pequeños y débiles: manchas de pocas hectáreas cerca del umbral, repartidas por toda la escena. En el mapa se ven como ruido disperso y tapan las áreas que importan.

El objetivo es que el usuario pueda quedarse con lo relevante: **las áreas grandes, intensas y de la dirección que le interesa**. El mapa y la lista deben mostrar exactamente lo mismo.

## Lo que ya existe (no rehacer)

**En el backend, al analizar:**
- Descarta los polígonos de menos de 0,01 km² (`minimum_area_km2`).
- Aplica un filtro de mediana 5×5 contra el speckle y una limpieza morfológica que quita los grupos de menos de 4 píxeles.
- El asistente pide un umbral de 3σ (`change_threshold_sigma: 3`).

**En la vista de análisis** (`frontend/src/observatory/AnalysisPage.tsx`):
- **Por tipo de cambio:** cada fila de "Qué tipo de cambio" se enciende y se apaga. Usa el estado `hidden` y se aplica al mapa y a la lista.
- **Mostrar u ocultar todas las áreas:** casilla "Mostrar las áreas detectadas" (`showPolygons`).
- **Orden de la lista:** por tamaño o por intensidad (`order`).

**En la API**, cada polígono ya trae lo necesario para filtrar:

| Propiedad | Significado |
|---|---|
| `area_km2` | Área geodésica del polígono |
| `change_score` | Intensidad relativa de 0 a 1. Vale 0 en el umbral, 0,5 al doble y 0,75 al cuádruple. **No es una probabilidad** |
| `direction` | `DECREASE` = la superficie se oscureció · `INCREASE` = se aclaró |
| `change_type` | Tipo tentativo (`POSSIBLE_FLOODING`, `POSSIBLE_BURN_SCAR`, …) |
| `mean_change_db` | Cambio medio en dB, con signo |

`GET /changes` y `GET /changes/geojson` ya aceptan `min_area_km2`, `min_score`, `direction` y `change_type` (repetible). En el front, `changesService.page(filtros)` y el tipo `ChangeFilters` (`src/types/change.ts`) ya los incluyen. Ver `docs/api.md`, sección "Cambios: listado, filtros y capas de mapa".

## Lo que hay que hacer

### 1. Controles en el panel izquierdo

Agregar un bloque "Filtrar áreas" en `AnalysisPage.tsx`, debajo de "Qué tipo de cambio", con:

- [ ] **Área mínima.** Opciones fijas en vez de un deslizador libre, por ejemplo: `Todas` · `≥ 0,1 km²` · `≥ 0,5 km²` · `≥ 1 km²`. Los intervalos del histograma de `insights` (`< 0,05`, `0,05–0,1`, `0,1–0,5`, `0,5–1`, `1–5`, `> 5` km²) sirven de guía. Es el filtro que más limpia la dispersión.
- [ ] **Intensidad mínima.** Por ejemplo: `Todas` · `Moderada (≥ 0,3)` · `Alta (≥ 0,6)`. Usar las mismas palabras que la función `significance()` de `lib.ts`, que ya traduce el score a "Baja / Moderada / Alta".
- [ ] **Dirección.** `Ambas` · `Se oscureció` · `Se aclaró`. Usar los colores del sistema: rojo `#c8322a` para oscureció y azul `#3f6fb0` para aclaró.
- [ ] Un texto con el resultado, por ejemplo **"Se muestran 23 de 80 áreas"**. El total filtrado sale de `changesService.page(...).total` (cabecera `X-Total-Count`).
- [ ] Un botón **"Quitar filtros"** cuando haya alguno activo.

Para los grupos de opciones conviene reusar el control `.segmented` que ya existe (el de Comparar / Cambio / Antes / Después).

### 2. Aplicarlos al mapa

En `frontend/src/observatory/CompareMap.tsx`, el efecto marcado con "Mode, polygon visibility, type filter and selection…" ya filtra por tipo con `map.setFilter`.

- [ ] Agregar props nuevas a `CompareMap`, por ejemplo `minArea`, `minScore` y `direction`, y combinarlas con el filtro de tipo en una sola expresión:

```ts
const visible: FilterSpecification = [
  "all",
  ["!", ["in", ["get", "change_type"], ["literal", hiddenTypes]]],
  [">=", ["get", "area_km2"], minArea],
  [">=", ["get", "change_score"], minScore],
  ...(direction ? [["==", ["get", "direction"], direction]] : []),
] as FilterSpecification;
```

- [ ] Aplicarla a `changes-fill` y `changes-line` en **los dos mapas** (`pair.after` y `pair.before`), igual que hoy.
- [ ] Es un filtro del lado del cliente sobre los tiles vectoriales: es instantáneo y no hace más peticiones.

### 3. Aplicarlos a la lista

- [ ] En la consulta `list` de `AnalysisPage.tsx`, pasar los filtros a `changesService.page({ job_id, sort, limit, change_type, min_area_km2, min_score, direction })`.
- [ ] Incluir los filtros en el `queryKey`, por ejemplo `["job", id, "changes", order, shown, minArea, minScore, direction]`, para que la lista se recargue al cambiarlos.
- [ ] Si el polígono seleccionado (`selected`) queda fuera del filtro, cerrar su panel o avisar.

### 4. Cifras coherentes

El resumen de arriba ("74,2 km² con cambios, en 80 áreas") y los totales de cada tipo vienen de `GET /jobs/{id}/insights`, que **no recibe filtros**. Hay que elegir una de dos:

- **A (más simple):** dejar esas cifras como "del análisis completo" y mostrar aparte "Se muestran N de M áreas".
- **B:** recalcular área y conteo filtrados en el front a partir de `changesService.page` con `limit` alto (hasta 1000).

Recomendado: **A**. Lo que no puede pasar es que el mapa muestre 23 áreas y el resumen siga diciendo 80 sin explicación.

### 5. Guardar los filtros en la URL

- [ ] Guardarlos como parámetros, por ejemplo `/analisis/:id?area=0.5&intensidad=0.3&direccion=DECREASE`, con `useSearchParams`, igual que hace `ExplorePage.tsx` con `?lat&lon&dias&radio`. Así un enlace compartido abre el mapa ya filtrado.

## Lo que el filtro no cubre

- **El modo "Cambio"** dibuja el raster `difference`: todos los píxeles que superaron el umbral, sin polígonos. Ese raster **no se puede filtrar** desde el front y seguirá mostrando todo. Conviene una nota corta en ese modo, algo como "Los filtros se aplican a las áreas, no a esta capa".
- **El comparador del inicio** (`HomePage.tsx`, `CompareMap` con `bare`) no lleva filtros.

## Reglas del diseño

- La menta `#a1ffcb` solo significa "seleccionado". No usarla para indicar que un filtro está activo; para eso, el estado presionado del `.segmented` (fondo tinta).
- El rojo y el azul son solo para la dirección del cambio.
- Las cifras van con la clase `num` (Geist Mono).
- Textos en español y sin presentar el tipo de cambio como un hecho: siempre "posible".

## Cómo comprobarlo

1. `docker compose up -d` y abrir un análisis terminado, por ejemplo el del Trapecio Amazónico o el del Delta del Krishna desde el inicio.
2. Subir el área mínima: el mapa debe perder los polígonos pequeños y la lista y el contador deben bajar en la misma medida.
3. Elegir "Se oscureció": solo deben quedar polígonos con `direction = DECREASE`. En la lista, todos con el valor en dB en rojo.
4. Recargar la página: los filtros deben seguir aplicados.
5. `docker compose exec frontend npm run typecheck` sin errores.

## Coordinación

- Trabajar en una rama propia. `AnalysisPage.tsx` y `CompareMap.tsx` también los va a tocar quien haga **los gráficos** y **la evidencia en el mapa** (ver `docs/pendientes-frontend.md`). Avisarse antes de cambiar la estructura de esos archivos.
- Si hace falta un filtro nuevo en la API (por ejemplo, por dB), pedirlo a quien lleva el backend: hoy no existe.
