# 🤖 Snowflake NLP Agent v2

Una aplicación web inteligente construida con Streamlit que permite realizar consultas en lenguaje natural (español) a bases de datos Snowflake, utilizando LangChain con soporte dual para Groq/Llama y Google Gemini para conversión automática de texto a SQL con detección híbrida de consultas.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![Snowflake](https://img.shields.io/badge/snowflake-supported-blue.svg)

## 🌟 Características Principales

- **💬 Interfaz de Chat Intuitiva**: Conversación natural con tu base de datos
- **🧠 Procesamiento NLP Híbrido**: Detección inteligente de consultas (BD vs ayuda vs fuera de contexto)
- **🔄 Soporte Dual de LLM**: Compatible con Groq/Llama y Google Gemini con auto-detección
- **📊 Visualización Inteligente**: Formateo automático de resultados con tablas interactivas
- **🔒 Conexión Segura**: Integración robusta con Snowflake usando credenciales encriptadas
- **🎯 Respuestas Educativas**: Guía inteligente para usuarios con ejemplos y redirección amigable
- **🎨 Interfaz Moderna**: Diseño responsivo con Streamlit y componentes interactivos

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.8+
- Cuenta de Snowflake con credenciales de acceso
- **API Key de Groq** (opción 1) para modelos Llama
- **API Key de Google Gemini** (opción 2) para modelos Gemini
- Al menos uno de los dos proveedores LLM configurado

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

# Proveedores LLM - Configurar al menos uno
# Groq (opción 1)
GROQ_API_KEY=tu-groq-api-key
MODEL_NAME=llama-3.3-70b-versatile

# Google Gemini (opción 2) 
GOOGLE_API_KEY=tu-google-api-key
GEMINI_MODEL=gemini-1.5-flash

# Selección de proveedor (auto, groq, gemini)
LLM_PROVIDER=auto

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

### 🔍 Consultas de Bases de Datos

```
🔹 "?¿Cuáles son los 10 pedidos con mayor valor?"
🔹 "Muéstrame las ventas de este mes"
🔹 "?¿Cuántos clientes hay en total?"
🔹 "Lista los productos más vendidos"
🔹 "?¿Qué base de datos estoy usando?"
🔹 "Muestra las tablas disponibles"
🔹 "?¿Cuál es el promedio de ingresos por región?"
```

### 🎯 Consultas de Ayuda (Respuesta Educativa)

```
🔹 "?¿En qué me puedes ayudar?"
🔹 "?¿Qué puedes hacer?"
🔹 "?¿Cómo funciona esta aplicación?"
🔹 "Muéstrame ejemplos de lo que puedes hacer"
```

### 🚫 Consultas Fuera de Contexto (Redirección Amigable)

```
🔹 "?¿Cómo está el clima?"
🔹 "Cuéntame un chiste"
🔹 "?¿Qué películas recomiendas?"
→ Se redirige amigablemente a funcionalidades de BD
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
│   │   └── snowflake_conn.py
│   └── ⚙️  utils/              # Configuración y helpers
│       ├── config.py
│       └── helpers.py
├── 📋 requirements.txt        # Dependencias Python
├── 🔧 .env.example           # Template configuración
└── 📚 WARP.md                # Documentación desarrollo
```

### Tecnologías Clave

| Tecnología | Propósito | Versión |
|------------|-----------|----------|
| **Streamlit** | Framework web | 1.28+ |
| **LangChain** | Orquestación LLM | 0.1+ |
| **Groq** | API LLM (Llama 3.3) ✅ | Latest |
| **Google Gemini** | API LLM (Gemini 1.5) ✅ | Latest |
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
| `GROQ_API_KEY` | API Key Groq (opción 1) | 🔄 | `gsk_...` |
| `GOOGLE_API_KEY` | API Key Google Gemini (opción 2) | 🔄 | `AIza...` |
| `MODEL_NAME` | Modelo Groq | ❌ | `llama-3.3-70b-versatile` |
| `GEMINI_MODEL` | Modelo Gemini | ❌ | `gemini-1.5-flash` |
| `LLM_PROVIDER` | Selección proveedor | ❌ | `auto`, `groq`, `gemini` |

**Nota:** 🔄 = Al menos uno de los dos proveedores LLM debe estar configurado

### Comandos de Desarrollo

```bash
# Ejecutar con puerto específico
streamlit run streamlit_app.py --server.port 8080

# Modo desarrollo con logs detallados
DEBUG=True streamlit run streamlit_app.py

# Producción (servidor público)
streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0


# Verificar sintaxis
python -m py_compile streamlit_app.py

# Linting
flake8 src/ streamlit_app.py
```

## 🔬 Ejemplo de Flujo Detallado

Para entender cómo funciona la magia detrás de escena, sigamos el viaje de una pregunta simple a través del sistema.

**Pregunta del usuario:** `¿Cuáles son los 10 clientes que más han gastado?`

---

#### **Paso 1: Interfaz de Usuario (Streamlit)**

1.  **Entrada del Usuario**: El usuario escribe la pregunta en el chat de la aplicación web (`streamlit_app.py`).
2.  **Procesamiento de Entrada**: La aplicación guarda y muestra inmediatamente el mensaje del usuario en la interfaz.
3.  **Llamada al Agente**: Se invoca al núcleo del sistema: `agent.process_query(...)`.

---

#### **Paso 2: Capa del Agente NLP (LangChain + Groq)**

4.  **Inicio del Procesamiento**: El `SnowflakeNLPAgent` (`src/agent/nlp_agent.py`) recibe la consulta.
5.  **Construcción del Prompt**: La `SQLDatabaseChain` de LangChain combina la pregunta del usuario con el esquema de las tablas de la base de datos y una plantilla de prompt en español.
6.  **Invocación del LLM**: Se envía el prompt completo a la API de Groq, que utiliza el modelo `llama-3.3-70b-versatile`.
7.  **Generación de SQL**: El LLM, guiado por el prompt, genera la consulta SQL correspondiente.
    ```sql
    SELECT c.c_name, SUM(o.o_totalprice) AS total_gastado
    FROM CUSTOMER c
    JOIN ORDERS o ON c.c_custkey = o.o_custkey
    GROUP BY c.c_name
    ORDER BY total_gastado DESC
    LIMIT 10
    ```
8.  **Extracción de SQL**: El agente extrae la consulta SQL generada de la respuesta de LangChain.

---

#### **Paso 3: Capa de Acceso a Datos (Snowflake)**

9.  **Ejecución de la Consulta**: El agente ejecuta la consulta SQL a través de la capa de conexión a la base de datos (`src/database/snowflake_conn.py`).
10. **Procesamiento en Snowflake**: Snowflake recibe la consulta, la ejecuta en su motor de cómputo y devuelve los resultados. Por ejemplo:
    ```
    [('Customer#0001', Decimal('555285.16')), ('Customer#0002', Decimal('544089.09')), ...]
    ```
11. **Recepción de Resultados**: La aplicación recibe estos resultados (una lista de tuplas).

---

#### **Paso 4: Formateo y Visualización (Streamlit)**

12. **Formateo Inteligente**: Una función de utilidad (`format_sql_result_to_dataframe`) convierte la lista de tuplas en un DataFrame de Pandas, aplicando formato de moneda y nombres de columna amigables.
13. **Visualización Final**:
    *   La aplicación muestra el DataFrame formateado en una tabla interactiva.
    *   Muestra un contador debajo de la tabla: `📊 10 registros encontrados`.
    *   La respuesta completa se guarda en el historial del chat.

---

#### **Paso 5: Trazabilidad (Logs en UI)**

14. **Panel de Logs**: Durante todo el proceso, se registran logs detallados que se muestran en el panel lateral, ofreciendo total transparencia sobre lo que hizo el sistema, desde la SQL que generó hasta los resultados que obtuvo.

## 🔄 Actualizaciones Recientes (v2.2)

### ✅ Nuevas Características Principales

- **🔄 Soporte Dual de LLM**: Groq/Llama + Google Gemini con auto-detección
- **🧠 Detección Híbrida**: Clasificación inteligente de consultas (BD vs ayuda vs fuera de contexto)
- **🎯 Respuestas Educativas**: Guía completa con ejemplos para usuarios nuevos
- **🚀 Redirección Amigable**: Respuestas amigables para consultas fuera de contexto
- **📊 Información Dinámica**: Sidebar muestra el modelo LLM activo en tiempo real

### ✅ Mejoras Anteriores (v2.1)

- **🎯 Formateo Inteligente**: Reconocimiento automático de tipos de consulta
- **💹 Formato Monetario**: Visualización automática de valores financieros
- **🔧 Parsing Robusto**: Manejo avanzado de objetos Decimal de Snowflake
- **⚡ Modelo Actualizado**: Llama 3.3 70B Versatile + Gemini 1.5 Flash
- **🖥️ UI Mejorada**: Tablas de ancho completo y contadores de registros

### 🐛 Correcciones

- ✅ Método obsoleto `__call__` reemplazado por `invoke`
- ✅ Manejo robusto de errores DataFrame constructor
- ✅ Parsing de strings con resultados SQL complejos
- ✅ Configuración dinámica de proveedores LLM
- ✅ Detección automática de modelos disponibles

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
