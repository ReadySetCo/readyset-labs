# RS Strategy Tool — Simplificar la sección "Segments"
**Contexto para trabajar en Cowork. Objetivo: rediseñar cómo se modelan/muestran los segmentos y traer la solución de vuelta para implementarla.**

---

## 1. Qué es el tool (30 segundos)

App HTML single-file ("RS Strategy Tool") para estrategas creativos de Ready Set. Flujo: **Strategy Layer → Creative Roadmap → Strategy Sheet → Brief Maker**, con un mapa de calor de performance (testeado/no testeado/winners/oportunidades). La Strategy Layer define los bloques de conocimiento de la marca: Product, Value Props, Differentiators, **CTPs** (perfiles psicológicos), **Segments** (grupos demográfico-conductuales) y **Angles** (rutas de persuasión). En el roadmap se combinan: *"Test [CTP] in [Segment], through the [Angle] angle, at [Funnel] as an [Phase] play."*

## 2. El problema

La sección Segments de Stately quedó **muy larga: 19 segmentos**, casi todos variaciones de "hombre, 40s-50s, [conducta]". Problemas concretos:

- El **nombre duplica** lo que ya dicen las columnas Age/Gender/Behaviour ("Busy dads in their 30s and 40s" = age 30-40s + male + Busy Dads).
- Muchos se **superponen** (¿"Married, settled men 40s-50s" vs "Older, established men 50s" vs "White-collar professionals 40s-50s" son segmentos distintos o el mismo señor?).
- En el **roadmap builder** aparecen como 19 chips para elegir → parálisis de elección.
- En el **heat map**, 19 valores en un eje generan una grilla enorme y rala (casi todo "untested").
- La realidad del join con performance: la Strategy Sheet histórica de Stately usa solo **4 macro-segmentos** en la columna Segment: `BUSY, OVERLOADED, TIME-STARVED MEN` / `THE INSECURE OR SELF-CONSCIOUS GUY` / `LIFESTYLE & INTEREST-BASED` / `THE "LEVEL-UP" GUY` (+ uno suelto "Identity Transition Personas"). O sea: la data real ya vive en macro-grupos, y nuestra lista de 19 no matchea con nada.

## 3. Modelo de datos actual

```js
// cada segmento:
{ name:'Busy dads in their 30s and 40s',  // texto libre, es LA clave visible en todo el tool
  age:'30-40s', gender:'male', beh:'Busy Dads',
  val:'Validated' | 'Testing' | 'Not Tested',   // colorea el heat map (⭐ opportunity = validated × validated untested)
  src:'Client Brief' | 'Ad Performance Data' | 'Reddit/Forums' | 'Social Listening' | 'Market Research' }
```

UI actual: tabla editable de 6 columnas (Segment / Age / Gender / Behaviour / Validation / Source) + botón "Add segment". Hint: *"live independently — they get paired in the roadmap"*.

## 4. Los 19 segmentos actuales de Stately (seed)

| # | Name | Age | Behaviour | Val | Source |
|---|------|-----|-----------|-----|--------|
| 1 | Busy dads in their 30s and 40s | 30-40s | Busy Dads | Validated | Client Brief |
| 2 | Frequent traveler guys in their 40s and 50s | 40-50s | Frequent Traveler Guys | Validated | Reddit/Forums |
| 3 | New dads in their mid-30s to early 40s | mid 30s-early 40s | New dads | Testing | Reddit/Forums |
| 4 | Newly single men in their late 30s and 40s | late 30s-40s | Newly single | Validated | Ad Performance Data |
| 5 | Recently relocated urban guys in their 30s and 40s | 30s-40s | Recently relocated urban | Not Tested | Reddit/Forums |
| 6 | Fashion-forward urban guys in their 30s and 40s | 30s-40s | Fashion-forward urban guys | Not Tested | Reddit/Forums |
| 7 | Married, settled men in their 40s and 50s | 40s-50s | Married, settled men | Validated | Ad Performance Data |
| 8 | Blue-collar workers in their 40s and 50s | 40s-50s | Blue-collar workers | Testing | Social Listening |
| 9 | Budget-conscious guys in their 40s and 50s | 40s-50s | Budget-conscious guys | Validated | Social Listening |
| 10 | Older, established men in their 50s | 50s | Older, established men | Validated | Social Listening |
| 11 | Premium, high-spend guys in their 40s and 50s | 40s-50s | Premium, high-spend guys | Validated | Ad Performance Data |
| 12 | Golf and country club guys in their 40s and 50s | 40s-50s | Golf and country club guys | Testing | Market Research |
| 13 | White-collar professionals in their 40s and 50s | 40s-50s | White-collar professionals | Testing | Market Research |
| 14 | Younger workers in their early 30s (non-core) | early 30s | Younger workers | Testing | Market Research |
| 15 | Larger-build men in their 40s and 50s | 40s-50s | Larger-build men | Validated | Ad Performance Data |
| 16 | Men going through a weight change in their 40s and 50s | 40s-50s | Weight change | Testing | Client Brief |
| 17 | Style-novice men in their 40s and 50s | 40s-50s | Style-novice men | Validated | Ad Performance Data |
| 18 | Gym and fitness-focused guys in their 30s and 40s | 30s-40s | Gym & fitness-focused | Testing | Reddit/Forums |
| 19 | Health and wellness-focused men in their 40s and 50s | 40s-50s | Health & wellness-focused | Testing | Reddit/Forums |

