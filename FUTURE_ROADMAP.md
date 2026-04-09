# Brand Intelligence Scraper - Future Roadmap

> **Generado:** 2026-01-04  
> **Estado:** Fases 1-9 completadas. Este documento lista features futuros priorizados.

---

## 🔥 NEXT-GEN FEATURES (Nuevos)

### 2. Offer & Funnel X-ray
**Output:** Mapa del embudo actual y dónde se rompe.

| Componente | Descripción |
|------------|-------------|
| **Arquitectura del sitio** | Páginas clave, jerarquía, mensajes por etapa (awareness/consideration/purchase) |
| **Oferta** | Pricing, bundles, garantías, envío/devoluciones, pruebas sociales, urgencia/escasez |
| **CRO heurístico** | Fricciones (formularios, velocidad, popups, CTA ambiguas), claridad de propuesta |
| **Segmentación implícita** | A quién le hablan (por copy) vs a quién creen |
| **Acción directa** | 5 cambios de copy/landing + 10 ángulos de ads alineados al embudo |

**Dificultad:** Media  
**Valor:** 🔥 Muy Alto

---

### 3. Message-Market Fit Map
**Output:** Matriz estructurada para generar anuncios no genéricos.

```
ICP Clusters:
├── Roles + contextos
├── Disparadores de compra
├── Alternativas actuales ("antes usaba X")
└── Sensibilidad a precio

Jobs-to-be-Done:
├── Funcional (qué lograr)
├── Emocional (qué sentir)
└── Social (cómo ser percibido)

Objeciones por tipo:
├── Precio
├── Confianza
├── Eficacia
├── Tiempo/Complejidad
└── "Esto no es para mí"

Lenguaje Exacto:
└── Frases repetidas en reviews/foros (sin parafrasear)
```

**Métrica:** CTR/Hook rate por cluster  
**Dificultad:** Media  
**Valor:** 🔥 Muy Alto

---

### 4. Proof & Claims Engine
**Output:** Inventario de claims con nivel de evidencia + "claim-safe copy".

| Score de Riesgo | Copy Pattern |
|-----------------|--------------|
| **Fuerte** | "X% / en Y tiempo" |
| **Medio** | "la mayoría nota…" |
| **Bajo** | "diseñado para ayudar…" |

**Fuentes de claims:**
- Sitio / FAQs / blogs / docs
- Casos de estudio / reviews
- UGC / testimonios

**Evidencia asociada:** Citas, números, estudios, screenshots, garantías.

**Métrica:** Menos rechazos compliance + menor tasa de refund  
**Dificultad:** Media  
**Valor:** 🔥 Muy Alto

---

### 5. Competitor & Positioning Radar
**Output:** "Comparative positioning sheet" usable en ads.

```
Set competitivo:
├── Directos
├── Indirectos
└── Substitutos

Matriz de mensajes:
├── Qué prometen
├── Qué tono usan
├── Qué pruebas muestran
└── Qué formatos ganan

Análisis:
├── White space angles (ángulos poco explotados)
├── Parity (table stakes)
└── Advantage (diferencial real)
```

**Métrica:** Tasa de fatiga creativa vs competidores  
**Dificultad:** Baja (ya tenemos competitor_ads)  
**Valor:** 🔥 Muy Alto

---

### 6. UGC & Creator Brief Generator
**Output:** Briefs de UGC casi listos para enviar.

```
Guiones por arquetipo:
├── Escéptico
├── Experto
├── Antes/Después
├── Comparación
├── Rutina diaria
└── "3 cosas que..."

Casting constraints:
├── Edad/estilo/entorno
├── Props necesarios
└── Tomas necesarias

Shotlist:
├── 9:16 format
├── Hooks
├── Cortes
└── On-screen text policy

Checklist autenticidad:
└── Frases y objeciones reales de reviews/foros
```

**Dificultad:** Baja (ya tenemos todos los datos)  
**Valor:** 🔥 Muy Alto

---

### 7. Creative Testing Plan
**Output:** Backlog priorizado de experimentos con hipótesis.

| Eje de Testing | Ejemplo |
|----------------|---------|
| Hook | "POV" vs "You won't believe" |
| Claim | "50% faster" vs "works in days" |
| Prueba | UGC vs Founder |
| Oferta | Bundle vs Single |
| CTA | "Shop now" vs "See how" |
| Formato | Face-to-cam vs B-roll |

**Priorización:** Impacto × Confianza × Costo (ICE/RICE)  
**Diseño:** Qué mantener constante, qué variar, sample size sugerido

**Dificultad:** Media  
**Valor:** 🔥 Muy Alto

---

## 📊 Priority Matrix (Actualizada)

| Feature | Valor | Dificultad | Priority |
|---------|-------|------------|----------|
| **Offer & Funnel X-ray** | 🔥 | Media | P0 |
| **Message-Market Fit Map** | 🔥 | Media | P0 |
| **Proof & Claims Engine** | 🔥 | Media | P0 |
| **Competitor Radar** | 🔥 | Baja | P0 |
| **UGC Brief Generator** | 🔥 | Baja | P0 |
| **Creative Testing Plan** | 🔥 | Media | P0 |
| Ad Concept Generator | Alto | Media | P1 |
| Notion Export | Alto | Media | P1 |
| Comment Analysis | Alto | Media | P1 |

---

## ✅ Ya Implementado (Fases 1-9)

- [x] 10 Scrapers funcionando (Apify + Firecrawl)
- [x] Video Analysis con 30+ dimensiones IMA
- [x] Instagram Feed Analysis
- [x] Twitter Track 2 con Apify
- [x] Script Generator con video_analysis
- [x] Proto-ICPs clustering
- [x] Cross-source validation
- [x] Persistent logging
- [x] Unified Data Layer
- [x] Quality Auditor (grades A-D)

---

## 🚀 Recomendación de Próximos Pasos

1. **Message-Market Fit Map** - Base para todo lo demás
2. **Proof & Claims Engine** - Compliance-safe desde el día 1
3. **UGC Brief Generator** - Escalar creativos rápido
4. **Creative Testing Plan** - Medir y mejorar sistemáticamente
5. **Offer & Funnel X-ray** - Encontrar dónde se pierde dinero


