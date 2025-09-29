# 🏗️ Arquitectura del Sistema - Snowflake NLP Agent v2

## 📋 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🌐 STREAMLIT WEB APP                                │
│                          (streamlit_app.py)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  🎨 UI Components:                                                          │
│  ├─ 💬 Chat Interface (mensajes, historial)                                 │
│  ├─ 📊 Data Display (DataFrames, tablas formateadas)                       │
│  ├─ 🔧 Sidebar (configuración, estado conexión)                            │
│  └─ 📋 Logs Panel (trazabilidad proceso)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ user_input
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      🧠 NLP AGENT LAYER                                     │
│                   (src/agent/nlp_agent.py)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  🤖 Groq LLM    │    │  🔗 LangChain   │    │  📝 SQL Prompt  │         │
│  │ (Llama 3.3 70B) │◄──►│ SQLDatabaseChain│◄──►│   (English)     │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  Flujo:                                                                     │
│  1️⃣ Receives question in English                                               │
│  2️⃣ Generates SQL using LLM + custom prompt                                   │
│  3️⃣ Extracts SQL from intermediate_steps                                       │
│  4️⃣ Executes SQL directly in Snowflake                                        │
│  5️⃣ Logs steps for traceability                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ sql_query
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     🗄️  DATABASE LAYER                                      │
│                 (src/database/snowflake_conn.py)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ 🔌 Native       │    │ ⚙️  SQLAlchemy  │    │ 🔍 Schema       │         │
│  │ Connector       │    │    Engine       │    │ Inspector       │         │
│  │                 │    │ (NullPool)      │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  Métodos principales:                                                       │
│  • connect() - Establece conexión + validación                             │
│  • execute_query() - SQL → filas + columnas                                │
│  • get_connection_string() - Para LangChain                                │
│  • get_connection_info() - Metadatos sesión                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ sql_execution
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ❄️  SNOWFLAKE CLOUD                                  │
│                     (External Data Warehouse)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🏢 Account: RNSWQJK-IU53947                                               │
│  🗃️  Database: SNOWFLAKE_SAMPLE_DATA                                        │
│  📋 Schema: TPCH_SF1                                                        │
│  🏭 Warehouse: COMPUTE_WH                                                   │
│                                                                             │
│  📊 Tablas disponibles:                                                     │
│  ├─ CUSTOMER (clientes)                                                     │
│  ├─ ORDERS (pedidos)                                                        │
│  ├─ LINEITEM (líneas de pedido)                                             │
│  ├─ PART (productos)                                                        │
│  ├─ SUPPLIER (proveedores)                                                  │
│  └─ NATION, REGION (geografía)                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ query_results
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    📊 RESULT FORMATTING LAYER                              │
│                   (streamlit_app.py - formateo)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🔧 Funciones de formateo:                                                  │
│  ├─ parse_sql_result_string() - Parser strings → listas                    │
│  ├─ format_sql_result_to_dataframe() - Formateo inteligente                │
│  └─ Automatic detection of query types                                      │
│                                                                             │
│  🎯 Tipos de formateo soportados:                                           │
│  ├─ 💰 Pedidos con valores (formato monetario)                              │
│  ├─ 🗂️  Información de base de datos                                        │
│  ├─ 📋 Listado de tablas                                                    │
│  └─ 🔀 Formato genérico (fallback)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ formatted_dataframe
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       👤 USER INTERFACE                                    │
│                    (Browser @ localhost:8501)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📱 Resultados mostrados:                                                   │
│  ├─ 📊 Tablas interactivas (ancho completo)                                 │
│  ├─ 🔢 Contadores de registros                                              │
│  ├─ 💬 Historial de conversación persistente                                │
│  └─ 📋 Logs de proceso paso a paso                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Datos Detallado

### 1. 🎯 Entrada del Usuario
```
Usuario escribe: "¿Cuáles son los 10 pedidos con mayor valor?"
                                │
                                ▼
                    process_user_input()
                                │
                                ▼
                    st.session_state.agent.process_query()
```

### 2. 🧠 Procesamiento NLP
```
SnowflakeNLPAgent.process_query()
    │
    ├─ 🔍 Log: "Processing query"
    │
    ├─ 🤖 sql_chain.invoke(english_question)
    │   │
    │   ├─ Groq LLM genera SQL usando prompt personalizado
    │   ├─ Template incluye schema de tablas Snowflake
    │   └─ Devuelve: SQL + intermediate_steps
    │
    ├─ 📝 Extrae SQL de intermediate_steps[0]['sql_cmd']
    │   │
    │   └─ SQL: "SELECT o_orderkey, o_totalprice FROM orders ORDER BY o_totalprice DESC LIMIT 10"
    │
    ├─ 🧹 Normaliza SQL (remueve markdown, backticks)
    │
    ├─ 🚀 Ejecuta: self.db.run(cleaned_sql)
    │   │
    │   └─ Datos: [(1750466, Decimal('555285.16')), (4722021, Decimal('544089.09')), ...]
    │
    └─ 📊 Retorna: {success: True, result: datos, sql_query: sql}
```

