# 🤖 Snowflake NLP Agent v2

Una aplicación web inteligente construida con Streamlit que permite realizar consultas en lenguaje natural (español) a bases de datos Snowflake, utilizando LangChain y Groq LLM para conversión automática de texto a SQL.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![Snowflake](https://img.shields.io/badge/snowflake-supported-blue.svg)

## 🌟 Características Principales

- **💬 Interfaz de Chat Intuitiva**: Conversación natural con tu base de datos
- **🧠 Procesamiento NLP Avanzado**: Convierte preguntas en español a consultas SQL precisas
- **📊 Visualización Inteligente**: Formateo automático de resultados con tablas interactivas
- **🔒 Conexión Segura**: Integración robusta con Snowflake usando credenciales encriptadas
- **⚡ Rendimiento Optimizado**: Modelo Llama 3.3 70B Versatile para respuestas rápidas y precisas
- **🎨 Interfaz Moderna**: Diseño responsivo con Streamlit y componentes interactivos

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.8+
- Cuenta de Snowflake con credenciales de acceso
- API Key de Groq para servicios LLM

### 1. Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/snowflake_nlp_agent_v2.git
cd snowflake_nlp_agent_v2

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

```bash
# Copiar template de configuración
cp .env.example .env

# Editar .env con tus credenciales
nano .env
```

Configurar las siguientes variables en `.env`:

```env
# Credenciales Snowflake
SNOWFLAKE_ACCOUNT=tu-account-url
SNOWFLAKE_USER=tu-usuario
SNOWFLAKE_PASSWORD=tu-password
SNOWFLAKE_WAREHOUSE=tu-warehouse
SNOWFLAKE_DATABASE=tu-database
SNOWFLAKE_SCHEMA=PUBLIC

# Groq LLM API
GROQ_API_KEY=tu-groq-api-key
MODEL_NAME=llama-3.3-70b-versatile

# Opcional
DEBUG=False
```

### 3. Ejecutar la Aplicación

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar aplicación
streamlit run streamlit_app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 💻 Ejemplos de Uso

### Consultas en Español

```
🔹 "¿Cuáles son los 10 pedidos con mayor valor?"
🔹 "Muéstrame las ventas de este mes"
🔹 "¿Cuántos clientes hay en total?"
🔹 "Lista los productos más vendidos"
🔹 "¿Qué base de datos estoy usando?"
🔹 "Muestra las tablas disponibles"
```

### Resultados Automáticos

La aplicación genera automáticamente:
- ✅ **Consultas SQL** optimizadas y validadas
- 📊 **Tablas formateadas** con nombres de columnas amigables
- 💰 **Formato monetario** para valores financieros
- 📈 **Contadores de registros** y estadísticas
- 🔍 **Historial de conversación** persistente

## 🏗️ Arquitectura

### Estructura del Proyecto

```
snowflake_nlp_agent_v2/
├── 📄 streamlit_app.py         # Aplicación principal
├── 📁 src/
│   ├── 🤖 agent/              # Lógica NLP y LangChain
│   │   └── nlp_agent.py
│   ├── 🗄️  database/           # Conexión Snowflake
│   │   ├── snowflake_conn.py
│   │   └── schema_inspector.py
│   └── ⚙️  utils/              # Configuración y helpers
│       ├── config.py
│       └── helpers.py
├── 🧪 tests/                  # Suite de pruebas
├── 📋 requirements.txt        # Dependencias Python
├── 🔧 .env.example           # Template configuración
└── 📚 WARP.md                # Documentación desarrollo
```

### Tecnologías Clave

| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| **Streamlit** | Framework web | 1.28+ |
| **LangChain** | Orquestación LLM | 0.1+ |
| **Groq** | API LLM (Llama 3.3) | Latest |
| **Snowflake** | Data Warehouse | Connector 3.0+ |
| **Pandas** | Manipulación datos | 1.5+ |
| **SQLAlchemy** | ORM y conexiones | 2.0+ |

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Requerido | Ejemplo |
|----------|-------------|-----------|---------|
| `SNOWFLAKE_ACCOUNT` | URL cuenta Snowflake | ✅ | `tu-org-account` |
| `SNOWFLAKE_USER` | Usuario Snowflake | ✅ | `usuario@empresa.com` |
| `SNOWFLAKE_PASSWORD` | Contraseña usuario | ✅ | `password123` |
| `SNOWFLAKE_WAREHOUSE` | Warehouse a usar | ✅ | `COMPUTE_WH` |
| `SNOWFLAKE_DATABASE` | Base de datos | ✅ | `PROD_DB` |
| `SNOWFLAKE_SCHEMA` | Schema por defecto | ❌ | `PUBLIC` |
| `GROQ_API_KEY` | API Key Groq | ✅ | `gsk_...` |
| `MODEL_NAME` | Modelo LLM | ❌ | `llama-3.3-70b-versatile` |

### Comandos de Desarrollo

```bash
# Ejecutar con puerto específico
streamlit run streamlit_app.py --server.port 8080

# Modo desarrollo con logs detallados
DEBUG=True streamlit run streamlit_app.py

# Producción (servidor público)
streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0

# Ejecutar tests
python -m pytest tests/

# Verificar sintaxis
python -m py_compile streamlit_app.py

# Linting
flake8 src/ streamlit_app.py
```

## 🔄 Actualizaciones Recientes (v2.1)

### ✅ Nuevas Características

- **🎯 Formateo Inteligente**: Reconocimiento automático de tipos de consulta
- **💹 Formato Monetario**: Visualización automática de valores financieros
- **🔧 Parsing Robusto**: Manejo avanzado de objetos Decimal de Snowflake
- **⚡ Modelo Actualizado**: Llama 3.3 70B Versatile para mejor rendimiento
- **🖥️ UI Mejorada**: Tablas de ancho completo y contadores de registros
- **🏭 Producción Lista**: Código limpio sin debug statements

### 🐛 Correcciones

- ✅ Método obsoleto `__call__` reemplazado por `invoke`
- ✅ Parsing de strings con resultados SQL complejos
- ✅ Manejo de conexiones Snowflake mejorado
- ✅ Visualización de datos en formato tabla legible

## 🤝 Contribución

1. **Fork** el proyecto
2. Crear branch para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir **Pull Request**

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

¿Problemas o preguntas?

- 📧 **Email**: soporte@empresa.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/tu-usuario/snowflake_nlp_agent_v2/issues)
- 📚 **Documentación**: Ver `WARP.md` para detalles técnicos

## 🙏 Agradecimientos

- **Streamlit** por el framework web increíble
- **LangChain** por la orquestación de LLM
- **Groq** por los servicios de LLM rápidos
- **Snowflake** por la plataforma de datos robusta

---

**Desarrollado con ❤️ usando Python y tecnologías modernas de IA**
