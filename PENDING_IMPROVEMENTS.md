# Mejoras Pendientes

## 🔴 Prioridad Alta (Seguridad y Estabilidad)

### 1. **SQL Injection - Uso de f-strings en queries dinámicas**
**Archivos afectados:**
- `src/database/schema_inspector.py` (líneas 310, 398)
- `src/agent/nlp_agent.py` (líneas 715, 721, 771, 777, 848)

**Problema:**
```python
# ❌ Inseguro - f-string directo
count_query = f"SELECT COUNT(*) FROM {table_name} LIMIT 1000000"
sql = f"SELECT * FROM {table} LIMIT {limit_val}"
```

**Solución:**
```python
# ✅ Seguro - Usar text() con parámetros o validación estricta
# Opción 1: Validación estricta de nombres
if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
    raise ValueError(f"Invalid table name: {table_name}")
sql = f"SELECT * FROM {table_name} LIMIT {limit_val}"

# Opción 2: Usar identificadores SQLAlchemy
from sqlalchemy import text, quoted_name
table_id = quoted_name(table_name, quote=False)
query = text(f"SELECT * FROM {table_id} LIMIT :limit").bindparams(limit=limit_val)
```

**Impacto:** 🔴 **ALTO** - Riesgo de seguridad si nombres de tablas no están validados

---

### 2. **Schema Cache no funcional**
**Archivo:** `src/database/schema_inspector.py` (líneas 599-633)

**Problema:**
```python
def _load_from_cache(self) -> Optional[DatabaseContext]:
    # ...
    # Note: Full reconstruction would need more complex deserialization
    # For now, return None to force fresh analysis
    return None  # ⚠️ Siempre retorna None
```

**Solución:**
- Implementar serialización completa de `DatabaseContext`
- Guardar/recuperar `TableInfo` y `ColumnInfo` correctamente
- Usar `dataclasses.asdict()` y reconstrucción adecuada

**Impacto:** 🟡 **MEDIO** - Afecta rendimiento al recargar schema cada vez

---

## 🟡 Prioridad Media (Mejoras de Código)

### 3. **Logging - Reemplazar print() con logger**
**Archivo:** `src/agent/nlp_agent.py` (32 ocurrencias de `print()`)

**Problema:**
```python
# ❌ Debug con print()
print(f"✅ EXTRACTOR: Found SQL in dict['{key}']")
print(f"🔍 EXTRACTOR: Data string preview: {step[:200]}...")
```

**Solución:**
```python
# ✅ Usar logger apropiado
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Found SQL in dict['{key}']")
logger.debug(f"Data string preview: {step[:200]}...")
```

**Impacto:** 🟡 **MEDIO** - Mejora depuración y control de logs

---

### 4. **Validación de nombres de tablas mejorada**
**Archivo:** `src/agent/nlp_agent.py` (líneas 684, 838)

**Problema:**
```python
# Validación básica actual
if re.fullmatch(r"[A-Za-z0-9_]+", table):
    # ...
```

**Mejora:**
- Validar contra lista de tablas existentes en schema
- Verificar que la tabla existe antes de construir query
- Manejar nombres con espacios o caracteres especiales (usar quotes)

**Impacto:** 🟡 **MEDIO** - Previene errores y mejora UX

---

### 5. **Manejo de errores más específico**
**Archivos:** Múltiples archivos

**Problema:**
```python
# ❌ Genérico
except Exception as e:
    logger.warning(f"Failed: {e}")
```

**Mejora:**
```python
# ✅ Específico
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
except ValueError as e:
    logger.warning(f"Validation error: {e}")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
```

**Impacto:** 🟡 **MEDIO** - Mejor debugging y mensajes de error

---

## 🟢 Prioridad Baja (Optimizaciones)

### 6. **Conexiones - Manejo de timeouts y reconexiones**
**Archivo:** `src/database/snowflake_conn.py`

**Mejora:**
- Añadir timeouts configurables
- Implementar retry logic para conexiones perdidas
- Pool de conexiones más robusto

**Impacto:** 🟢 **BAJO** - Mejora estabilidad en entornos inestables

---

### 7. **Dependencias - Añadir langchain-ollama a requirements**
**Archivo:** `requirements.txt`

**Mejora:**
- Añadir `langchain-ollama>=0.2.0` como dependencia opcional
- Documentar claramente en README

**Impacto:** 🟢 **BAJO** - Reduce warnings de deprecación

---

### 8. **Documentación - Actualizar README**
**Archivo:** `README.md`

**Mejora:**
- Documentar mejoras realizadas
- Añadir sección de troubleshooting
- Actualizar ejemplos de uso

**Impacto:** 🟢 **BAJO** - Mejora experiencia de usuarios

---

## 📊 Resumen de Mejoras

| Prioridad | Cantidad | Impacto |
|-----------|----------|---------|
| 🔴 Alta   | 2        | Seguridad y estabilidad |
| 🟡 Media  | 3        | Calidad de código |
| 🟢 Baja   | 3        | Optimizaciones |

## 🚀 Plan de Implementación Sugerido

### Fase 1: Seguridad (🔴 Alta)
1. ✅ Fix SQL Injection - f-strings
2. ✅ Implementar Schema Cache funcional

### Fase 2: Calidad (🟡 Media)
3. ✅ Reemplazar print() con logger
4. ✅ Mejorar validación de tablas
5. ✅ Mejorar manejo de errores

### Fase 3: Optimización (🟢 Baja)
6. ✅ Mejorar manejo de conexiones
7. ✅ Actualizar dependencias
8. ✅ Actualizar documentación

## 📝 Notas

- Las mejoras de **Prioridad Alta** deberían implementarse primero por seguridad
- Las mejoras de **Prioridad Media** mejoran la mantenibilidad del código
- Las mejoras de **Prioridad Baja** son optimizaciones que pueden esperar