### 3. 🎨 Formateo y Visualización
```
format_sql_result_to_dataframe(data, sql, question)
    │
    ├─ 🔍 Detects type: "highest value" → orders format
    │
    ├─ 💰 Applies monetary formatting: "$555,285.16"
    │
    ├─ 📋 Creates DataFrame with friendly columns:
    │   │
    │   └─ ['Order ID', 'Total Value']
    │
    └─ 📊 st.dataframe(df, use_container_width=True)
```

## 🏛️ Patrones de Arquitectura Utilizados

### 🔧 Patrones de Diseño

| Patrón | Implementación | Ubicación |
|--------|---------------|-----------|
| **🔄 Chain of Responsibility** | LangChain SQLDatabaseChain | `nlp_agent.py` |
| **🏭 Factory** | Connection string building | `snowflake_conn.py` |
| **🔍 Observer** | Logging system integration | Todos los módulos |
| **📦 Singleton** | Global config, connection instances | `config.py`, `helpers.py` |
| **🎯 Strategy** | Intelligent formatting by query type | `streamlit_app.py` |
| **🔒 Context Manager** | Database connections (`with` statements) | `snowflake_conn.py` |

### 🌊 Arquitectura por Capas

```
┌─────────────────────────────────────────────────────────────────┐
│  🎨 PRESENTATION LAYER (UI)                                     │
│  └─ Streamlit components, chat interface, data display         │
└─────────────────────────────────────────────────────────────────┘
           │ ▲
           ▼ │  
┌─────────────────────────────────────────────────────────────────┐
│  🧠 BUSINESS LOGIC LAYER (NLP Agent)                           │
│  └─ Natural language processing, SQL generation, execution     │
└─────────────────────────────────────────────────────────────────┘
           │ ▲
           ▼ │
┌─────────────────────────────────────────────────────────────────┐
│  🗄️  DATA ACCESS LAYER (Database Connection)                    │
│  └─ Snowflake connectivity, query execution, result parsing    │
└─────────────────────────────────────────────────────────────────┘
           │ ▲
           ▼ │
┌─────────────────────────────────────────────────────────────────┐
│  ❄️  EXTERNAL SERVICES (Snowflake + Groq)                      │
│  └─ Cloud data warehouse + LLM API services                    │
└─────────────────────────────────────────────────────────────────┘
```

## 🔐 Gestión de Configuración

```
┌─────────────────────────────────────────────────────────────────┐
│                    ⚙️  CONFIGURATION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  .env.example ────copy───► .env ────load───► config.py          │
│       │                     │                    │              │
│       │                     │                    ▼              │
│       │                     │         ┌─────────────────┐       │
│       │                     │         │ Environment     │       │
│       │                     │         │ Variables:      │       │
│       │                     │         │                 │       │
│       │                     │         │ SNOWFLAKE_*     │       │
│       │                     │         │ GROQ_API_KEY    │       │
│       │                     │         │ MODEL_NAME      │       │
│       │                     │         │ DEBUG           │       │
│       │                     │         └─────────────────┘       │
│       │                     │                    │              │
│       │                     │                    ▼              │
│       │                     │         ┌─────────────────┐       │
│       │                     │         │ Validation &    │       │
│       │                     │         │ Default Values  │       │
│       │                     │         └─────────────────┘       │
│       │                     │                    │              │
│       │                     │                    ▼              │
│       │                     │         ┌─────────────────┐       │
│       │                     │         │ Global Config   │       │
│       │                     │         │ Instance        │       │
│       │                     │         └─────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📈 Escalabilidad y Mantenimiento

### 🔧 Puntos de Extensión

1. **🌐 Nuevos Idiomas**: Modificar prompt en `nlp_agent.py`
2. **🗄️  Nuevas Bases de Datos**: Extender `database/` con nuevos conectores
3. **🎨 Nuevos Formatos**: Añadir casos en `format_sql_result_to_dataframe()`
4. **🤖 Nuevos LLMs**: Cambiar `ChatGroq` por otro proveedor en `nlp_agent.py`
5. **📊 Nuevas Visualizaciones**: Extender UI components en `streamlit_app.py`

### 🛡️ Aspectos de Seguridad

- ✅ **Variables de entorno** para credenciales sensibles
- ✅ **Validación de SQL** antes de ejecución  
- ✅ **Automatic LIMIT** in queries to avoid overloads
- ✅ **Connection pooling** controlado (NullPool)
- ✅ **Error handling** robusto en cada capa

### 📊 Monitoreo y Observabilidad

- 📋 **Logs paso a paso** en UI para transparencia
- 🔍 **Trazabilidad completa** del flujo NL → SQL → Resultados  
- ⏱️ **Timestamps** en logs para análisis de rendimiento
- 📈 **Contadores** de registros y estadísticas básicas

---

**🏗️ Esta arquitectura está diseñada para ser modular, extensible y mantenible, siguiendo principios de separación de responsabilidades y bajo acoplamiento.**
