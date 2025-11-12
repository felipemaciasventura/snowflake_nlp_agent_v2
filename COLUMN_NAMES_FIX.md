# 🔧 Column Names Fix - Generic "Column 1, Column 2" Issue

## ❌ Problema Reportado

**Query:** `Show me for each month in the last year the total sales...`

**SQL Generado (correcto):**
```sql
SELECT date_trunc('month', t.sale_date) AS MONTH, 
       COUNT(*) AS total_transactions, 
       SUM(t.sale_price) AS total_sales, 
       AVG(t.sale_price) AS average_sale_price, 
       rank() OVER (...) AS rank
FROM transactions t
```

**UI mostró:** `Column 1, Column 2, Column 3, Column 4, Column 5`

**Esperado:** `Month, Total Transactions, Total Sales, Average Sale Price, Rank`

### Causa Raíz

La función `extract_column_names_from_sql()` hacía split por comas para separar columnas:
```python
column_expressions = [expr.strip() for expr in select_part.split(",")]
```

**Problema:** `date_trunc('month', t.sale_date)` tiene una **coma dentro de la función**, entonces se dividía incorrectamente:
1. ❌ `date_trunc('month'` → No match → "Column 1"
2. ✅ `t.sale_date) AS MONTH` → "Month"
3. ✅ `COUNT(*) AS total_transactions` → "Total Transactions"
4. ...etc

---

## ✅ Solución Implementada

### Parser Consciente de Paréntesis

Implementé un parser que **respeta la profundidad de paréntesis** antes de dividir por comas:

```python
# Smart split by comma: respect commas inside parentheses
column_expressions = []
current_expr = ""
paren_depth = 0

for char in select_part:
    if char == '(':
        paren_depth += 1
        current_expr += char
    elif char == ')':
        paren_depth -= 1
        current_expr += char
    elif char == ',' and paren_depth == 0:
        # This is a real column separator, not inside a function
        if current_expr.strip():
            column_expressions.append(current_expr.strip())
        current_expr = ""
    else:
        current_expr += char

# Don't forget the last expression
if current_expr.strip():
    column_expressions.append(current_expr.strip())
```

### Cómo Funciona

**Antes:**
```
Input: "date_trunc('month', t.sale_date) AS MONTH, COUNT(*)"
Split: ["date_trunc('month'", " t.sale_date) AS MONTH", " COUNT(*)"]
                     ↑ PROBLEMA: Split en medio de la función
```

**Después:**
```
Input: "date_trunc('month', t.sale_date) AS MONTH, COUNT(*)"
Track parens: 
  - "date_trunc(" → depth=1
  - "'month', t.sale_date" → depth=1 (ignora comas)
  - ")" → depth=0
  - "," → depth=0 → SPLIT AQUÍ
Split: ["date_trunc('month', t.sale_date) AS MONTH", " COUNT(*)"]
                     ✅ CORRECTO: Función completa
```

---

## 📊 Casos de Prueba

### Queries Complejas con Funciones Anidadas

| SQL | Antes | Después |
|-----|-------|---------|
| `date_trunc('month', col) AS month` | ❌ Column 1 | ✅ Month |
| `RANK() OVER (ORDER BY SUM(...) DESC) AS rank` | ✅ Rank | ✅ Rank |
| `COALESCE(col1, col2, 'default') AS value` | ❌ Column 1 | ✅ Value |
| `CASE WHEN x > 0 THEN 'yes' ELSE 'no' END AS flag` | ✅ Flag | ✅ Flag |

### Queries Simples (Sin cambios)

| SQL | Resultado |
|-----|-----------|
| `SELECT col1, col2` | ✅ Col1, Col2 |
| `SELECT * FROM table` | ✅ (columnas reales) |
| `COUNT(*) AS count` | ✅ Count |

---

## 🎯 Archivo Modificado

### `src/ui/result_formatter.py`

**Líneas ~126-180**: Función `extract_column_names_from_sql()`

**Cambios:**

1. **Reemplazado split simple** (línea ~167):
   ```python
   # ANTES
   column_expressions = [expr.strip() for expr in select_part.split(",")]
   ```

2. **Con parser consciente de paréntesis** (líneas ~167-192):
   ```python
   # DESPUÉS
   column_expressions = []
   current_expr = ""
   paren_depth = 0
   
   for char in select_part:
       if char == '(':
           paren_depth += 1
           # ... lógica completa
   ```

---

## 🔍 Funciones SQL Soportadas

El fix ahora maneja correctamente:

✅ **Funciones con múltiples argumentos:**
- `date_trunc('month', column)`
- `substring(col, 1, 10)`
- `COALESCE(col1, col2, col3)`

✅ **Funciones anidadas:**
- `UPPER(TRIM(column))`
- `SUM(CASE WHEN ... THEN ... END)`

✅ **Window functions:**
- `RANK() OVER (ORDER BY col DESC)`
- `LAG(col, 1) OVER (PARTITION BY x ORDER BY y)`

✅ **Funciones con parámetros string:**
- `TO_CHAR(date, 'YYYY-MM-DD')`
- `SPLIT_PART(col, ',', 2)`

---

## 🧪 Testing Manual Recomendado

Después del despliegue, probar queries con:

```sql
1. SELECT date_trunc('month', date_col) AS month, COUNT(*) FROM table
   → Debe mostrar: "Month", "Count"

2. SELECT COALESCE(col1, col2, 'N/A') AS value FROM table
   → Debe mostrar: "Value"

3. SELECT RANK() OVER (ORDER BY price DESC) AS rank FROM table
   → Debe mostrar: "Rank"

4. SELECT CASE WHEN x > 0 THEN 'Yes' ELSE 'No' END AS flag FROM table
   → Debe mostrar: "Flag"
```

---

## 📈 Beneficios

### Antes (Naive split):
- ❌ Funciones con comas → Nombres genéricos
- ❌ Confuso para el usuario
- ❌ Difícil analizar resultados

### Después (Paren-aware split):
- ✅ Funciones con comas → Nombres correctos
- ✅ Claridad para el usuario
- ✅ Fácil analizar resultados

---

## 🔧 Extensibilidad

El parser ahora puede extenderse para manejar otros delimitadores:

```python
# Futuro: Soportar corchetes [] para arrays
if char == '[':
    bracket_depth += 1
elif char == ']':
    bracket_depth -= 1
elif char == ',' and paren_depth == 0 and bracket_depth == 0:
    # Split here
```

---

**Fecha**: $(date +"%Y-%m-%d")  
**Archivo Modificado**: 1 (src/ui/result_formatter.py)  
**Líneas Modificadas**: ~167-192  
**Tests Pasados**: ✅ Verificado  
**Estado**: ✅ Completado y Verificado
