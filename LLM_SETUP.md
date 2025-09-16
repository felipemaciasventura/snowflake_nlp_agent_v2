# 🤖 Guía Rápida: Configuración de Proveedores LLM

Esta guía te ayuda a configurar y cambiar entre los diferentes proveedores de modelos de lenguaje (LLM) disponibles en **Snowflake NLP Agent v2.3**.

## 🎯 Proveedores Disponibles

| Proveedor | Modelo | Ubicación | Costo | Privacidad | Velocidad |
|-----------|--------|-----------|-------|------------|-----------|
| **🏠 Ollama** | CodeLlama 7B | Local | 💚 **Gratis** | 🔒 **Máxima** | ⚡ **Rápida** |
| **🟢 Gemini** | Gemini 1.5 Flash | Cloud | 💛 **Económico** | 🔄 **Media** | ⚡ **Muy Rápida** |
| **🔵 Groq** | Llama 3.3 70B | Cloud | 🧡 **Moderado** | 🔄 **Media** | 🚀 **Ultra Rápida** |

## 🚀 Configuración Rápida por Proveedor

### 🏠 Opción 1: Ollama (Modelo Local - RECOMENDADO para Privacidad)

```bash
# 1. Configurar variables en .env
OLLAMA_BASE_URL=http://localhost:11434  # O tu servidor Ollama
OLLAMA_MODEL=codellama:7b-instruct
LLM_PROVIDER=ollama

# 2. Verificar que Ollama esté ejecutándose
curl http://localhost:11434/api/tags

# 3. Ejecutar aplicación
source venv/bin/activate && streamlit run streamlit_app.py --server.port 8502
```

**✅ Ventajas:**
- 🔒 **Privacidad total** - Sin datos enviados a internet
- 💰 **Costo cero** - Sin gastos de API
- 🛡️ **Offline** - Funciona sin conexión a internet
- 🎯 **Especializado** - CodeLlama optimizado para SQL

**⚠️ Requisitos:**
- Servidor Ollama configurado
- Modelo CodeLlama descargado
- Al menos 4GB RAM disponible

---

### 🟢 Opción 2: Gemini (Cloud - RECOMENDADO por Defecto)

```bash
# 1. Obtener API Key de Google AI Studio
# https://aistudio.google.com/app/apikey

# 2. Configurar variables en .env
GOOGLE_API_KEY=tu-google-api-key-aqui
GEMINI_MODEL=gemini-1.5-flash
LLM_PROVIDER=gemini

# 3. Ejecutar aplicación
source venv/bin/activate && streamlit run streamlit_app.py --server.port 8502
```

**✅ Ventajas:**
- ⚡ **Muy rápido** - Respuesta casi instantánea
- 💡 **Inteligente** - Excelente comprensión de contexto
- 💰 **Económico** - Precios competitivos
- 🌐 **Reliable** - Alta disponibilidad

---

### 🔵 Opción 3: Groq (Cloud - Ultra Velocidad)

```bash
# 1. Obtener API Key de Groq Console
# https://console.groq.com/keys

# 2. Configurar variables en .env
GROQ_API_KEY=gsk_tu-groq-api-key-aqui
MODEL_NAME=llama-3.3-70b-versatile
LLM_PROVIDER=groq

# 3. Ejecutar aplicación
source venv/bin/activate && streamlit run streamlit_app.py --server.port 8502
```

**✅ Ventajas:**
- 🚀 **Ultra rápido** - Inferencia extremadamente veloz
- 🧠 **Potente** - Modelo Llama 70B parámetros
- 🎯 **Preciso** - Excelente para SQL complejo

---

## ⚙️ Auto-Detección Inteligente

Si configuraste múltiples proveedores, usa **auto-detección** para selección automática:

```bash
# En .env
LLM_PROVIDER=auto

# Prioridad automática: Ollama > Gemini > Groq
# (Prioriza modelos locales por privacidad)
```

## 🔄 Cambio Rápido de Proveedores

