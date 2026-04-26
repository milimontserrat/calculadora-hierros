# Calculadora de Hierros — Optimizador de Compra de Armadura

> Web app para minimizar la compra de barras de hierro de construcción aprovechando los sobrantes de cada barra.

---

## 1. Contexto del negocio

Se trata de una herramienta para un estudio de arquitectura que desarrolla edificios multifamiliares de baja escala en Buenos Aires. En cada obra hay que comprar **barras de hierro de construcción** (también llamadas "armadura") para el hormigón armado. Las barras vienen del proveedor en **largo fijo** (típicamente 12m) y se cortan en obra para fabricar bases, plateas, vigas, columnas, tabiques, losas, etc.

El estructuralista entrega una **planilla de armaduras** que especifica, para cada elemento estructural:

- Nombre del elemento (ej: "PLATEA", "BASE 1", "VF", "tronco C5", "L502", etc.)
- Diámetro (φ) en mm (valores típicos: 6, 8, 10, 12, 16, 20, 25)
- Cantidad de piezas necesarias para ese elemento
- Cantidad de veces que el elemento se repite en la obra
- Largo de cada pieza, en metros (ej: 3.20, 6.90, 1.42)

Hoy el cálculo de cuántas barras comprar lo hacen a mano en una planilla de Excel y el resultado **sobreestima la compra** porque suman barra por barra sin combinar piezas chicas dentro de una misma barra de 12m. En un caso real, la planilla manual dijo "comprar 117 barras de φ8" cuando combinando astutamente alcanzaba con **105 barras** (ahorro de 144 metros lineales de hierro).

## 2. Problema técnico a resolver

Esto es un **Cutting Stock Problem unidimensional** (1D-CSP):

> Dado un conjunto de piezas de diferentes largos y un stock de barras de largo fijo L, encontrar el mínimo número de barras necesarias para cortar todas las piezas, sabiendo que cada barra se puede cortar en varias piezas siempre que la suma de sus largos no supere L.

Reglas duras del dominio:

1. **Solo se pueden combinar piezas del mismo diámetro φ en una misma barra.** Por lo tanto, el problema se resuelve **por separado para cada φ**.
2. **No se pueden cortar las medidas dadas.** Si una pieza tiene que medir 6.90m y la barra es de 12m, esa pieza ocupa 6.90m enteros — no se puede partir en 3.45 + 3.45.
3. **No se pueden empalmar/solapar barras.** Si una pieza necesita 13m y la barra es de 12m, **no es posible** (esto debe validarse y mostrar error).
4. **No hay sobrante mínimo aprovechable.** Cualquier sobrante menor a la pieza más chica simplemente queda como desperdicio.

## 3. Objetivo funcional de la app

La usuaria carga la planilla de armaduras del estructuralista en una tabla editable, le da "Calcular" y la app devuelve:

1. **Cantidad total de barras a comprar por diámetro** (ej: φ8 → 105 barras de 12m).
2. **Plan de corte detallado**: por cada barra individual, qué piezas se cortan y cuánto sobra (ej: "Barra #1 de φ8: cortar 1×6.90 + 1×3.20 + 1×1.80, sobrante 0.10m").
3. **Excel descargable** que replica la estructura de la planilla original con todas las columnas calculadas (`cantidad directa`, `cantidad x barra`, `cantidad final de barras`, `sobrante`, `RESTO TOTAL`) más una nueva sección con el plan de corte optimizado.

## 4. Stack técnico

| Capa | Tecnología | Motivo |
|------|-----------|--------|
| UI | **Streamlit** (Python) | Permite hacer toda la app en Python, sin HTML/CSS/JS. Buena para tablas editables (`st.data_editor`). |
| Optimización | **Google OR-Tools** (CP-SAT solver) | Solver de programación lineal entera. Resuelve el Cutting Stock óptimamente en milisegundos para casos realistas (~100-300 piezas por φ). |
| Fallback de optimización | **First Fit Decreasing (FFD)** implementado a mano | Heurística simple, por si OR-Tools fallara en algún caso. |
| Manipulación Excel | **pandas** + **openpyxl** | pandas para data wrangling, openpyxl para preservar formato y agregar formulas. |
| Persistencia | **Supabase** (PostgreSQL gratis) | Para guardar proyectos. Streamlit Community Cloud no tiene filesystem persistente. |
| Secretos | **st.secrets** | Para credenciales de Supabase y password del login. Nunca hardcodear en el código. |
| Deploy | **Streamlit Community Cloud** | Gratis, conectado a GitHub, da URL pública. |
| Repo | **GitHub** (privado) | Versionado. |

