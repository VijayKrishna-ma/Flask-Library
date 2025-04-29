import oracledb

# OracleDB connection setup
def get_connection():
    try:
        conn = oracledb.connect(
            user="system",
            password="password",
            dsn="localhost:1521/XEPDB1"
        )
        return conn
    except oracledb.Error as e:
        print("Error connecting to OracleDB:", e)
        return None

# Helper function to execute a SELECT query
def execute_select(query, params=()):
    conn = get_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        columns = [col[0] for col in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return rows
    except Exception as e:
        print("Select query error:", e)
        return None
    finally:
        conn.close()

# Helper function to execute INSERT/UPDATE/DELETE query
def execute_query(query, params=()):
    conn = get_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print("Query execution error:", e)
        return False
    finally:
        conn.close()
