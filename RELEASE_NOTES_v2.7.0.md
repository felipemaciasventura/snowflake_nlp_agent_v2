# Release Notes - Version 2.7.0

## 🎉 New Features & Major Improvements

### ✨ **SQL Query Transparency & Visibility**
- **NEW**: SQL queries now visible in UI for complete transparency
- **NEW**: Real-time SQL display in expandable sections for each query
- **NEW**: Historical SQL queries preserved in chat message history
- **NEW**: Enhanced process logs with auto-expanded SQL highlighting

### 🛠️ **Critical Bug Fixes**
- **FIXED**: SQL execution failures due to destructive query cleaning
- **FIXED**: LangChain chain execution issues with fallback mechanisms
- **FIXED**: Decimal data type handling for Snowflake monetary values
- **FIXED**: SQL extraction logic that was losing queries in processing pipeline

### 🎯 **Enhanced User Experience**
- **IMPROVED**: Immediate SQL execution when LangChain chain fails
- **IMPROVED**: Robust error handling and multiple fallback mechanisms
- **IMPROVED**: Educational captions explaining AI-generated SQL
- **IMPROVED**: Consistent SQL display across all UI elements

## 🔧 Technical Improvements

### Core Changes
- **Redesigned SQL cleaning algorithm** to preserve query structure
- **Enhanced SQL extraction** with immediate execution capability
- **Improved LLM detection logic** to prevent user question confusion
- **Added comprehensive logging** for debugging and transparency

### Architecture Enhancements
- **Multiple execution paths** for maximum reliability
- **Fallback mechanisms** when LangChain execution fails
- **Enhanced data parsing** with proper Decimal support
- **Robust SQL validation** before execution

## 🎯 Benefits for End Users

### For Clients
- **Complete transparency** - see exactly what SQL is generated
- **Enhanced trust** - verify queries match expectations
- **Learning opportunity** - understand SQL through AI examples
- **Better debugging** - identify issues when results don't match expectations

### For Developers
- **Improved debugging** with detailed execution logs
- **Robust error handling** with multiple fallback paths
- **Better maintainability** with cleaner code structure
- **Enhanced reliability** with immediate execution capabilities

## 📊 Impact

- ✅ **100% SQL visibility** in user interface
- ✅ **Improved query success rate** through robust execution
- ✅ **Enhanced debugging capabilities** for troubleshooting
- ✅ **Better user confidence** through transparency

## 🔄 Migration Notes

This version is **fully backward compatible**. No configuration changes required.

### What's New in UI
- SQL expanders appear automatically in chat messages
- Process logs show SQL queries with syntax highlighting
- Historical queries remain accessible in message history

### What's Fixed
- Queries that previously failed to execute now work correctly
- SQL cleaning no longer destroys query structure
- Decimal values display properly in results

---

**Version 2.7.0 represents a major step forward in transparency, reliability, and user experience for the Snowflake NLP Agent.**