### Versiones específicas
- Python 3.11
- streamlit >= 1.32
- ortools >= 9.10
- pandas >= 2.2
- openpyxl >= 3.1
- supabase-py >= 2.4

## 5. Estructura del repositorio

```
calculadora-hierros/
├── CLAUDE.md                    # este documento
├── README.md                    # instrucciones para deploy
├── requirements.txt
├── .streamlit/
│   ├── config.toml              # tema visual
│   └── secrets.toml.example     # plantilla de secretos (sin valores reales)
├── app.py                       # entrypoint de Streamlit (login + router)
├── pages/
│   ├── 1_Nuevo_Proyecto.py      # formulario de carga de planilla
│   └── 2_Mis_Proyectos.py       # listado de proyectos guardados
├── core/
│   ├── __init__.py
│   ├── models.py                # dataclasses: Element, Project, CutPlan, BarUsage
│   ├── optimizer.py             # OR-Tools CP-SAT + fallback FFD
│   ├── excel_export.py          # generación del Excel de salida
│   ├── excel_import.py          # parser de planillas de armadura subidas
│   └── db.py                    # cliente Supabase (CRUD de proyectos)
├── tests/
│   ├── test_optimizer.py        # incluye el caso φ8 que debe dar ≤ 105
│   └── fixtures/
│       └── ejemplo_real.json    # datos del Excel real provisto por la usuaria
└── assets/
    └── logo.svg                 # placeholder de branding
```

## 6. Especificación funcional detallada

### 6.1 Autenticación

- Pantalla de login simple en `app.py` con campos usuario y contraseña.
- Credenciales válidas: usuario `mili`, contraseña `hierros`. La contraseña se lee de `st.secrets["auth"]["password"]` (no hardcodear en el código).
- Una vez autenticado, guardar `st.session_state.authenticated = True`.
- Si no está autenticado, bloquear acceso a las pages y mostrar el login.
- Botón de "Cerrar sesión" en el sidebar.

### 6.2 Navegación / páginas

**Home (Mis Proyectos)** — primera pantalla post-login.
- Lista de proyectos guardados (nombre, fecha de creación, cantidad total de barras calculadas).
- Cada proyecto tiene tres acciones: **Abrir**, **Duplicar**, **Eliminar**.
- Botón grande "+ Nuevo proyecto" arriba.

**Nuevo Proyecto / Editar Proyecto**
- Campo "Nombre del proyecto" (obligatorio).
- Campo "Largo de barra (m)" — default 12, editable. Aplica a todo el proyecto.
- Tabla editable (`st.data_editor`) con las columnas:
  - **Elemento** (texto libre, ej: "PLATEA", "BASE 1", "tronco C5", "L502")
  - **φ** (diámetro, número entero, valores comunes 6/8/10/12/16/20/25 — pero permitir cualquier entero)
  - **Cantidad de elementos** (entero ≥ 1)
  - **Cantidad de repeticiones** (entero ≥ 1, default 1)
  - **Medida (m)** (decimal positivo)
- Filas dinámicas: la usuaria puede agregar/eliminar filas.
- Botón "Calcular" → corre el optimizador y muestra los resultados debajo.
- Botón "Guardar proyecto" → guarda en Supabase.
- Botón "Descargar Excel" — habilitado solo después de calcular.

### 6.3 Modelo de datos

