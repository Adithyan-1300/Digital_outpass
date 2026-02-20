import traceback

print('Testing import of backend.config and DB connection')
try:
    import backend.config as cfg
    print('Imported backend.config successfully')
    conn = cfg.get_db_connection()
    if conn:
        print('Database connection obtained:', type(conn))
        try:
            conn.close()
        except Exception:
            pass
    else:
        print('get_db_connection() returned None (no connection)')
except Exception as e:
    print('Exception while importing or connecting:')
    traceback.print_exc()
