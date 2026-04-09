# Brand DNA - Plan de Implementación
## Basado en Google Pomelli (labs.google.com/pomelli)

Fecha: 2025-12-15

---

## Qué es Pomelli (Google Labs)

Pomelli es una herramienta de Google Labs + DeepMind que:
1. Analiza el website de una marca
2. Extrae su "Business DNA" automáticamente
3. Genera campañas de marketing on-brand

### Componentes del Brand DNA (extraídos de los screenshots):

1. **Colors** - Paleta de colores con hex codes (ej: #002432, #0070c9, #ffffff, #fcae03)
2. **Tagline** - Slogan de la marca (ej: "Your credit building toolkit. Start the path to financial freedom.")
3. **Brand Values** - Tags como: "Builders First", "Transparency Matters", "Accessibility", "Financial Inclusion"
4. **Brand Aesthetic** - Tags como: "modern", "clean", "digital", "approachable", "trustworthy", "vibrant"
5. **Brand Tone of Voice** - Tags como: "Empathetic", "Informative", "Encouraging", "Trustworthy"
6. **Business Overview** - Descripción completa del negocio
7. **Brand Images** - Grid de imágenes representativas de la marca

---

## Requerimientos del Usuario

### 1. Nuevos Campos para el Modelo Brand

- `brand_colors` (JSON) - Paleta de colores: `["#002432", "#0070c9", ...]`
- `tagline` (String) - Slogan/tagline
- `brand_values` (JSON) - Valores: `["Transparency", "Innovation", ...]`
- `brand_aesthetic` (JSON) - Estética: `["modern", "clean", "digital", ...]`
- `tone_of_voice` (JSON) - Tono: `["Empathetic", "Informative", ...]`
- `logo_url` (String) - URL del logo detectado
- `fonts` (JSON) - Tipografías detectadas
- `brand_images` (JSON) - URLs de imágenes representativas
- `social_media_urls` (JSON) - `{"twitter": "...", "instagram": "...", "linkedin": "...", "facebook": "...", "tiktok": "..."}`
- `product_descriptions` (JSON) - `[{"name": "Product A", "description": "..."}]`

### 2. Mensajes de Progreso (EN INGLÉS)

Durante el análisis, mostrar estos mensajes animados:

```
Pulling images from website...
Finding your logo...
Gathering colors...
Picking brand fonts...
Studying your brand values...
Learning your tone of voice...
Determining your visual aesthetic...
Writing your tagline...
Summarizing your business...
```

**IMPORTANTE**: Esto se SUMA a las 6 fases existentes, no las reemplaza:
- Phase 1: Discovering brand
- Phase 2: Generating search queries
- Phase 3: Scraping sources (reddit, trustpilot, news, forums, etc.)
- Phase 4: Ad Library Intelligence
- Phase 5: Deep Competitor Analysis
- Phase 6: Generating insights

### 3. UI Visual del Brand DNA (Imitar Pomelli)

La UI debe mostrar:
- **Colors**: Círculos de colores con sus hex codes debajo
- **Tagline**: En cursiva/itálica destacado
- **Brand Values**: Como tags/chips/badges
- **Brand Aesthetic**: Como tags/chips
- **Tone of Voice**: Como tags/chips
- **Business Overview**: Card con texto
- **Brand Images**: Grid de imágenes (como Pomelli muestra)

### 4. Timer de Progreso

Como Pomelli que dice "~10 min remaining", agregar estimación de tiempo.

---

## Archivos a Modificar/Crear

| Archivo | Acción |
|---------|--------|
| `backend/app/models.py` | Agregar campos Brand DNA |
| `backend/app/schemas.py` | Agregar schemas Brand DNA |
| `backend/app/services/brand_dna.py` | **NUEVO** - Servicio extractor de Brand DNA |
| `backend/app/services/research_orchestrator.py` | Integrar Brand DNA como fase inicial, mejorar progreso |
| `backend/app/routers/research.py` | Exponer paso actual en API con tiempo estimado |
| `frontend/src/pages/Research.tsx` | UI de progreso con timer y pasos descriptivos |
| `frontend/src/pages/Results.tsx` | Tab/sección Brand DNA visual |
| `frontend/src/api/client.ts` | Tipos TypeScript nuevos |

---

## Servicio BrandDNAExtractor

```python
# backend/app/services/brand_dna.py

class BrandDNAExtractor:
    """Extrae la identidad de marca desde el website."""
    
    async def extract_brand_dna(self, website_url: str, brand_name: str) -> Dict:
        """
        1. Scrape website con Firecrawl (HTML + imágenes)
        2. Extraer colores dominantes del CSS
        3. Detectar tipografías del CSS
        4. Encontrar logo (og:image, favicon, elementos con "logo")
        5. Extraer links a redes sociales
        6. Usar LLM para analizar: tagline, valores, tono, estética
        """
        return {
            "brand_colors": ["#002432", "#0070c9", "#ffffff", "#fcae03"],
            "tagline": "Your credit building toolkit.",
            "brand_values": ["Transparency", "Innovation", "Trust"],
            "brand_aesthetic": ["modern", "clean", "digital"],
            "tone_of_voice": ["Empathetic", "Informative", "Encouraging"],
            "logo_url": "https://...",
            "fonts": ["Inter", "Helvetica"],
            "brand_images": ["url1", "url2", ...],
            "social_media_urls": {
                "twitter": "https://twitter.com/brand",
                "instagram": "https://instagram.com/brand",
                "linkedin": "https://linkedin.com/company/brand"
            },
            "product_descriptions": [
                {"name": "Product A", "description": "Description..."}
            ]
        }
```

---

## Flujo de Datos

```
Website URL
    ↓
[BrandDNAExtractor]
    ├── Firecrawl Scrape (HTML + branding format)
    ├── CSS Parser → Colores + Fonts
    ├── HTML Parser → Logo + Social Links + Imágenes
    └── LLM Analysis → Tagline + Values + Tone + Aesthetic
    ↓
Brand DNA Object → Guardado en Brand model
    ↓
[Research Orchestrator - Fases existentes]
    ├── Phase 1: Brand Discovery (ya existía)
    ├── Phase 2: Keyword Generation
    ├── Phase 3: Scraping
    ├── Phase 4: Ad Library
    ├── Phase 5: Competitors
    └── Phase 6: Insights
    ↓
Results Page con nuevo Tab "Brand DNA"
```

---

## UI de Progreso (Frontend)

```tsx
// Ejemplo de componente de progreso
const PROGRESS_STEPS = [
  { id: 'images', label: 'Pulling images from website...', icon: Image },
  { id: 'logo', label: 'Finding your logo...', icon: Sparkles },
  { id: 'colors', label: 'Gathering colors...', icon: Palette },
  { id: 'fonts', label: 'Picking brand fonts...', icon: Type },
  { id: 'values', label: 'Studying your brand values...', icon: Heart },
  { id: 'tone', label: 'Learning your tone of voice...', icon: MessageSquare },
  { id: 'aesthetic', label: 'Determining your visual aesthetic...', icon: Eye },
  { id: 'tagline', label: 'Writing your tagline...', icon: PenTool },
  { id: 'summary', label: 'Summarizing your business...', icon: FileText },
];

// Timer countdown
<div className="text-center">
  <span className="text-2xl font-bold">~{estimatedMinutes} min remaining</span>
</div>
```

---

## UI del Brand DNA (Resultados)

Basado en los screenshots de Pomelli:

```tsx
// Sección Colors
<div className="card">
  <h3>Colors</h3>
  <div className="flex gap-4">
    {brand.brand_colors.map(color => (
      <div className="flex flex-col items-center">
        <div 
          className="w-16 h-16 rounded-full" 
          style={{ backgroundColor: color }}
        />
        <span className="text-sm">{color}</span>
      </div>
    ))}
  </div>
</div>

// Sección Tagline
<div className="card">
  <h3>Tagline</h3>
  <p className="text-xl italic text-amber-400">{brand.tagline}</p>
</div>

// Sección Brand Values
<div className="card">
  <h3>Brand Values</h3>
  <div className="flex flex-wrap gap-2">
    {brand.brand_values.map(value => (
      <span className="tag">{value}</span>
    ))}
  </div>
</div>

// Sección Brand Aesthetic
<div className="card">
  <h3>Brand Aesthetic</h3>
  <div className="flex flex-wrap gap-2">
    {brand.brand_aesthetic.map(item => (
      <span className="tag">{item}</span>
    ))}
  </div>
</div>

// Sección Tone of Voice
<div className="card">
  <h3>Brand Tone of Voice</h3>
  <div className="flex flex-wrap gap-2">
    {brand.tone_of_voice.map(tone => (
      <span className="tag">{tone}</span>
    ))}
  </div>
</div>

// Sección Business Overview
<div className="card">
  <h3>Business Overview</h3>
  <p>{brand.description}</p>
</div>

// Grid de Imágenes (como Pomelli)
<div className="card">
  <h3>Brand Images</h3>
  <div className="grid grid-cols-4 gap-2">
    {brand.brand_images.map(url => (
      <img src={url} className="rounded-lg" />
    ))}
  </div>
</div>
```

---

## Notas Adicionales

1. **Firecrawl tiene formato "branding"** que extrae colores, fonts y más - usar esto
2. **El análisis de Brand DNA debe ser la PRIMERA fase** antes de todo lo demás
3. **Los colores deben extraerse del CSS** (background-color, color, etc.)
4. **Las fonts del CSS** (font-family)
5. **El logo buscar en**: og:image, link[rel="icon"], img con "logo" en class/id/alt
6. **Social links buscar**: href con twitter.com, instagram.com, linkedin.com, facebook.com, tiktok.com

---

## APIs Disponibles

- **Firecrawl**: Ya configurado, tiene formato "branding" que extrae brand identity
- **OpenAI GPT**: Para análisis de tagline, valores, tono, estética
- **Gemini**: Para análisis de imágenes si es necesario

---

## Pendiente: Arreglar Generators

Los generators (`scripts.py`, `thumbnails.py`, `ab_tests.py`) están devolviendo 0 resultados.
Ya se mejoró el LLM client para parsear JSON, hay que verificar que funcionen.


