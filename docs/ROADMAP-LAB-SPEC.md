> ⚠ **Este documento describe el SANDBOX del rediseño del Creative Roadmap (roadmap-lab).**
> Toda cifra de performance/confianza mencionada acá (p.ej. "Dating Dude 36%") sale de un **ledger MOCK del lab**, calibrado contra agregados reales pero con conceptos inventados — NO es data de producción. El lab HTML no se sube al repo por eso mismo: Evan y los usuarios deben ver solo información real (la del tool vivo). Los pasos 1–4 del FINAL SPEC ya están integrados en `rsstrategytool.html`; los 5–8 esperan el cableado a data real (§6.3).

# Roadmap Lab — rediseño del Creative Roadmap maker (sandbox)

> **Instrucción para el chat que trabaje este lab:** este es un sandbox INÓCUO — la app viva (`Claude Code Context/strategy-os/rsstrategytool.html`) **no se toca desde acá**. Se itera sobre `roadmap-lab.html` (lógica + UX + visualización), commiteando cada iteración en el git local de esta carpeta (prefijo `lab:`) para poder ir para adelante y para atrás. Al terminar, se escribe la sección **FINAL SPEC** abajo y Felipe le avisa al chat principal, que integra el resultado en la app viva (ese es el "push"). Mantener este doc actualizado con las decisiones.

**Last updated:** 2026-09-07 — **INTEGRADO (pasos 1–4) en la app viva** por el chat principal: commits `5298772` (composer), `0997897` (tesis+contrato), `510135f` (mapa), `5d95b2e` (export hub) en strategy-os. Pendientes de integración: pasos 5–8 (§6.6) esperando data real. **LAB CERRADO.** (iteraciones 1–8 hechas: tesis, visualizador de dimensiones, sugerencias, composer rápido, mapa de subte, archivo de roadmaps. Spec en §6 en estado BORRADOR — falta el OK de Felipe.)

## 1. Qué es esto

Felipe quiere probar otras estructuras/visualizaciones para el **Creative Roadmap maker** sin arriesgar el tool vivo (que además lo editan dos chats en paralelo, con git propio en `strategy-os/`). `roadmap-lab.html` es un HTML standalone con:

- **Data real de Stately** (extraída del tool el 2026-09-06): 11 personas del cliente (con tag e insight), 5 segmentos demográficos con su casting[], 30 angles, funnels y phases reales.
- **Baseline v0 = copia fiel de la lógica actual del builder**: oración componible ("Test [CTP] in [Segment], through the [Angle] angle…"), chips con tooltips, hypothesis obligatoria, concepts/variants, Suggested casting (multi, del menú del segmento) + Suggested format (multi), notas, add/edit/delete lanes, Consolidate con período, vista de roadmap consolidado, dark/light.
- Estado propio en localStorage (`roadmap-lab-v1`), botón **Reset** y botón **📤 Export lanes JSON** (copia el JSON con la forma exacta del contrato).

## 2. EL CONTRATO — lo que la integración final necesita

El resto de la app consume el roadmap con esta forma. La UX puede cambiar TODO lo demás; esto es lo que tiene que salir del builder (o venir con una tabla de migración explícita en el FINAL SPEC):

```js
roadmap = {
  title: 'October 2026 — Stately Creative Roadmap',
  period: 'October 2026',            // lo pregunta el consolidate
  consolidatedAt: ISOstring,
  lanes: [{
    ctp: 'The Effort Minimizer',     // NOMBRE de persona (la UI nunca muestra tags; el export a sheet traduce a p-effort)
    segment: 'Core 40s',             // nombre del segmento
    angle: 'Save Time',
    funnel: 'TOFU'|'MOFU'|'BOFU',
    phase: 'Explore'|'Exploit'|'Amplify',
    hypothesis: string,              // OBLIGATORIA — es lo que hace que sea un test
    concepts: int >= 1,
    variants: int | '',              // '' = sin decidir
    notes: string,
    castings: string[],              // subset del casting[] del segmento elegido — sugerencia, NO variable
    formats: string[],               // subset de VID/STA/GIF/CAR/THU
    delivery?: int                   // lo agrega el export (D#), no el builder
  }]
}
```

**Consumidores aguas abajo (en la app viva):**
- **Export → Strategy Sheet**: expande lanes a filas D#/C#/V## (delivery por lane, concepts secuenciales, variants), CTP→tag, castings/formats: si hay UNO solo pre-llena Talent/Format, si hay varios quedan para asignar por fila (desplegables en la sheet).
- **Brief Maker**: hereda por concepto ctp (con insight y clothing persona), segment (con age+casting), angle, funnel, phase, hypothesis, notes, talent/format o el "pick from".
- El heat map NO lee del roadmap (lee de la sheet + performance).

