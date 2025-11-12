# 📖 Guía de Consultas - Snowflake NLP Agent

## 🎯 Tipos de Consultas Soportadas

La aplicación soporta varios tipos de consultas en lenguaje natural (inglés). Aquí están organizadas por categoría con ejemplos.

---

## 1. 📊 Consultas de Metadatos (Procesadas Directamente)

Estas consultas son procesadas directamente sin usar el LLM, por lo que son más rápidas y precisas.

### 📋 Listar Tablas Disponibles

**Ejemplos:**
- `show tables`
- `show me tables`
- `show all tables`
- `list tables`
- `list all tables`
- `what tables are available?`
- `which tables do we have?`
- `tables available`
- `available tables`
- `table names`
- `all tables`

**Resultado:** Lista todas las tablas en el schema actual.

---

### 🔢 Contar Número de Tablas

**Ejemplos:**
- `how many tables are there?`
- `how many tables do we have?`
- `how many tables in the database?`
- `how many tables that we have on the database?`
- `count of tables`
- `number of tables`
- `total tables`
- `table count`

**Resultado:** Número total de tablas en el schema actual.

**Nota:** Esta consulta cuenta solo tablas y vistas (BASE TABLE y VIEW) en el schema actual.

---

### 🗄️ Información de Base de Datos

**Ejemplos:**
- `what database are we using?`
- `which database?`
- `current database`
- `database name`
- `what db?`
- `which db?`
- `current db`
- `db name`
- `what database we are using now?`

**Resultado:** Nombre de la base de datos actual.

---

### 📁 Información de Schema

**Ejemplos:**
- `what schema are we using?`
- `which schema?`
- `current schema`
- `schema name`
- `schema we are using`

**Resultado:** Nombre del schema actual.

---

### 👤 Información de Rol

**Ejemplos:**
- `what role are we using?`
- `which role?`
- `current role`
- `role name`
- `role we are using`

**Resultado:** Rol actual del usuario.

---

### 🏭 Información de Warehouse

**Ejemplos:**
- `what warehouse are we using?`
- `which warehouse?`
- `current warehouse`
- `warehouse name`
- `warehouse we are using`

**Resultado:** Warehouse actual.

---

### 👁️ Vista Previa de Tabla Específica

**Ejemplos:**
- `show me the customers table`
- `show customers table`
- `show me customers`
- `show customers`
- `show the properties table`
- `show properties`

**Resultado:** Muestra las primeras filas de la tabla especificada (por defecto 100 filas, configurable).

**Nota:** Si la tabla no existe, te sugerirá tablas similares.

---

## 2. 🔢 Consultas de Conteo (Procesadas Directamente)

Estas consultas son optimizadas para conteos simples.

### 📈 Contar Registros

**Ejemplos:**
- `how many customers are there?`
- `how many customers in the customers table?`
- `how many properties?`
- `count of customers`
- `count from customers`
- `how many transactions?`

**Resultado:** Número total de registros en la tabla.

**Patrones reconocidos:**
- `how many [table_name]`
- `how many [table_name] on/in [table_name] table`
- `count of/from [table_name]`

---

## 3. 📊 Consultas de Datos (Procesadas por LLM)

Estas consultas son procesadas por el LLM para generar SQL complejo.

### 🏆 Consultas de Ranking / Top N

**Ejemplos:**
- `show the 10 highest-value orders`
- `top 10 most expensive properties`
- `highest-value transactions`
- `most expensive properties by city`
- `agents with most sales`
- `top 5 customers by revenue`
- `cheapest properties`
- `lowest price properties`

**Resultado:** Lista ordenada de los elementos solicitados.

**Consejos:**
- Especifica el número: "top 10", "top 5", etc.
- Para precios/valores: usa "highest-value", "most expensive", "cheapest"
- Para conteos: usa "most", "least", "highest", "lowest"

---

### 📈 Consultas de Agregación

**Ejemplos:**
- `what's the average price per square foot?`
- `average sale price by city`
- `total revenue by agent`
- `sum of all transactions`
- `maximum price in properties`
- `minimum price in properties`
- `average commission of agents`
- `total count of properties per city`

**Funciones soportadas:**
- `average` / `avg`
- `sum` / `total`
- `count`
- `maximum` / `max`
- `minimum` / `min`

