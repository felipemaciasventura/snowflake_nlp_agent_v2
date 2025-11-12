"""
Result formatting utilities for SQL query results
"""

import ast
import re
from decimal import Decimal

import pandas as pd
import streamlit as st

# Regex constants
DECIMAL_REGEX = r"Decimal\('([^']+)'\)"


def parse_sql_result_string(result_string):
    """Parse a string with SQL results and convert it to real data"""

    # If it's not a string or doesn't have expected format, return as is
    if not isinstance(result_string, str) or not result_string.strip():
        return result_string

    # Clean input string
    cleaned_string = result_string.strip()

    try:
        # Case 1: List of tuples [(...), (...)]
        if cleaned_string.startswith("[") and cleaned_string.endswith("]"):
            # Replace Decimal('...') with float
            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            
            # Replace datetime.date(Y, M, D) with 'YYYY-MM-DD'
            def _date_repl(match):
                y, m, d = match.group(1), match.group(2), match.group(3)
                try:
                    y_i, m_i, d_i = int(y), int(m), int(d)
                    return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                except Exception:
                    return match.group(0)
            
            cleaned_string = re.sub(
                r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
                _date_repl,
                cleaned_string,
            )
            
            # Replace None with 'None' for safe evaluation
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            # Try to evaluate as Python literal
            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

        # Case 2: Simple tuple (...)
        elif cleaned_string.startswith("(") and cleaned_string.endswith(")"):
            # Convert simple tuple to list of tuples
            cleaned_string = f"[{cleaned_string}]"
            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            
            # Replace datetime.date
            def _date_repl(match):
                y, m, d = match.group(1), match.group(2), match.group(3)
                try:
                    y_i, m_i, d_i = int(y), int(m), int(d)
                    return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                except Exception:
                    return match.group(0)
            
            cleaned_string = re.sub(
                r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
                _date_repl,
                cleaned_string,
            )
            
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

        # Case 3: String that seems to be data but not well formatted
        elif "Decimal(" in cleaned_string or "None" in cleaned_string or "datetime.date(" in cleaned_string:
            # Try to fix the format
            if not cleaned_string.startswith("["):
                cleaned_string = f"[{cleaned_string}]"

            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            
            # Replace datetime.date
            def _date_repl(match):
                y, m, d = match.group(1), match.group(2), match.group(3)
                try:
                    y_i, m_i, d_i = int(y), int(m), int(d)
                    return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                except Exception:
                    return match.group(0)
            
            cleaned_string = re.sub(
                r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
                _date_repl,
                cleaned_string,
            )
            
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

    except (ValueError, SyntaxError, TypeError):
        # Parsing errors are normal for complex data like datetime
        # The fallback will handle the case

        # Fallback: try to extract data using regex
        try:
            # Look for tuple patterns with numbers
            tuple_pattern = r"\(([^)]+)\)"
            matches = re.findall(tuple_pattern, cleaned_string)

            if matches:
                parsed_tuples = []
                for match in matches:
                    # Separate elements by comma
                    elements = [elem.strip().strip("'\"") for elem in match.split(",")]
                    # Convert numbers when possible
                    converted_elements = []
                    for elem in elements:
                        try:
                            # Try to convert to number
                            if "." in elem:
                                converted_elements.append(float(elem))
                            else:
                                converted_elements.append(int(elem))
                        except ValueError:
                            # If not a number, keep as string
                            converted_elements.append(elem)

                    parsed_tuples.append(tuple(converted_elements))

                return parsed_tuples

        except Exception:
            # Fallback also failed, will return original string
            pass

    # If everything fails, return original string
    return result_string