## 5. Dónde se usa "segment" en el tool (todo lo que la solución tiene que seguir alimentando)

1. **Strategy Layer**: la tabla editable de arriba. Regla de completitud: la layer está "Complete" con ≥1 segmento con nombre.
2. **Roadmap builder**: chips para completar la oración *"Test X in [SEGMENT]..."* — el usuario elige 1 por lane.
3. **Heat map de performance**: Segment es eje seleccionable (X o Y) y filtro. La validación (`val`) decide el color de las celdas sin data: `Validated×Validated sin testear = ⭐ opportunity`.
4. **Strategy Sheet**: columna "Segment" (texto, editable) en cada fila exportada.
5. **Brief**: línea *"You'll be writing for **[segment]** — **[CTP]**, who [insight]"*.
6. **Glosario**: "Segment: The demographic/behavioural group used for casting and tone (age, gender, behaviour)."
7. **Join con performance real**: los dims vienen de la Strategy Sheet histórica por string exacto → hoy solo existen los 4-5 macro-segmentos listados en §2.

## 6. Restricciones / libertades

- **Se puede cambiar el modelo de datos** (agregar campos, jerarquía, lo que haga falta) — yo adapto el código después. No hay usuarios en producción; el localStorage se puede migrar o resetear.
- Los **CTPs quedan como están** (7, psicológicos). Ojo con no duplicar: varios "segmentos" actuales huelen a CTP disfrazado (Style-novice ≈ Never Learned Fashion, Premium high-spend ≈ Status Climber).
- El segmento sigue siendo lo que define **casting y tono** en el brief (edad/género/conducta).
- Tiene que seguir funcionando como **eje/filtro del heat map** con pocos valores (ideal: 4-8) y con estado de validación.
- Idealmente los nombres finales **matchean o mapean** a los macro-segmentos de la Strategy Sheet histórica (§2) para que el join de performance funcione sin tabla de traducción… o la solución incluye esa tabla de mapeo.
- Vale pensar en jerarquía: **macro-segmento** (el que se elige en roadmap/heat map) + **sub-segmentos/descriptores** (los 19 actuales como detalle de casting dentro de cada macro). Es una opción, no un mandato.

## 7. Qué traer de vuelta (formato de la solución)

Para implementarlo directo, lo ideal es que la solución diga:

1. **Lista final de segmentos** (nombre corto para chips/ejes + descripción de casting si hay jerarquía).
2. **Mapeo**: cada uno de los 19 actuales → a qué segmento final pertenece (y a cuál macro-segmento histórico de la sheet mapea).
3. **Modelo de datos propuesto** (campos por segmento; si hay macro/sub, cómo se anidan).
4. **Cómo se ve la UI**: la tabla de la Strategy Layer (¿qué columnas quedan?), y qué se muestra en chips del roadmap, heat map y brief.
5. **Estado de validación**: cómo se hereda/agrega si un macro tiene subs con validaciones mixtas.

Con eso vuelvo al chat principal y lo implemento en `rsstrategytool.html`.