---

### 🔗 Consultas con JOINs

**Ejemplos:**
- `show properties with their locations`
- `list transactions with agent names`
- `properties with location details`
- `customers with their orders`
- `agents and their total sales`

**Resultado:** Datos combinados de múltiples tablas relacionadas.

---

### 🗺️ Consultas Geográficas

**Ejemplos:**
- `properties by city`
- `average price per city`
- `transactions by state`
- `most expensive properties by city`
- `properties in New York`
- `cities with most properties`

**Palabras clave:**
- `city`, `cities`
- `state`, `states`
- `county`, `counties`
- `location`, `locations`
- `region`, `regions`
- `area`, `areas`

---

### ⏰ Consultas Temporales

**Ejemplos:**
- `last 10 transactions`
- `recent properties`
- `latest transactions`
- `transactions from last month`
- `properties sold this year`
- `sales from past year`
- `transactions in the last 30 days`

**Palabras clave:**
- `last`, `recent`, `latest`
- `past month`, `past year`
- `this year`, `this month`
- `last 30 days`, `last week`

**Nota:** Solo se añaden filtros temporales si los mencionas explícitamente.

---

### 🔍 Consultas con Filtros

**Ejemplos:**
- `properties with more than 3 bedrooms`
- `properties with price greater than 500000`
- `agents with commission rate above 5%`
- `transactions with sale price over 1000000`
- `properties in New York with pool`
- `customers from California`

**Operadores implícitos:**
- `more than` → `>`
- `greater than` → `>`
- `less than` → `<`
- `above` → `>`
- `below` → `<`
- `over` → `>`
- `under` → `<`
- `with` → condiciones específicas

---

### 📊 Consultas de Análisis

**Ejemplos:**
- `for each city, get the average sale price`
- `properties grouped by property type`
- `transactions by agent with total sales`
- `average price per square foot by city`
- `commission rate distribution`
- `properties per city with average price`

**Palabras clave:**
- `for each`, `per`, `by`, `grouped by`
- `distribution`, `statistics`, `analysis`

---

### 🏠 Consultas Específicas de Real Estate

**Ejemplos:**
- `properties with bedrooms and bathrooms`
- `properties with pool and garage`
- `average price per square foot`
- `properties by property type`
- `agents with most transactions`
- `owners with multiple properties`
- `properties sold by agent`
- `locations with highest average price`

**Campos comunes:**
- `bedrooms`, `bathrooms`, `sqft`, `price`
- `property_type`, `sale_price`, `sale_date`
- `agent`, `owner`, `location`, `city`

---

## 4. 🎨 Mejores Prácticas para Formular Consultas

### ✅ DO (Haz esto)

1. **Sé específico:**
   - ✅ `show the 10 highest-value transactions`
   - ❌ `show transactions`

2. **Usa palabras clave claras:**
   - ✅ `average price per city`
   - ❌ `price city average`

3. **Especifica límites cuando sea necesario:**
   - ✅ `top 10 most expensive properties`
   - ✅ `last 5 transactions`

4. **Menciona filtros temporales explícitamente:**
   - ✅ `transactions from last month`
   - ✅ `properties sold this year`

5. **Usa nombres de tablas en singular o plural:**
   - ✅ `how many customers?`
   - ✅ `show me properties`

---

### ❌ DON'T (Evita esto)

1. **No uses SQL directo:**
   - ❌ `SELECT * FROM customers`
   - ✅ `show me customers`

2. **No uses markdown o código:**
   - ❌ ````sql SELECT ...`
   - ✅ `show me properties`

3. **No uses caracteres especiales innecesarios:**
   - ❌ `show me customers!!!`
   - ✅ `show me customers`

4. **No mezcles idiomas:**
   - ❌ `muéstrame customers` (solo inglés)
   - ✅ `show me customers`

5. **No uses consultas fuera del contexto de la base de datos:**
   - ❌ `what's the weather today?`
   - ✅ `what's the average price in properties?`

---

## 5. 📝 Ejemplos Completos por Categoría

### Consultas Básicas
```
show tables
what database are we using?
show me customers
how many properties are there?
```