**Reglas de producto que la nueva UX debe conservar:**
- Hypothesis obligatoria por lane.
- Casting ≠ variable de testeo (es quién sale en cámara; para testear se promueve a segmento). El hint puede cambiar de forma, no de mensaje.
- La UI muestra nombres de persona, nunca tags.
- Campos ADITIVOS son bienvenidos (la integración los puede adoptar); RENOMBRAR o eliminar campos requiere tabla de migración en el FINAL SPEC.

## 3. Libertades

Todo lo visual y estructural: pasos vs canvas, oración vs tabla vs kanban vs matriz, drag & drop, agrupación por delivery, vista de calendario, resumen de cobertura (qué celdas del heat map toca este roadmap), duplicar lanes, templates, lo que sea. También la lógica interna del builder (el shape del `comp` intermedio es libre — solo el output del contrato importa).

## 4. Workflow

1. Iterar sobre `roadmap-lab.html`. **Commit por iteración**: `lab: <qué probaste>` — así Felipe va adelante/atrás con `git checkout <hash> -- roadmap-lab.html` o compara con `git diff`.

   | commit | qué es |
   |---|---|
   | `2d9cde7` | v0 — copia fiel del builder vivo |
   | `ab0a81e` | it1 — tesis + visualizador de dimensiones (motor PLS) + sugerencias |
   | `2205aed` | it2 — mapa de subte + delivery como terminal + numeración de conceptos |
   | `f769d9e` | it3 — composer rápido (multi-select → batch) + casting/format por concepto |
   | `1039e3a` | it4 — archivo de roadmaps con resultados |
   | `a86326c` | it5 — período con duración + conceptos contratados por mes |
   | `631e232` | it6 — período en semanas + calendario de producción (Creative Menu) |
   | `34e35cd` | it7 — flags layer-vs-evidencia + hub de export (5 formatos) |
   | `b799c1a` | it8 — one-pager presentable |
   | `4083608` | it8b — la tesis sigue editable después de consolidar |
2. Variantes en paralelo: copiar a `roadmap-lab-B.html` o usar branches, lo que resulte cómodo.
3. Decisiones y descartes se anotan acá (sección 5).
4. Al cerrar: escribir **FINAL SPEC** (§6) — qué cambió, mapa de campos si difiere del contrato, y qué archivo/commit es la referencia final. Felipe avisa al chat principal y este integra en `rsstrategytool.html` (repo `strategy-os/`, commit `main: roadmap redesign from lab`).

## 5. Decisiones tomadas

Dirección elegida por Felipe (2026-09-06): las tres opciones juntas, en fases, con su propia visión encima. El roadmap deja de ser una lista de lanes y pasa a ser **una tesis + una base de datos visualizada + una red de líneas en el tiempo**.

### 5.1 La tesis del roadmap (it1)
Todo roadmap tiene una hipótesis general que reina sobre las lanes y explica la maduración: de dónde viene y a dónde va. Se agregó una tarjeta arriba de todo con `title` (el nombre de la apuesta), `text` (por qué ahora), `from` y `to`. **Es aditivo al contrato** (`roadmap.thesis`), no reemplaza nada.

### 5.2 El visualizador de la base de datos (it1)
Tabla por dimensión (CTP / Segment / Angle / Funnel / Phase) con: estado del Strategy Layer, **cómo se fue llenando** (un punto por concepto shippeado, verde si superó el benchmark, rojo si no), **Confidence**, **Effect** y **Trigger**.

- El motor de Confidence es el del **PLS simulator**, portado tal cual desde `performance-learning-simulator/index.html`: `confFromUnits(u)=100·(1−e^(−u/4))`, `SUMMARY_W {attention .25, interest .25, business .5}`, `ENT_MULT {combo 1.0, pair 0.7, ctp 0.4, angle 0.25, funnel 0.15}`, `INDEP [1, 0.35, 0.35]`, `adScores()` y `recommend()`. Único agregado: las entidades `segment` (peso 0.4, como CTP) y `phase` (0.15, como funnel), que el simulator no modelaba.
- **Hallazgo importante:** los umbrales del simulator (`effect ±25`) estaban calibrados para swings sintéticos grandes. Con data de escala real **todas** las dimensiones daban "Explore" y la columna no decía nada. Se recalibró a **±8** en una const `THRESH` para que quede tuneable por marca. Un efecto ponderado de +10 en Stately equivale a una persona corriendo ~20% mejor de CPA que el benchmark de la cuenta: eso sí es señal de decisión.
- Lectura que sale de esto y que vale para el pitch del PLS: después de 6 meses y $523k, la persona mejor conocida (Dating Dude) está en **36% de confianza**, y cinco personas tienen **cero evidencia**. El roadmap existe justamente para llenar eso.

