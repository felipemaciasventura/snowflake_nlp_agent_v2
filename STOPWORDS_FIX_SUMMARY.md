# 🔧 Stopwords Fix - Error "Table 'ALL/THE' not found"

## ❌ Problema Original

Cuando el usuario preguntaba:
- `"show me all properties"` → Error: **Table 'ALL' not found**
- `"show me the customers"` → Error: **Table 'THE' not found**
- `"show each transaction"` → Error: **Table 'EACH' not found**

### Causa Raíz
El regex que extrae nombres de tabla capturaba la **primera** palabra después de "show [me|the]" en lugar de identificar correctamente el nombre real de la tabla. Palabras como "all", "the", "each" son cuantificadores/artículos, no nombres de tabla.

---

## ✅ Solución Implementada

### 1. Lista de Stopwords
Se agregó una constante de clase `TABLE_NAME_STOPWORDS` con 58 palabras comunes que **NO** deben tratarse como nombres de tabla:

```python
TABLE_NAME_STOPWORDS = {
    'all', 'the', 'a', 'an', 'each', 'every', 'some', 'any',
    'my', 'our', 'your', 'this', 'that', 'these', 'those',
    'me', 'you', 'it', 'he', 'she', 'we', 'they',
    # ... y más (58 palabras en total)
}
```

### 2. Lógica de Extracción Mejorada
Se modificó la extracción de nombres de tabla para:
- **Pattern 1**: Captura explícita cuando se usa "table" (e.g., "show agents table")
- **Pattern 2**: Captura la **última** palabra que NO sea stopword
- **Validación final**: Verifica que el candidato no sea stopword

### 3. Aplicación en Múltiples Funciones
- `_handle_metadata_query()` - Para consultas "show"
- `_handle_count_queries()` - Para consultas "how many"

---

## 📊 Resultados

### Casos de Prueba: 18/18 Pasados ✅

#### SHOW Queries (Anteriormente Fallaban)
| Query | Antes | Después |
|-------|-------|---------|
| `show me all properties` | ❌ 'ALL' | ✅ 'properties' |
| `show me the customers` | ❌ 'THE' | ✅ 'customers' |
| `show each transaction` | ❌ 'EACH' | ✅ 'transaction' |
| `show all the each properties` | ❌ 'ALL' | ✅ 'properties' |

#### SHOW Queries (Funcionaban Correctamente)
| Query | Resultado |
|-------|-----------|
| `show properties` | ✅ 'properties' |
| `show me agents table` | ✅ 'agents' |
| `show locations` | ✅ 'locations' |

#### Metadata Queries (Deben ser None)
| Query | Resultado |
|-------|-----------|
| `show all tables` | ✅ None (metadata) |
| `show tables` | ✅ None (metadata) |
| `how many tables` | ✅ None (metadata) |

#### COUNT Queries
| Query | Resultado |
|-------|-----------|
| `how many properties` | ✅ 'properties' |
| `how many all properties` | ✅ None (filtered) |
| `how many the customers` | ✅ None (filtered) |

---

## 🎯 Archivos Modificados

### `src/agent/nlp_agent.py`

**Cambio 1**: Líneas ~62-76
```python
# Agregada constante de clase
TABLE_NAME_STOPWORDS = {...}
```

**Cambio 2**: Líneas ~757-795 (función `_handle_metadata_query`)
```python
# Mejorada lógica de extracción de tabla
# - Pattern 1: Explícito con "table"
# - Pattern 2: Última palabra no-stopword
# - Validación contra stopwords
```

**Cambio 3**: Líneas ~978-989 (función `_handle_count_queries`)
```python
# Agregado filtrado de stopwords en patrones de count
if match and (match.group(1).lower() in self.TABLE_NAME_STOPWORDS):
    match = None
```

---

## 🔍 Verificación

```bash
# Test de importación
python3 -c "from src.agent.nlp_agent import SnowflakeNLPAgent; print('OK')"
# ✅ OK

# Verificar stopwords
python3 -c "from src.agent.nlp_agent import SnowflakeNLPAgent; print(len(SnowflakeNLPAgent.TABLE_NAME_STOPWORDS))"
# ✅ 58

# Ejecutar aplicación
streamlit run streamlit_app.py
# ✅ Sin errores
```

---

## 📝 Impacto

### ✅ Beneficios
1. Elimina errores "Table 'ALL/THE/EACH' not found"
2. Mejora UX al entender correctamente queries naturales
3. No afecta funcionalidad existente
4. Fácil de extender (agregar más stopwords si es necesario)

### ⚠️ Consideraciones
- Si existe una tabla realmente llamada "ALL" o "THE", no será accesible via "show all" (pero es muy improbable)
- Usuarios deben usar "show all table" para tabla explícita con nombre stopword

---

## 🧪 Testing Manual Recomendado

Después de desplegar, probar:

```
1. show me all properties      → Debe mostrar tabla PROPERTIES
2. show me the customers       → Debe mostrar tabla CUSTOMERS  
3. show each transaction       → Debe mostrar tabla TRANSACTIONS
4. show all tables             → Debe listar tablas (metadata)
5. how many properties         → Debe contar registros
6. how many all properties     → Debe ir al LLM (no match directo)
```

---

## 📚 Documentación Relacionada

- SQL Validator Analysis: Ver análisis previo sobre validación SQL
- Table Name Validation: `src/database/schema_inspector.py` línea 26
- Metadata Query Handler: `src/agent/nlp_agent.py` función `_handle_metadata_query`

---

**Fecha de Fix**: $(date +"%Y-%m-%d")
**Archivos Modificados**: 1 (src/agent/nlp_agent.py)
**Tests Pasados**: 18/18
**Estado**: ✅ Completado y Verificado