def extract_column_names_from_sql(sql_query, db_connection=None):
    """Extract meaningful column names from SQL query using aliases or column names.
    
    For SELECT * queries, if db_connection is provided, attempts to get actual column names from table.
    """
    # If it's already a list of column names, return it directly
    if isinstance(sql_query, list):
        return sql_query

    if not sql_query or not isinstance(sql_query, str):
        return None

    # Clean the SQL query
    sql_clean = sql_query.strip().upper()

    try:
        # For CTEs (WITH statements), find the LAST SELECT statement
        # which is usually the main query
        all_selects = re.findall(
            r"SELECT\s+(.*?)\s+FROM", sql_clean, re.DOTALL | re.IGNORECASE
        )

        if not all_selects:
            return None

        # Use the LAST SELECT (main query, not CTE)
        select_part = all_selects[-1].strip()

        # Handle SELECT * case
        if select_part.strip() == "*":
            # Try to get actual column names from table if we have db connection
            if db_connection is not None:
                # Extract table name from the FROM clause
                from_match = re.search(
                    r"FROM\s+(\w+)", sql_clean, re.IGNORECASE
                )
                if from_match:
                    table_name = from_match.group(1)
                    try:
                        # Query the database for column names
                        column_query = f"""
                        SELECT COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = '{table_name}' 
                        ORDER BY ORDINAL_POSITION
                        """
                        result = db_connection.run(column_query)
                        if result:
                            # Extract column names and make them readable
                            column_names = []
                            for row in result:
                                if isinstance(row, (tuple, list)) and len(row) > 0:
                                    col_name = str(row[0]).replace("_", " ").title()
                                    column_names.append(col_name)
                                elif isinstance(row, str):
                                    col_name = row.replace("_", " ").title()
                                    column_names.append(col_name)
                            
                            if column_names:
                                print(f"✅ COLUMN EXTRACTOR: Found {len(column_names)} columns for table {table_name}")
                                return column_names
                    except Exception as e:
                        print(f"❌ COLUMN EXTRACTOR: Failed to get columns for {table_name}: {e}")
            
            # Fallback: return None for SELECT * when we can't get actual column names
            return None

        # Smart split by comma: respect commas inside parentheses
        # This handles functions like date_trunc('month', column) correctly
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
                # This is a real column separator, not a comma inside a function
                if current_expr.strip():
                    column_expressions.append(current_expr.strip())
                current_expr = ""
            else:
                current_expr += char
        
        # Don't forget the last expression
        if current_expr.strip():
            column_expressions.append(current_expr.strip())

        column_names = []

        for expr in column_expressions:
            # Case 1: Look for AS alias (e.g., "column_name AS alias")
            as_match = re.search(r"\bAS\s+([\w_]+)$", expr, re.IGNORECASE)
            if as_match:
                alias = as_match.group(1).lower()
                # Convert to more readable format
                readable_name = alias.replace("_", " ").title()
                column_names.append(readable_name)
                continue

            # Case 2: Look for function calls with aliases (e.g., "COUNT(*) AS count")
            func_as_match = re.search(
                r"\w+\([^)]*\)\s+AS\s+([\w_]+)", expr, re.IGNORECASE
            )
            if func_as_match:
                alias = func_as_match.group(1).lower()
                readable_name = alias.replace("_", " ").title()
                column_names.append(readable_name)
                continue

            # Case 3: Simple column reference (e.g., "p.property_id", "city")
            simple_col_match = re.search(r"(?:[\w]+\.)?([\w_]+)$", expr)
            if simple_col_match:
                col_name = simple_col_match.group(1).lower()
                readable_name = col_name.replace("_", " ").title()
                column_names.append(readable_name)
                continue

            # Case 4: Function calls without aliases (e.g., "COUNT(*)", "AVG(price)")
            func_match = re.search(r"(\w+)\(", expr)
            if func_match:
                func_name = func_match.group(1).upper()
                if func_name == "COUNT":
                    column_names.append("Count")
                elif func_name == "AVG":
                    column_names.append("Average")
                elif func_name == "SUM":
                    column_names.append("Total")
                elif func_name == "MAX":
                    column_names.append("Maximum")
                elif func_name == "MIN":
                    column_names.append("Minimum")
                elif func_name == "CURRENT_DATABASE":
                    column_names.append("Database")
                elif func_name == "CURRENT_SCHEMA":
                    column_names.append("Schema")
                else:
                    column_names.append(func_name.title())
                continue

            # Fallback: use a generic name
            column_names.append(f"Column {len(column_names) + 1}")

        return column_names if column_names else None

    except Exception:
        # If parsing fails, return None to use fallback
        return None