### 5.3 Sugerencias de testeo (it1)
Tarjeta "Where the next test should go", leída de la evidencia, no de una lista fija. Reglas: **Confirm** (efecto positivo pero fino — la confianza más barata disponible), **Investigate** (atención sin negocio), **⭐ nunca combinados** (por evidencia de ambos lados, más las marcas `Validated` del Layer como segunda fuente), **↔️ transferencia** (un angle que solo corrió sobre una persona está confundido con ella), **🕳 puntos ciegos** (dimensiones sin ninguna evidencia). Cada sugerencia carga el composer. Tiene Hide/Show.

### 5.4 El composer rápido (it3)
- Cada dimensión guarda un **array**. Elegir 2 personas × 3 angles compone **6 swimlanes de una pasada** — esto es lo "ágil para testeos amplios y no unidimensional".
- Secciones apiladas en vez del wizard lineal: una sección está abierta mientras no elegiste nada (seguís eligiendo) o mientras la abriste a propósito (estás agregando un segundo valor). El camino simple sigue siendo 5 clics.
- Filtro de texto en Angle (30 opciones), Enter elige el primero.
- Los chips muestran el % de confianza de esa dimensión; el tooltip trae el trigger y su porqué. La elección se hace contra la evidencia, no a ciegas.
- Panel **"What this batch will teach"**: proyecta la ganancia de confianza por dimensión tocada, sumada sobre todas las lanes que va a emitir. Deja explícito que N variantes valen `1+0.35(N−1)`, no N — es el argumento visual de por qué conviene un concepto independiente más y no tres variantes.

### 5.5 Casting y formato POR CONCEPTO (pedido de Felipe, it3)
Al fijar la cantidad de conceptos, el composer pide un **suggested casting + format por cada concepto** (con atajos "aplicar el de C1 a todos"). Se guarda en `lane.conceptSpecs[]`, alineado con `conceptNums`. `lane.castings` / `lane.formats` **siguen existiendo en el contrato** como la unión deduplicada, así la regla del sheet ("uno → pre-llena, varios → se asigna por fila") sigue funcionando sin cambios mientras el roadmap ahora dice exactamente qué concepto lleva qué. En un batch multi-segmento el menú es la unión, y un casting que no pertenece al segmento de una lane **se descarta de esa lane** en vez de asignarse mal en silencio.