```python
# core/models.py

@dataclass
class Element:
    nombre: str           # "PLATEA", "BASE 1", "tronco C5", etc.
    phi: int              # diámetro en mm
    cantidad_elementos: int
    cantidad_repeticiones: int
    medida: float         # largo de cada pieza, en metros

    @property
    def cantidad_total_piezas(self) -> int:
        """Cantidad real de piezas a cortar de este elemento."""
        return self.cantidad_elementos * self.cantidad_repeticiones

    @property
    def longitud_total(self) -> float:
        """Hierro lineal total que demanda este elemento, en metros."""
        return self.cantidad_total_piezas * self.medida

@dataclass
class Project:
    id: str | None        # uuid en Supabase
    nombre: str
    largo_barra: float    # default 12
    elementos: list[Element]
    created_at: datetime
    updated_at: datetime

@dataclass
class BarUsage:
    """Cómo se usa una barra individual: qué piezas se cortan de ella."""
    phi: int
    piezas: list[tuple[str, float]]  # [(nombre_elemento, medida), ...]
    sobrante: float

@dataclass
class CutPlan:
    """Resultado del optimizador para un proyecto entero."""
    barras_por_phi: dict[int, list[BarUsage]]   # cada φ → lista de barras
    total_barras: int
    desperdicio_total_m: float
    metodo_usado: str   # "OR-Tools CP-SAT" o "First Fit Decreasing"
```

### 6.4 Algoritmo de optimización

#### Estrategia general
Resolver **por separado para cada diámetro φ**. Para cada φ:

1. Expandir la lista de piezas: cada `Element` con `cantidad_total_piezas = N` genera N piezas individuales del largo `medida`.
2. Validar: si alguna pieza es más larga que `largo_barra`, abortar con error claro indicando cuál.
3. Calcular cota inferior: `ceil(suma_de_largos / largo_barra)`. El óptimo no puede ser menor.
4. Calcular cota superior trivial: una barra por pieza. (Sirve para limitar el espacio de búsqueda del solver.)
5. Correr el solver óptimo (OR-Tools CP-SAT). Si supera 30 segundos, abortar y caer al fallback FFD.
6. Devolver el `BarUsage` para cada barra usada.

#### Implementación con OR-Tools CP-SAT

Modelar como problema de *bin packing* con asignación pieza→barra:

```
Variables:
  x[i][j] ∈ {0,1}    pieza i asignada a barra j
  y[j]    ∈ {0,1}    barra j está en uso
  
Restricciones:
  ∑_j x[i][j] = 1                      ∀ pieza i  (cada pieza va exactamente a una barra)
  ∑_i largo[i] · x[i][j] ≤ L · y[j]    ∀ barra j  (capacidad)

Objetivo:
  minimizar ∑_j y[j]
```

Donde el rango de `j` va de 0 hasta la cota superior trivial.

**Importante**: agregar restricción de simetría para acelerar el solver — `y[j] ≥ y[j+1]` (las barras se "llenan" en orden).

#### Fallback: First Fit Decreasing
1. Ordenar piezas de mayor a menor.
2. Para cada pieza, ponerla en la primera barra abierta donde entre. Si no entra en ninguna, abrir una barra nueva.

Esta heurística da resultados óptimos o casi óptimos (gap < 5%) para Cutting Stock 1D en la práctica.

### 6.5 Excel de salida

Replicar la estructura del Excel original que usa la usuaria, **manteniendo todas las columnas existentes**:

- Nombre del elemento
- φ
- Cantidad de elementos
- Cantidad de repeticiones
- Cantidad total
- Medida
- Longitud total (= cantidad total × medida)
- Cantidad directa (= longitud total / largo_barra)
- Cantidad x barra (= floor(largo_barra / medida))
- Cantidad final de barras por elemento (cálculo "ingenuo" — para comparación)
- Sobrante por barra del elemento

**Agregar una sección nueva** al final del archivo con dos hojas adicionales:

- **Hoja "Resumen"**: tabla con `φ | barras_optimizadas | barras_metodo_ingenuo | ahorro_barras | ahorro_metros | desperdicio_total`. Esto le permite ver el ahorro vs. el método manual.
- **Hoja "Plan de corte"**: una fila por barra individual, con columnas `φ | barra_# | piezas_cortadas | sobrante`. La columna "piezas_cortadas" se formatea como texto: `"3×3.20 + 1×2.40"` para que sea legible en obra.