def format_sql_result_to_dataframe(data, sql_query="", user_question="", db_connection=None):
    """Convert SQL results into a well-formatted DataFrame"""
    # Smart formatting of SQL results

    try:
        # Case 1: If it's a string, try to parse it first
        if isinstance(data, str):
            # Try to parse if it looks like SQL data
            if data.startswith("[") or data.startswith("("):
                parsed_data = parse_sql_result_string(data)
                if parsed_data != data:  # If it could be parsed
                    data = parsed_data
                    # String parsed successfully
                else:
                    return pd.DataFrame({"Result": [data]})
            else:
                return pd.DataFrame({"Result": [data]})

        # Normalize single-row structures into a list so downstream logic works uniformly
        # Single SQLAlchemy Row
        if not isinstance(data, list) and hasattr(data, "_mapping"):
            data = [data]
        # Single dict row
        if isinstance(data, dict):
            data = [data]
        # Single tuple/list row
        if isinstance(data, tuple):
            data = [data]

        # Case 2: If there's no data or it's not a list
        if not isinstance(data, list) or not data:
            return pd.DataFrame({"Result": ["No data"]})

        # Normalization utilities (used across formats)
        def _normalize_value(v):
            # Normalize common DB types for Arrow compatibility
            if isinstance(v, (bytes, bytearray)):
                try:
                    return v.decode("utf-8", errors="ignore")
                except Exception:
                    return str(v)
            if isinstance(v, Decimal):
                try:
                    return float(v)
                except Exception:
                    return str(v)
            return v

        def _readable_names(names):
            return [str(n).replace("_", " ").title() for n in names]

        # Pre-extract column names from SQL if possible
        extracted_column_names = extract_column_names_from_sql(sql_query, db_connection)

        # Debug logging for column extraction
        if hasattr(st, "session_state") and hasattr(
            st.session_state, "processing_logs"
        ):
            st.session_state.processing_logs.append(
                {
                    "step": "📋 Column Extraction",
                    "content": f"SQL: {sql_query[:100] if sql_query else 'None'}..., "
                    f"Extracted columns: {extracted_column_names}, "
                    f"Data first row: {data[0] if data else 'None'}",
                    "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
                }
            )

        # Case 3: Handle rows returned as SQLAlchemy Row/RowMapping or dicts
        first_row = data[0]
        # SQLAlchemy Row -> use _mapping for stable order
        if hasattr(first_row, "_mapping") and hasattr(first_row._mapping, "keys"):
            mapping_keys = list(first_row._mapping.keys())
            rows = []
            for r in data:
                vals = [_normalize_value(r._mapping[k]) for k in mapping_keys]
                rows.append(vals)
            # Prefer names extracted from SQL if they match; else mapping keys prettified
            if extracted_column_names and len(extracted_column_names) == len(
                mapping_keys
            ):
                columns = extracted_column_names
            else:
                columns = _readable_names(mapping_keys)
            return pd.DataFrame(rows, columns=columns)

        # Dict rows
        if isinstance(first_row, dict):
            dict_keys = list(first_row.keys())
            rows = []
            for r in data:
                vals = [_normalize_value(r.get(k)) for k in dict_keys]
                rows.append(vals)
            if extracted_column_names and len(extracted_column_names) == len(dict_keys):
                columns = extracted_column_names
            else:
                columns = _readable_names(dict_keys)
            return pd.DataFrame(rows, columns=columns)

        # Case 5: COUNT queries (Enhanced for real estate domain)
        if "COUNT(*)" in sql_query.upper() or "COUNT(1)" in sql_query.upper():
            if len(data) > 0 and len(data[0]) == 1:
                count_value = data[0][0]
                user_lower = user_question.lower()

                # Determine what's being counted based on the query context
                if "agent" in user_lower:
                    description = "Total real estate agents"
                elif "property" in user_lower or "properties" in user_lower:
                    description = "Total properties"
                elif "transaction" in user_lower or "sale" in user_lower:
                    description = "Total transactions"
                elif "owner" in user_lower:
                    description = "Total property owners"
                elif "location" in user_lower:
                    description = "Total locations"
                elif "table" in user_lower:
                    description = "Total database tables"
                elif "customer" in user_lower or "client" in user_lower:
                    description = "Total customers"
                elif "order" in user_lower:
                    description = "Total orders"
                else:
                    # Try to extract table name from SQL for generic description
                    table_match = re.search(
                        r"FROM\s+([a-zA-Z0-9_]+)", sql_query.upper()
                    )
                    if table_match:
                        table_name = table_match.group(1).lower()
                        description = f"Total records in {table_name} table"
                    else:
                        description = "Total records"

                return pd.DataFrame(
                    [{"Description": description, "Count": f"{count_value:,}"}]
                )

        # Case 6: For CURRENT_DATABASE
        if "CURRENT_DATABASE" in sql_query.upper():
            return pd.DataFrame(data, columns=["Database"])

        # Case 7: For SHOW TABLES
        if "SHOW TABLES" in sql_query.upper():
            if len(data) > 0 and len(data[0]) >= 2:
                table_data = []
                for row in data:
                    table_data.append(
                        {
                            "Table": row[1],
                            "Type": row[4] if len(row) > 4 else "TABLE",
                            "Description": (
                                row[5] if len(row) > 5 else "No description"
                            ),
                        }
                    )
                return pd.DataFrame(table_data)

        # Case 8: For region-based queries (English only)
        if "region" in user_question.lower() and len(data) > 0 and len(data[0]) == 2:
            # Detect if it's average, sum, total, etc.
            if "average" in user_question.lower() or "avg" in sql_query.lower():
                metric_name = "Average Revenue"
            elif "sum" in user_question.lower() or "total" in user_question.lower():
                metric_name = "Total Revenue"
            elif "count" in sql_query.lower():
                metric_name = "Count"
            else:
                metric_name = "Value"

            formatted_rows = []
            for row in data:
                region = row[0]
                value = row[1]

                # Format value as currency if numeric
                if isinstance(value, (int, float, Decimal)):
                    value_formatted = f"${float(value):,.2f}"
                else:
                    value_formatted = str(value)

                formatted_rows.append({"Region": region, metric_name: value_formatted})

            return pd.DataFrame(formatted_rows)

        # Case 9: Default - create DataFrame with intelligent column names
        try:
            # Debug logging for default case
            if hasattr(st, "session_state") and hasattr(
                st.session_state, "processing_logs"
            ):
                st.session_state.processing_logs.append(
                    {
                        "step": "📊 Default DataFrame Creation",
                        "content": f"Data type: {type(data[0]) if data else 'None'}, "
                        f"Data length: {len(data) if data else 0}, "
                        f"Extracted columns: {extracted_column_names}, "
                        f"First row cols: {len(data[0]) if data and hasattr(data[0], '__len__') else 'N/A'}",
                        "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
                    }
                )

            # Normalize tuple/list rows
            if len(data) > 0 and isinstance(data[0], (tuple, list)):
                num_cols = len(data[0]) if data[0] else 1
                normalized_rows = [[_normalize_value(v) for v in row] for row in data]
                if extracted_column_names and len(extracted_column_names) == num_cols:
                    df = pd.DataFrame(normalized_rows, columns=extracted_column_names)
                    return df
                # Fall back to generic names to avoid unnamed columns
                df = pd.DataFrame(
                    normalized_rows, columns=[f"Column {i+1}" for i in range(num_cols)]
                )
                return df

            # Fallback attempt
            df = pd.DataFrame([[_normalize_value(v) for v in data]])
            return df
        except Exception:
            # If it fails, try with intelligent column names
            try:
                if len(data) > 0 and isinstance(data[0], (tuple, list)):
                    # Try to extract column names from SQL first
                    num_cols = len(data[0]) if data[0] else 1

                    if (
                        extracted_column_names
                        and len(extracted_column_names) == num_cols
                    ):
                        column_names = extracted_column_names
                    else:
                        # Create more descriptive generic column names
                        column_names = [f"Column {i+1}" for i in range(num_cols)]

                    normalized_rows = [
                        [_normalize_value(v) for v in row] for row in data
                    ]
                    df = pd.DataFrame(normalized_rows, columns=column_names)
                    return df
                else:
                    # Data in unexpected format
                    df = pd.DataFrame(
                        {"Result": data if isinstance(data, list) else [data]}
                    )
                    return df
            except Exception:
                # Last resort: convert everything to string
                return pd.DataFrame({"Result": [str(data)]})

    except Exception:
        # Formatting error, use robust handling with intelligent column names
        try:
            # Try to create basic DataFrame
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (tuple, list)):
                    # List of tuples/lists - try to extract column names from SQL
                    extracted_column_names = extract_column_names_from_sql(sql_query, db_connection)
                    num_cols = len(data[0]) if data[0] else 1

                    if (
                        extracted_column_names
                        and len(extracted_column_names) == num_cols
                    ):
                        column_names = extracted_column_names
                    else:
                        # Use more readable generic names
                        column_names = [f"Column {i+1}" for i in range(num_cols)]

                    return pd.DataFrame(data, columns=column_names)
                else:
                    # Simple list
                    return pd.DataFrame({"Result": data})
            else:
                # Generic case
                return pd.DataFrame({"Result": [str(data)]})
        except Exception:
            # Absolute last resort
            return pd.DataFrame(
                {"Error": [f"Could not process data: {str(data)[:100]}..."]}
            )