### 5.6 El mapa de subte (it2)
- Una swimlane = **una línea**. Estaciones en orden: CTP → Segment → Angle. Un valor compartido por dos lanes es **un solo nodo** → intercambio real (estación hueca, "⇄ 2 lines"). Eso hace visible el solapamiento: dos líneas que pasan por la misma estación heredan la evidencia una de la otra y ninguna se puede leer sola.
- Después del Angle la línea **se abre en sus conceptos** (C###), cada uno con su casting/formato.
- **El delivery es la terminal de la línea.** Una línea lleva un solo delivery; correr el mismo test en otro delivery = **duplicar la línea** (botón). Es además el modelo honesto: la copia es evidencia independiente.
- Funnel y Phase **no son estaciones** (modifican la línea entera): van debajo de la terminal.
- Numeración de conceptos: escribís el primero (`roadmap.conceptStart`, default 235 = el siguiente al último del ledger) y el resto sigue en escala, ordenado por delivery.
- Cada estación muestra lo que la cuenta ya sabe de esa dimensión (confianza + efecto), así el mapa sirve también como lectura de cobertura.
- Layout: y del nodo = promedio de las lanes que pasan por él, separadas a `MIN_GAP`; codos a 45°; offset paralelo donde varias líneas comparten tramo; halo de recorte en los textos para que los nombres se lean sobre las líneas. Paleta TfL.

### 5.7 El archivo de roadmaps (it4)
- Los roadmaps **se concatenan y se almacenan**. La franja de períodos muestra una tarjeta por período con su CPA contra el benchmark (Jun $388 → Jul $417 → Aug $441, que es la deriva real de Stately) más una tarjeta punteada de "now".
- Al abrir un período se dibuja **la misma red** con el resultado pintado encima: estación de concepto **verde** (superó el benchmark), **roja** (perdió), **gris** (sin lectura), con su CPA y su spend. El tooltip da purchases, CPA vs bench y efecto ponderado.
- Los roadmaps pasados se reconstruyen agrupando los conceptos shippeados de vuelta en las swimlanes de las que salieron, así lo que ves es lo que realmente corrió. En la app viva esto lee el Strategy Sheet + performance en vez del ledger.

### 5.8 Data de performance en el lab
`LEDGER` = 22 conceptos mock, **marcados como LAB-ONLY en el código**, calibrados contra el pull real de Motion de 6 meses: CPA de cuenta $416 vs $415 real, y spend/CPA por persona dentro de un par de puntos (Dating $143k/$418, Deal $127k/$377, Executive $103k/$465, Effort $96k/$397, Casualist $29k/$365, Perfect Fit $25k/$668). Los conceptos son inventados porque los ads reales taggeados con `p:` **no traen segment ni angle** — hacía falta que cada fila tuviera las dimensiones completas para que el motor tuviera algo que masticar. En la integración este const se reemplaza por la lectura de la data viva.

### 5.10 Período y capacidad contratada (it5, pedido de Felipe)
El roadmap ahora tiene **tiempo** y **presupuesto**, no solo orden.

- **Período con duración**: selector de mes + cuántos meses abarca. De ahí sale el label (`October 2026`, o `October 2026 – December 2026`). El `consolidate` ya no pregunta el período por `prompt()`: lo toma de acá.
- **Capacidad contratada**: `conceptos/mes` por marca. Viene del **deal de HubSpot** pero **es editable**, porque la capacidad real del mes depende de la estrategia vigente (un mes cargado de Amplify compra menos conceptos nuevos que un mes de Explore del mismo tamaño). Cuando el estratega la pisa, la UI dice `overridden from 12` con un link para restaurar — nunca se pierde de vista cuál es el número contractual.
- **Capacidad = conceptos/mes × meses del período.** La barra muestra `planificados de contratados` y avisa en rojo cuando te pasaste (`3 concepts over contract — cut a lane, or agree the overage before it reaches production`) y en gris cuánto te falta comprometer.
- **La unidad es el CONCEPTO, no el ad.** Las variantes no cuentan contra el contrato — está dicho explícitamente en la UI porque es la confusión obvia.
- El `consolidate` ahora confirma si el roadmap está por encima o por debajo del contrato, en vez de dejarlo pasar en silencio.
- La franja del archivo muestra los conceptos de cada período pasado, así se ve si históricamente se entregó de más o de menos.

⚠ En el lab el número es un **placeholder** (`CONTRACT_SRC = 12 conceptos/mes, Stately — 360 retainer`), marcado como tal en el código y en el tooltip de la UI. No consulté HubSpot: hace falta saber qué propiedad del deal guarda el volumen contratado (ver §6.3).

### 5.11 Período en semanas + calendario de producción (it6, pedido de Felipe)

**El período ya no es un mes.** Ahora es **fecha de inicio + cantidad de semanas** (1 a 52). El label sale solo (`Oct 1 – Oct 28, 2026 · 4 weeks`) y la capacidad contratada se **prorratea**: `conceptos/mes × semanas / 4.345`. Un roadmap de 4 semanas contra un contrato de 12/mes da 11 conceptos, no 12.

**Ruta de producción por concepto.** Se agregó una tercera columna en la tabla de conceptos: la **ruta del Creative Menu**. El `MENU` const está levantado literal de `Creative Menu/CreativeMenu.html` (el array `SERVICES`): 12 rutas con su timeline, su costo base y el equipo que la hace.

- Lectura del timeline a **días hábiles**: tomé el **extremo pesimista del rango base** (`1-2 days` → 2, `2-4 weeks` → 20, `3+ weeks` → 15), porque un plan armado sobre el extremo optimista no es un plan. Las rutas que el Menu tiene en TBD o PARKED quedan con `bd:null`: no se pueden agendar y el calendario lo dice en vez de adivinar.
- **El formato del ad NO determina la ruta.** Un VID puede ser un Editor Ad de $250 en 3 días o un Creator bundle de $2.500. Por eso solo los formatos de diseño inequívocos (STA/GIF/CAR/THU) proponen ruta automática, y **VID queda en blanco a propósito** hasta que alguien elija — para que nadie termine con un cronograma construido sobre una suposición.

**Calendario de producción.** Una fila por delivery sobre las semanas del período:
- Cada delivery tiene **fecha de entrega**, repartida pareja sobre el período por default (y siempre cayendo en día hábil), editable.
- La barra es **la ruta más larga de ese delivery contada hacia atrás desde la entrega**, con los días hábiles convertidos a calendario a 5 por semana. Si el trabajo tendría que empezar **antes de que abra el período**, la barra se pone roja y el pie lo dice: eso es un delivery imposible, no uno apenas tarde.
- Pie con totales: días hábiles de producción, costo base del Menu, cuántos conceptos siguen sin ruta.

⚠ **Son estimaciones del Menu, no cycle time medido.** Está dicho en el código y en la UI. El punto de Felipe queda en pie: el número que importa es **lo que realmente tarda hoy un concepto en Ready Set**, y eso tiene que venir de data de producción (Monday / la sheet), no de los turnarounds cotizados. Esto es el andamio para enchufarlo.

### 5.12 Layer vs evidencia, y el hub de export (it7, pedido de Felipe)

**El ⚠ de desacuerdo.** La columna `LAYER` es un campo **manual** del Strategy Layer; confidence y effect son **calculados** de lo que se shippeó. Se separan, y cuando se separan el que suele estar viejo es el manual. Ahora la tabla lo marca en tres casos:

- **`⚠ stale`** — el layer dice *Not Tested* pero ya hay conceptos shippeados. Es el caso de las 11 personas de Stately: la migración de taxonomía del 6/9 las bajó a *Not Tested* y nadie las volvió a marcar, mientras la producción siguió corriendo. **Esta era la pregunta de Felipe** y la respuesta es que no es un bug de lectura: son dos fuentes que no se hablan.
- **`⚠ over`** — dice *Validated* pero la evidencia da menos de 35% de confianza. O la validación se apoya en data que este motor no ve, o es una creencia y no un hallazgo. Vale saber cuál antes de apostarle un delivery.
- **`✓ ready`** — sigue en *Testing* con efecto positivo y ≥45% de confianza: candidato a promover.

Arriba de la tabla aparece un contador (`⚠ 6 rows where the layer and the evidence disagree`) y el estado es **clickeable**: cicla Not Tested → Testing → Validated y queda en itálica subrayada mientras difiera del layer. En el lab eso vive en `S.valOverride`; **en la app viva tiene que escribir el Strategy Layer de verdad**, no un override local.

**El hub de export.** Felipe pidió explícitamente que el export **no sirva solo para la Strategy Sheet**. Un roadmap lo consumen audiencias muy distintas, así que son cinco formatos sobre la misma espina dorsal (`conceptList()`, una fila por concepto):

| Formato | Para quién | Qué sale |
|---|---|---|
| 📊 **Strategy Sheet** | la spreadsheet, mientras siga viviendo ahí | Las **31 columnas exactas** del tool vivo (`SHEET_COLS`/`SHEET_KEYS`, `rsstrategytool.html:213`), una fila por variante. TSV para pegar directo en Google Sheets, o descarga .csv |
| 🛠 **Production plan** | PM / Monday | Una fila por concepto: ruta del Menu, equipo, días hábiles, costo base, fecha de entrega y **la fecha en que tiene que empezar** (contada desde su propia ruta, no la del delivery) |
| 📝 **Brief payload** | el Brief Maker | Un objeto por concepto con la estrategia **resuelta**: insight y clothing persona de la CTP, edad y menú de casting del segmento, angle, funnel, phase, hipótesis, notas, casting, formato y ruta |
| 📄 **Readable roadmap** | Slack / Notion / el cliente | Markdown: la tesis, los deliveries con sus fechas, cada swimlane como su oración + hipótesis, los conceptos con casting/formato/ruta, y una tabla de **qué va a enseñar el roadmap** (confianza ahora → después) |
| `{ }` **Contract JSON** | la app | El objeto tal cual lo consume la integración (§6.1) |

Decisión de fondo en el export a la sheet: **las columnas que el roadmap no sabe se van en blanco a propósito** (Concept Name, links y fechas de brief/footage/scripts, Visual Hook, Visual Style, Offer Type, Variation Final Name, Sizes, Owner, Target Platform, Product). Inventar valores en una planilla sobre la que trabaja el equipo es peor que dejar la celda vacía. Y lo que sí mejora respecto del export actual del tool vivo: **Format y Talent salen por concepto** (no por lane) y **Delivery Due Date sale del calendario de producción**.

### 5.13 El one-pager (it8, pedido de Felipe)
Sexto formato del hub: una **página HTML standalone, sin dependencias, imprimible a una hoja A4 apaisada**. Lleva la tesis, los números, el mapa de subte y los tests — **el argumento, no el banco de trabajo**. Todo lo que el lab usa para trabajar (triggers, sugerencias, archivo, calendario) queda afuera a propósito.

Contenido, en orden: título y período · la tesis con su `de dónde viene → a dónde va` · seis números (tests, conceptos vs contratados, ads con variantes, deliveries, días de producción, costo base del Menu) · **el mapa de la red** · cada test como su oración con la hipótesis y sus conceptos (C#, formato, casting, ruta del Menu) · y **“What this roadmap will know that we don't know today”**: la tabla de confianza ahora → después, que es la única forma honesta de decir para qué sirve un roadmap.

Dos detalles de implementación: `vTube(lanes,{raw:true})` devuelve solo el `<svg>` para poder incrustarlo, y el CSS del one-pager es propio y con colores literales (no usa las variables del tema) porque tiene que imprimirse igual en cualquier lado. El pie lleva una marca visible de que la confianza sale del ledger **mock** del lab y no de data de producción — si esta página se comparte, no puede pasar por dato real.

Botones: **Copy**, **Download .html** y **Open & print** (abre en una ventana nueva y dispara el diálogo de impresión → Guardar como PDF).

### 5.14 La tesis sigue editable después de consolidar (it8b)
**Agujero encontrado al revisar:** el título, la descripción y el `from → to` se editaban en el builder, pero al **consolidar** el roadmap pasaban a solo lectura. Para corregir un typo en el título de lo que estabas por presentar tenías que apretar *Change Roadmap*, que desconsolida todo el roadmap.

Arreglado: la vista consolidada usa **la misma tarjeta editable** (sin la franja de período/contrato, que sí queda congelada). `setTh()` escribe en la tesis de trabajo **y** en la copia consolidada, y recompone `roadmap.title`, así el cambio llega a los seis formatos de export. La cabecera consolidada ahora es una chapa verde `🗺️ Consolidated` con período, cantidad de swimlanes y fecha de bloqueo, más los botones Export y Change Roadmap — sin repetir el título, que ya está en la tarjeta.

De paso: el one-pager toma el **título corto** de la tesis y no el largo del roadmap consolidado — el eyebrow ya dice la marca y la píldora el período, así que el título largo repetía las dos cosas en el titular.

### 5.9 Descartes / notas
- Se descartó el auto-avance de pasos del wizard: peleaba con la multi-selección (elegir una persona te sacaba de la sección antes de poder elegir la segunda).
- El preview del navegador no puede servir esta carpeta (sandbox de `~/Downloads`), así que el lab tiene un botón **▶ Demo** que carga un roadmap de octubre ya armado. Sirve para testear y para mostrar.
- Bug encontrado y arreglado en el camino: al reescribir el composer se perdió `nextDelivery()`, y `render()` tiraba excepción justo al completar las cinco dimensiones — la UI se congelaba sin error visible.

## 6. FINAL SPEC

> **Estado: CERRADO — Felipe dio el OK el 2026-09-07.** Archivo de referencia: `roadmap-lab.html` en el HEAD de este repo (it8b). Para ir hacia atrás: `git checkout <hash> -- roadmap-lab.html` con los hashes de §4.
>
> **Para el chat principal:** leé §6.1 (contrato), §6.3 (lo que hay que cablear), §6.4 (riesgos) y §6.6 (orden sugerido) antes de tocar `rsstrategytool.html`. Y antes de editar, `git status` en `strategy-os/` — el chat de Stately también edita ese archivo (ver `GIT-CONVENTION.md`).

### 6.1 Qué cambia en el contrato

**Nada se renombra y nada se elimina** — no hace falta tabla de migración. Todos los campos del contrato original salen igual. Lo que se agrega:

```js
roadmap = {
  title, period, consolidatedAt,          // igual que antes
  thesis: {                                // NUEVO — la hipótesis que reina sobre el roadmap
    title:  string,                        // el nombre de la apuesta
    text:   string,                        // por qué esta apuesta, ahora
    from:   string,                        // de dónde viene (lo que ya sabemos)
    to:     string,                        // a dónde va (lo que sabremos después)
    period: string
  },
  conceptStart: int,                       // NUEVO — primer C# ; el resto sigue en escala por delivery
  periodStart:  'YYYY-MM-DD',              // NUEVO — fecha de arranque del período
  periodWeeks:  int,                       // NUEVO — cuántas semanas abarca (capacity se prorratea)
  periodEnd:    'YYYY-MM-DD',              // NUEVO — derivado (start + weeks)
  schedule: [{                             // NUEVO — el plan de producción resuelto al consolidar
    delivery: int, due: 'YYYY-MM-DD',
    businessDays: int,                     // la ruta más larga del delivery, según el Menu
    menuCost: int,                         // suma del costo base de las rutas elegidas
    unroutedConcepts: int
  }],
  contract: {                              // NUEVO — el presupuesto del período
    conceptsPerMonth: int,                 // el número vigente (contractual o pisado)
    capacity: int,                         // conceptsPerMonth × periodMonths
    planned:  int,                         // suma de lane.concepts al consolidar
    source:   'HubSpot' | 'strategist override',
    of:       string                       // qué deal / retainer
  },
  lanes: [{
    ctp, segment, angle, funnel, phase,    // igual
    hypothesis, concepts, variants, notes, // igual
    castings: string[],                    // igual — ahora derivado: unión de conceptSpecs[].casting
    formats:  string[],                    // igual — ahora derivado: unión de conceptSpecs[].format
    delivery: int,                         // YA EXISTÍA como opcional del export; ahora lo fija el builder
    conceptNums:  int[],                   // NUEVO — los C# resueltos de esta lane
    conceptSpecs: [{casting, format, route}] // NUEVO — uno por concepto, alineado con conceptNums
                                           // route = id del Creative Menu (STATIC, UGC_A, EDITOR…), '' = sin agendar
  }]
}
```

### 6.2 Qué tiene que hacer cada consumidor

- **Export → Strategy Sheet.** Sigue funcionando sin tocar nada: `castings`/`formats` mantienen la semántica "uno → pre-llena Talent/Format, varios → se asigna por fila". **Mejora recomendada:** si la lane trae `conceptSpecs`, pre-llenar Talent y Format **por concepto** en vez de por lane — ahí desaparece buena parte de la asignación manual en la sheet. Los D# ya no hace falta pedirlos en el modal (vienen en `lane.delivery`); el modal queda para confirmar/corregir. El C# inicial sale de `roadmap.conceptStart`.
- **Brief Maker.** Puede heredar `conceptSpecs[k]` para dar casting y formato exactos por concepto en vez del "pick from". Y puede imprimir la tesis del roadmap arriba del brief: es el contexto que hoy falta.
- **Heat map.** Sin cambios (no lee del roadmap).

### 6.3 Lo que la integración necesita cablear (no es aditivo, es reemplazo de fuente)

Estas tres cosas en el lab leen un mock y en la app viva tienen que leer lo real:

1. **`LEDGER` → la data de performance viva.** Necesita filas con `{d, c, ctp, seg, ang, fun, ph, spend, purch, tsr, ctr, per}`. En la app eso sale de cruzar `B.sheet.rows` (que tiene D#/C# + dimensiones) con los combos de performance por período, que es exactamente lo que ya hace `castingRadar()` / `perfCombos()`. **Ojo:** solo cuentan las filas de taxonomía confirmada — las legacy son contexto, no evidencia (misma regla que el heat map).
2. **`BENCH` → los benchmarks de la marca.** `cpa` sale del benchmark de cuenta del período; `tsr`/`ctr` de los benchmarks de la marca; `refSpend`/`refConv` son los umbrales de evidencia (cuánto spend y cuántas conversiones hacen falta para que un concepto cuente como evidencia completa). Los tres primeros ya existen en la app; **`refSpend`/`refConv` hay que pedírselos a Media Buying** — hoy están en $25k y 60 conversiones por concepto, elegidos para que la escala de Stately dé números creíbles.
3. **`THRESH` → por marca.** Los ±8 están calibrados contra la varianza de Stately. Otra marca con otra dispersión necesita otros umbrales; conviene dejarlos en el seed de la marca.
4. **`MENU` → el Creative Menu vivo.** Hoy son 12 rutas copiadas a mano de `CreativeMenu.html`. Si el Menu cambia precios o tiempos, esta copia queda vieja en silencio — conviene leerlo de una fuente única (el backend del Menu o el xlsx) en vez de duplicarlo. **Y lo más importante: los `bd` son turnarounds cotizados, no medidos.** Para que el calendario sirva de verdad hay que reemplazarlos por el tiempo real por ruta, que sale de cruzar entregas históricas (Monday / la Strategy Sheet) con la ruta de cada concepto. Hasta que eso exista, el calendario es una maqueta útil para planificar, no una promesa de fechas.
5. **`CONTRACT_SRC` → el deal de HubSpot.** Hoy es `{conceptsPerMonth: 12, label: 'Stately — 360 retainer'}` hardcodeado. Para integrarlo hay que resolver **qué propiedad del deal guarda el volumen contratado de conceptos por mes** — no la busqué, y no todas las marcas la van a tener cargada. Recomendación: leerla del deal si existe, y si no existe caer al override manual con la UI diciendo "sin dato en HubSpot" en vez de inventar un número. El override del estratega **se guarda con el roadmap** (`roadmap.contract.source`), así queda registrado que ese mes se planificó contra otra capacidad que la contractual.

### 6.4 Riesgos y cosas a mirar antes de integrar

- **El mapa es denso con muchas lanes.** Con 9 líneas y 6 CTPs los nombres de estación se apiñan (el halo los salva, pero es apretado). Si un roadmap real tiene 15+ lanes, hay que probarlo antes: puede necesitar scroll vertical por delivery o colapsar el mapa por período.
- **`refSpend`/`refConv` mueven toda la escala de confianza.** Si se ponen mal, todo el visualizador miente en la misma dirección. Vale calibrarlos contra un período conocido antes de mostrárselo a nadie.
- **La confianza que muestra el lab es baja a propósito** (36% en la mejor persona). Es la verdad del modelo y es el argumento del PLS, pero conviene que Evan y Media Buying lo vean con esa lectura puesta y no como "el tool dice que no sabemos nada".
- **Multi-select puede explotar.** 3 personas × 2 segmentos × 3 angles = 18 lanes de un clic. Hay confirmación arriba de 12, pero el límite real lo pone la capacidad de producción — que ahora sí está en pantalla (la barra de contrato), aunque no bloquea.
- **El número de HubSpot puede estar viejo o vacío.** Si se lee mal, la barra de contrato miente con cara de dato duro. Mejor mostrar "sin dato" que un default silencioso.

### 6.6 Orden de integración sugerido

Son 8 iteraciones; meterlas de una sola vez en el tool vivo es innecesariamente riesgoso. Este orden deja el tool usable después de cada paso, y pone primero lo que no depende de data externa:

| # | Qué | Depende de | Commit sugerido |
|---|---|---|---|
| 1 | **Composer rápido** (multi-select → batch, secciones apiladas, filtro de angles) + **casting/formato por concepto** (`conceptSpecs`) | nada — es UX pura sobre el contrato actual | `main: roadmap composer from lab` |
| 2 | **Tesis del roadmap** + **período con duración** + **capacidad contratada** | el número de HubSpot (arrancá con el override manual y "sin dato") | `main: roadmap thesis + contracted capacity` |
| 3 | **Mapa de subte** (delivery como terminal, duplicar línea, numeración de conceptos) | nada | `main: roadmap line map` |
| 4 | **Hub de export** (sheet / producción / briefs / markdown / JSON / one-pager) | el paso 3 para las fechas del calendario | `main: roadmap export hub` |
| 5 | **Visualizador de dimensiones + confianza + triggers + sugerencias** | la data de performance real (§6.3 punto 1) y los benchmarks | `main: roadmap knowledge viewer` |
| 6 | **Flags layer-vs-evidencia** (con re-marcado que escriba el Strategy Layer de verdad) | el paso 5 | `main: layer vs evidence flags` |
| 7 | **Calendario de producción** | el Creative Menu como fuente única (§6.3 punto 4) | `main: production calendar` |
| 8 | **Archivo de roadmaps** | que haya roadmaps consolidados guardados + performance por período | `main: roadmap archive` |

Los pasos 1 a 4 se pueden hacer ya y no necesitan nada de nadie. Del 5 en adelante hay dependencias externas reales — si se integran con los mocks del lab, el tool va a mostrar números inventados con cara de dato, que es exactamente lo que no queremos.

### 6.5 Pendientes que quedaron fuera del lab

- Drag & drop para reordenar deliveries (hoy se cambia el número y el mapa se reordena solo).
- Editar una lane directamente desde el mapa (hoy se edita desde la tarjeta).
- Que la tesis se pueda derivar/sugerir automáticamente desde las sugerencias abiertas.
- Vista de calendario y agrupación visual por delivery dentro del mapa (hoy el delivery es la terminal, pero dos líneas del mismo delivery no se agrupan gráficamente).
- Que el re-marcado del layer escriba el Strategy Layer real en vez de un override local del lab.
- Repartir la capacidad contratada **por mes dentro de un período largo** (hoy es un total prorrateado; un roadmap de 12 semanas no dice cuántos conceptos van en cada mes).
- Capacidad **por equipo/departamento**: el calendario dice cuántos días hábiles se necesitan, pero no si DANDA o Footage tienen esos días libres. Con el `team` de cada ruta del Menu ya cargado, es el paso natural.
- Tiempo real de producción medido (ver §6.3 punto 4) — hoy son los turnarounds del Menu.
- **El tiempo de producción va a depender de la CLIENT SKIN** (Felipe, 6/9). La misma ruta cuesta distinto tiempo según cuánto del sistema propio del cliente tenga que satisfacer. Hoy no está modelado: `bd` es una constante por ruta. Cuando se modele, pasa a ser función de (ruta, skin de la marca) — ver `Creative Menu/skin-simulator/`.
- Lectura histórica de cumplimiento: entregado vs contratado por período pasado (la franja ya muestra los conceptos, falta el contrato de esos meses).