### Durante Desarrollo:
```bash
# Cambiar a Ollama
export LLM_PROVIDER=ollama
streamlit run streamlit_app.py

# Cambiar a Gemini
export LLM_PROVIDER=gemini
streamlit run streamlit_app.py

# Cambiar a Groq
export LLM_PROVIDER=groq
streamlit run streamlit_app.py
```

### Para Producción:
```bash
# Editar .env y reiniciar
nano .env
# Cambiar: LLM_PROVIDER=gemini
# Reiniciar aplicación
```

## 📊 Comparación de Rendimiento

### Para SQL Simple (ej: "lista clientes"):
| Proveedor | Tiempo Promedio | Precisión | Recomendación |
|-----------|----------------|-----------|---------------|
| **Ollama** | ~3-5s | 95% | 🏠 **Uso personal/privado** |
| **Gemini** | ~1-2s | 98% | 🏢 **Producción general** |
| **Groq** | ~0.5-1s | 97% | ⚡ **Aplicaciones tiempo real** |

### Para SQL Compleja (ej: "top 10 clientes por región"):
| Proveedor | Tiempo Promedio | Precisión | Recomendación |
|-----------|----------------|-----------|---------------|
| **Ollama** | ~5-8s | 90% | 🏠 **Casos no críticos** |
| **Gemini** | ~2-3s | 95% | 🏢 **Balanceado** |
| **Groq** | ~1-2s | 98% | 🚀 **Análisis avanzado** |

## 🐛 Solución de Problemas

### Ollama no conecta:
```bash
# Verificar estado
ollama list
systemctl status ollama  # Linux
brew services list | grep ollama  # macOS

# Reiniciar servicio
sudo systemctl restart ollama  # Linux
brew services restart ollama  # macOS
```

### Error API Key Gemini:
```bash
# Verificar key
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"test"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=TU_API_KEY"
```

### Error API Key Groq:
```bash
# Verificar key
curl -X POST \
  -H "Authorization: Bearer gsk_TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"model":"llama-3.3-70b-versatile"}' \
  "https://api.groq.com/openai/v1/chat/completions"
```

## 💡 Recomendaciones por Escenario

### 🏠 **Uso Personal/Desarrollo:**
- **Ollama** - Privacidad y costo cero
- Configuración: `LLM_PROVIDER=ollama`

### 🏢 **Producción Empresarial:**
- **Gemini** - Balance precio/rendimiento/confiabilidad
- Configuración: `LLM_PROVIDER=gemini`

### ⚡ **Aplicaciones Tiempo Real:**
- **Groq** - Máxima velocidad de inferencia
- Configuración: `LLM_PROVIDER=groq`

### 🔒 **Datos Sensibles:**
- **Ollama** - Procesamiento 100% local
- Configuración: `LLM_PROVIDER=ollama`

### 🌐 **Multi-Región:**
- **Auto-detección** - Failover automático
- Configuración: `LLM_PROVIDER=auto`

---

## 📋 Lista de Verificación Pre-Despliegue

### ✅ Configuración Mínima:
- [ ] Al menos un proveedor LLM configurado
- [ ] Variables de entorno validadas
- [ ] Conexión Snowflake funcionando
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)

### ✅ Para Ollama Local:
- [ ] Servidor Ollama ejecutándose
- [ ] Modelo CodeLlama descargado
- [ ] Red accesible (si servidor remoto)
- [ ] Recursos suficientes (RAM/CPU)

### ✅ Para Gemini:
- [ ] API Key válida de Google AI Studio
- [ ] Límites de cuota configurados
- [ ] Billing habilitado (si necesario)

### ✅ Para Groq:
- [ ] API Key válida de Groq Console
- [ ] Límites de rate entendidos
- [ ] Backup provider configurado

---

**🚀 ¡Listo para usar! Tu Snowflake NLP Agent v2.3 está configurado con el proveedor LLM óptimo para tu caso de uso.**