### Consultas de Ranking
```
show the 10 highest-value orders
top 5 most expensive properties
agents with most sales
cheapest properties by city
```

### Consultas de Agregación
```
what's the average price per square foot?
total revenue by agent
average sale price by city
maximum price in properties
```

### Consultas con JOINs
```
show properties with their locations
list transactions with agent names
properties with location details
```

### Consultas Geográficas
```
properties by city
average price per city
most expensive properties by city
properties in New York
```

### Consultas Temporales
```
last 10 transactions
recent properties
transactions from last month
properties sold this year
```

### Consultas con Filtros
```
properties with more than 3 bedrooms
properties with price greater than 500000
agents with commission rate above 5%
```

### Consultas de Análisis
```
for each city, get the average sale price
properties grouped by property type
average price per square foot by city
```

---

## 6. 🔧 Configuración de Límites

### Límite de Filas por Defecto

Por defecto, las consultas muestran hasta **100 filas** para vistas previas de tablas. Esto es configurable en `.env`:

```bash
SHOW_TABLE_LIMIT=100
```

### Sampling Opcional

Puedes habilitar sampling probabilístico para tablas grandes:

```bash
SHOW_TABLE_SAMPLE_PERCENT=0.1  # 0.1% de la tabla
```

---

## 7. 🎯 Tips para Mejores Resultados

### 1. **Usa el contexto del dominio**
Si tu base de datos es de real estate, usa términos como:
- `properties`, `agents`, `transactions`, `locations`
- `price`, `sale_price`, `commission`
- `bedrooms`, `bathrooms`, `sqft`

### 2. **Sé específico con números**
- ✅ `top 10` en lugar de `top`
- ✅ `more than 3 bedrooms` en lugar de `many bedrooms`

### 3. **Menciona filtros temporales explícitamente**
- ✅ `transactions from last month`
- ❌ `recent transactions` (puede ser ambiguo)

### 4. **Usa nombres de tablas correctos**
- Verifica los nombres de tablas con `show tables`
- La aplicación te sugerirá tablas similares si cometes un error

### 5. **Consulta metadatos primero**
- `show tables` para ver tablas disponibles
- `what database are we using?` para confirmar contexto

---

## 8. 🚨 Manejo de Errores

### Tabla No Encontrada

Si consultas una tabla que no existe:
```
Error: Table 'CUSTOMERS' not found in current schema. 
Did you mean: CUSTOMER, CUSTOMER_ORDERS, CUSTOMER_REVIEWS?
```

**Solución:** Usa uno de los nombres sugeridos.

### Consulta Ambigua

Si la consulta es ambigua, el LLM generará la mejor interpretación posible. Si no es lo que esperas, sé más específico.

**Ejemplo:**
- ❌ `show me orders` (¿qué órdenes?)
- ✅ `show me the 10 highest-value orders`
- ✅ `show me orders from last month`

---

## 9. 📚 Recursos Adicionales

### Ver el SQL Generado

En la interfaz de Streamlit, puedes ver el SQL generado en el panel de logs. Esto te ayuda a:
- Entender cómo se interpreta tu consulta
- Aprender patrones de SQL
- Depurar consultas que no funcionan como esperas

### Schema Cache

El schema se cachea automáticamente para mejorar el rendimiento. Si cambias el schema:
- Reinicia la aplicación para refrescar el cache
- O borra `data/schema_cache.json` manualmente

---

## 10. 🎓 Ejemplos Avanzados

### Consultas Complejas con Múltiples Condiciones

```
properties with more than 3 bedrooms and price less than 500000 in New York
```

### Consultas con Agregaciones y Agrupaciones

```
for each city, show the average price and total number of properties
```

### Consultas con Rankings y Filtros

```
top 10 most expensive properties by city with more than 2 bedrooms
```

### Consultas con Múltiples JOINs

```
show properties with their locations and agent names, ordered by price
```

---

## 🎉 ¡Comienza a Consultar!

La mejor manera de aprender es probando. Empieza con consultas simples y luego ve aumentando la complejidad.

**Ejemplos para empezar:**
1. `show tables`
2. `how many properties are there?`
3. `show me the customers table`
4. `top 10 most expensive properties`
5. `average price per city`

¡Disfruta consultando tu base de datos en lenguaje natural! 🚀

