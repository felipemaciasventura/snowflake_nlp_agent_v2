# Solución para errores de instalación en Python 3.12+

## Problema
Al instalar dependencias en Python 3.12+, puedes encontrar errores relacionados con:
1. `distutils` no disponible (removido en Python 3.12+)
2. PyYAML intentando compilar desde código fuente

## Solución Rápida

### Opción 1: Instalar setuptools primero (Recomendado)
```bash
# Activa tu entorno virtual
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows

# Instala setuptools primero (proporciona distutils como backport)
pip install --upgrade setuptools>=68.0.0

# Luego instala las dependencias
pip install -r requirements.txt
```

### Opción 2: Forzar uso de wheels precompilados
```bash
# Activa tu entorno virtual
source .venv/bin/activate

# Instala setuptools y PyYAML con wheel precompilado
pip install --upgrade setuptools>=68.0.0
pip install --only-binary :all: pyyaml>=6.0.1

# Luego instala el resto
pip install -r requirements.txt
```

### Opción 3: Instalación paso a paso
```bash
# Activa tu entorno virtual
source .venv/bin/activate

# 1. Actualiza pip, setuptools y wheel
pip install --upgrade pip setuptools>=68.0.0 wheel

# 2. Instala PyYAML con wheel
pip install --only-binary :all: pyyaml>=6.0.1

# 3. Instala Streamlit (versión actualizada)
pip install --upgrade streamlit>=1.39.0

# 4. Instala el resto de dependencias
pip install -r requirements.txt
```

## Verificación

Después de la instalación, verifica que todo esté correcto:

```bash
# Verifica que Streamlit funciona
streamlit --version

# Verifica que PyYAML está instalado
python -c "import yaml; print(yaml.__version__)"

# Ejecuta la aplicación
streamlit run streamlit_app.py
```

## Notas

- `setuptools>=68.0.0` incluye `distutils` como backport para Python 3.12+
- `pyyaml>=6.0.1` tiene wheels precompilados para Python 3.12+
- `streamlit>=1.39.0` no requiere `distutils`