Usar fórmulas de Excel donde tenga sentido (ej: `cantidad total = B*C`, `longitud total = D*E`) para que el archivo sea editable a mano si hace falta. NO hardcodear valores calculables.

### 6.6 Carga desde planilla de armaduras (importación de Excel)

En la pantalla de "Nuevo Proyecto", agregar un botón **"Importar desde Excel"** que abre un file uploader. Acepta `.xlsx`.

El parser debe ser tolerante:
- Detectar automáticamente las columnas relevantes por nombre (case-insensitive, ignorando tildes y espacios). Buscar headers que matcheen aproximadamente: `elemento` / `nombre`, `fi` / `φ` / `diametro`, `cantidad de elementos` / `cant elementos`, `cantidad de repeticiones` / `repeticiones`, `medida` / `largo`.
- Ignorar filas vacías y filas de subtotales (las que tienen NaN en las columnas críticas pero números en alguna columna agregada).
- Si la planilla tiene varias hojas, importar de todas y concatenar.
- Mostrar un preview antes de confirmar la importación.

### 6.7 Persistencia con Supabase

Schema SQL (incluir en `README.md` para que la usuaria lo corra una sola vez):

```sql
create table projects (
  id          uuid primary key default gen_random_uuid(),
  nombre      text not null,
  largo_barra numeric not null default 12,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

create table elements (
  id                       uuid primary key default gen_random_uuid(),
  project_id               uuid references projects(id) on delete cascade,
  nombre                   text not null,
  phi                      int not null,
  cantidad_elementos       int not null,
  cantidad_repeticiones    int not null default 1,
  medida                   numeric not null,
  orden                    int not null  -- para preservar el orden de las filas
);

create index on elements(project_id);
```

Conexión vía `supabase-py` con URL y anon key en `st.secrets["supabase"]`.

## 7. Estilo visual

Inspiración: **https://krasukzaietz.com.ar/** — minimalismo arquitectónico, tipografía sans-serif clean, paleta neutra, mucho whitespace, sin adornos.

**Tema (`.streamlit/config.toml`):**

```toml
[theme]
base = "light"
primaryColor = "#1a1a1a"           # negro tenue para botones/acciones
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f5f5f5"
textColor = "#1a1a1a"
font = "sans serif"
```

**CSS adicional** (inyectado con `st.markdown(..., unsafe_allow_html=True)` en `app.py`): tipografía `Inter` o `Helvetica Neue`, weights ligeros (300-400), botones rectangulares sin bordes redondeados agresivos, mucho padding entre secciones, headings con tracking ajustado.

**No usar emojis ni íconos coloridos.** Estética sobria, profesional, arquitectónica.

## 8. Criterios de aceptación

### Tests funcionales (deben pasar en `tests/test_optimizer.py`)

1. **Caso real φ8 del Excel original**: cargar los elementos de φ8 del archivo `ejemplo_real.json` (lo armo a partir de la hoja "bases y vf" del Excel provisto). Para barra de 12m, el optimizador debe devolver **≤ 105 barras**. Si devuelve 117 (método ingenuo) o más, el test falla.
2. **Caso trivial**: 1 pieza de 5m con barra de 12m → 1 barra, sobrante 7m.
3. **Caso pieza > barra**: pieza de 13m con barra de 12m → debe tirar `ValueError("Pieza de X m excede el largo de barra de Y m")`.
4. **Caso múltiples diámetros**: piezas de φ8 y φ10 nunca se combinan en la misma barra.
5. **Cota inferior**: para una lista cualquiera, `total_barras >= ceil(suma_largos / largo_barra)`.

### Tests de UI (manuales, documentados en README)

1. Login con credenciales correctas → entra. Con credenciales incorrectas → muestra error.
2. Crear proyecto, cargar 5 elementos, calcular, descargar Excel → el Excel abre sin errores en LibreOffice/Excel y el "Plan de corte" suma las piezas correctas.
3. Guardar proyecto, cerrar sesión, volver a entrar → el proyecto aparece en "Mis Proyectos" con los datos intactos.
4. Importar el Excel de ejemplo → la tabla se popula con todos los elementos.

## 9. Plan de implementación por fases

Implementar en este orden, sin saltear pasos. Cada fase debe tener tests pasando antes de avanzar.

