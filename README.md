# Calculadora de Hierros

Optimizador de compra de armadura para obras de hormigón armado. Resuelve el problema de Cutting Stock 1D: dada una planilla de armaduras, calcula el mínimo de barras de 12 m a comprar combinando piezas dentro de cada barra.

App web en Streamlit + OR-Tools + Supabase.

---

## Cómo deployar la app en Streamlit Cloud (paso a paso)

### 1. Crear el repo en GitHub

1. Andá a https://github.com/new
2. Nombre: `calculadora-hierros` (o el que quieras)
3. Marcá **Private** (es tuyo, no compartido)
4. **NO** tildes "Initialize with README" (ya tenés uno local)
5. Click en **Create repository**

GitHub te va a dar un link tipo `git@github.com:tuusuario/calculadora-hierros.git`. Copialo.

### 2. Subir el código por primera vez

Desde la terminal, parado en la carpeta del proyecto:

```bash
git remote add origin git@github.com:tuusuario/calculadora-hierros.git
git branch -M main
git push -u origin main
```

(Si te pide login, GitHub te pide un Personal Access Token o que tengas SSH configurado. Si nunca lo hiciste, seguí https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

### 3. Configurar Supabase (1 sola vez)

Si todavía no creaste las tablas, andá a tu proyecto en https://supabase.com → SQL Editor → "New query" y pegá el contenido del archivo [`db/schema.sql`](db/schema.sql). Apretá **Run without RLS**.

### 4. Conectar Streamlit Cloud

1. Andá a https://share.streamlit.io
2. Login con tu cuenta de GitHub.
3. Click en **New app**.
4. Seleccioná tu repo `calculadora-hierros`, branch `main`, main file `app.py`.
5. **Antes** de deployar, click en **Advanced settings** → pestaña **Secrets**, y pegá:

   ```toml
   [auth]
   password = "hierros"

   [supabase]
   url = "https://ruiqqlmradbkahotappx.supabase.co"
   anon_key = "eyJhbGciOiJI..."
   ```

   (los mismos valores de tu `.streamlit/secrets.toml` local)

6. Click en **Deploy**. Tarda 2-5 minutos la primera vez.

Cuando termine, te da una URL pública tipo `https://calculadora-hierros.streamlit.app`. Esa es tu app, podés usarla desde cualquier compu o celular.

### 5. Actualizaciones futuras

Cada vez que cambies algo y hagas `git push`, Streamlit Cloud lo redeploya automáticamente en ~1 minuto.

---

## Para correr la app localmente

```bash
# Instalar dependencias (1 sola vez)
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# Levantar la app
.venv\Scripts\python -m streamlit run app.py
```

Abrí http://localhost:8501 en el navegador.

Login: usuario `mili`, contraseña `hierros` (configurable en `.streamlit/secrets.toml`).

---

## Tests

```bash
.venv\Scripts\python -m pytest tests/ -v
```

18 tests del optimizador, validados contra los datos del Excel original.

---

## Estructura

```
hierros/
├── app.py                       # entrypoint con login
├── pages/
│   ├── 1_Nuevo_Proyecto.py      # tabla editable + cálculo + descarga Excel
│   └── 2_Mis_Proyectos.py       # listado de proyectos guardados
├── core/
│   ├── models.py                # dataclasses Element, Project, CutPlan
│   ├── optimizer.py             # OR-Tools CP-SAT + fallback FFD
│   ├── excel_export.py          # genera el .xlsx descargable
│   ├── excel_import.py          # parser tolerante de planillas
│   ├── db.py                    # CRUD contra Supabase
│   ├── auth.py                  # guard de autenticación + sidebar
│   └── styles.py                # CSS de la app (paleta rosa)
├── db/
│   └── schema.sql               # tablas para Supabase
├── tests/
│   ├── test_optimizer.py
│   └── fixtures/ejemplo_real.json
└── .streamlit/
    ├── config.toml
    ├── secrets.toml             # local, NO se sube a Git
    └── secrets.toml.example     # plantilla
```

---

## Stack

- **Streamlit** — UI
- **OR-Tools** (Google) — solver del Cutting Stock
- **pandas + openpyxl** — lectura/escritura Excel
- **Supabase** (PostgreSQL) — persistencia de proyectos
- **Python 3.13**