### Fase 1 — Fundamentos (sin UI todavía)
- Setup de proyecto: `requirements.txt`, estructura de carpetas, `.gitignore`.
- `core/models.py` con las dataclasses.
- `core/optimizer.py` con OR-Tools y fallback FFD.
- Tests de optimizador (los 5 listados arriba) pasando.

### Fase 2 — UI básica con datos en memoria
- `app.py` con login.
- `pages/1_Nuevo_Proyecto.py` con tabla editable y botón Calcular.
- Mostrar resultado del optimizador (resumen + plan de corte) en pantalla.
- Sin persistencia todavía: el proyecto se pierde al refrescar.

### Fase 3 — Excel export + import
- `core/excel_export.py` que genera el archivo replicando estructura original + nuevas hojas.
- `core/excel_import.py` para subir planilla de armaduras y popular la tabla.
- Botón "Descargar Excel" funcional.

### Fase 4 — Persistencia con Supabase
- `core/db.py` con CRUD de proyectos.
- `pages/2_Mis_Proyectos.py` con listado.
- Botones Guardar / Abrir / Duplicar / Eliminar.

### Fase 5 — Estilo y deploy
- `config.toml` y CSS personalizado.
- `README.md` con instrucciones para que la usuaria pueda hacer deploy en Streamlit Cloud (paso a paso, asumiendo que no es técnica).
- Configuración de `secrets.toml` en Streamlit Cloud.

## 10. Notas técnicas importantes

- **Edge case**: si `cantidad_total_piezas = 0` para algún elemento, ignorarlo silenciosamente (no es error).
- **Edge case**: si todas las piezas de un φ caben en una sola barra, no hay que correr el solver — devolver 1 barra directo.
- **Performance**: para casos con muchas piezas iguales (ej: 200 piezas de 1.00m), el solver puede ser lento por la combinatoria. Detectar piezas iguales y agruparlas (modelar con variables de cantidad por "patrón de corte" en lugar de pieza individual) si el caso lo amerita. Por ahora hacerlo simple y optimizar solo si los tests son lentos.
- **Idioma**: toda la UI en español rioplatense, voseo cuando aplique ("cargá", "calculá", "descargá").
- **Mobile**: Streamlit es responsive de fábrica, pero verificar que la tabla editable se vea bien en pantalla chica. Si no, ofrecer una vista alternativa "una fila a la vez" para mobile.
- **No usar `localStorage` ni cookies** para persistencia — todo va a Supabase.
- **Logging**: usar el logging estándar de Python con nivel INFO para trazar qué método de optimización se usó y cuánto tardó. Útil para debug en Streamlit Cloud.

## 11. Anexo — Datos del caso real (φ8, barra de 12m)

Estos son los elementos del Excel original que el optimizador debe poder resolver con ≤ 105 barras (el método ingenuo da 117):

| Elemento | φ | Cant. elementos | Repeticiones | Medida (m) |
|----------|---|-----------------|--------------|------------|
| PLATEA | 8 | 32 | 1 | 3.20 |
| PLATEA | 8 | 20 | 1 | 3.90 |
| PLATEA | 8 | 34 | 1 | 1.00 |
| PLATEA | 8 | 10 | 1 | 2.40 |
| PLATEA | 8 | 10 | 1 | 2.70 |
| VF | 8 | 28 | 1 | 4.49 |
| VF | 8 | 25 | 1 | 6.24 |
| VF | 8 | 10 | 1 | 1.80 |
| VF | 8 | 7 | 1 | 3.24 |
| VF | 8 | 10 | 1 | 2.14 |
| VF | 8 | 15 | 1 | 3.84 |
| VF | 8 | 28 | 1 | 5.27 |
| VF | 8 | 14 | 1 | 2.32 |
| VF | 8 | 30 | 1 | 4.87 |
| VF | 8 | 21 | 1 | 6.90 |

Convertir esto a `tests/fixtures/ejemplo_real.json` y usarlo como test de aceptación.

---

**Empezá por la Fase 1.** No avances a la siguiente hasta que los tests de la fase actual estén pasando. Antes de cada fase, mostrame el plan que vas a seguir.
