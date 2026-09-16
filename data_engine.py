import os
import shutil
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Path resolution: Vercel serverless has a read-only filesystem except /tmp.
# When running on Vercel (or any read-only environment), we copy the bundled
# data_pesos.db to /tmp at startup and use that as the writable database.
# ---------------------------------------------------------------------------
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_BUNDLED_DB = os.path.join(_PROJECT_DIR, "data_pesos.db")
_TMP_DB = os.path.join("/tmp", "data_pesos.db")

def _get_writable_db_path():
    """Return a writable path for the SQLite database.
    On Vercel / Lambda the project dir is read-only; use /tmp instead."""
    project_db = _BUNDLED_DB
    # Check if we can write to the project directory
    try:
        test_file = os.path.join(_PROJECT_DIR, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return project_db  # local dev: use project directory
    except OSError:
        # Read-only filesystem (Vercel / serverless). Use /tmp.
        if not os.path.exists(_TMP_DB):
            if os.path.exists(project_db):
                shutil.copyfile(project_db, _TMP_DB)
        return _TMP_DB

DB_PATH = _get_writable_db_path()
EXCEL_PATH = os.path.join(_PROJECT_DIR, "Data pesos.xlsx")

T_COLS = [f"t{i}" for i in range(1, 49)]

def sync_database_if_needed():
    """Ensure data_pesos.db is created and updated if Excel is newer."""
    if not os.path.exists(EXCEL_PATH):
        return

    needs_rebuild = False
    if not os.path.exists(DB_PATH):
        needs_rebuild = True
    else:
        try:
            conn_chk = sqlite3.connect(DB_PATH)
            cur_chk = conn_chk.cursor()
            cur_chk.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sobrepesos_tecnologia'")
            if not cur_chk.fetchone():
                needs_rebuild = True
            cur_chk.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produccion'")
            if not cur_chk.fetchone():
                needs_rebuild = True
            conn_chk.close()
        except Exception:
            needs_rebuild = True

        if not needs_rebuild:
            excel_mtime = os.path.getmtime(EXCEL_PATH)
            db_mtime = os.path.getmtime(DB_PATH)
            if excel_mtime > db_mtime:
                needs_rebuild = True

    if needs_rebuild:
        print(f"Building SQLite database from {EXCEL_PATH}...")
        try:
            import shutil, tempfile, subprocess
            import openpyxl

            temp_dir = tempfile.gettempdir()
            temp_excel = os.path.join(temp_dir, "temp_data_pesos_sync.xlsx")
            
            # Copy with PowerShell to safely read even if Excel has the file locked
            try:
                subprocess.run(
                    ['powershell', '-NoProfile', '-NonInteractive', '-Command', f'Copy-Item -LiteralPath \'{EXCEL_PATH}\' -Destination \'{temp_excel}\' -Force'],
                    check=True, capture_output=True
                )
                read_path = temp_excel
            except Exception:
                try:
                    shutil.copyfile(EXCEL_PATH, temp_excel)
                    read_path = temp_excel
                except Exception:
                    read_path = EXCEL_PATH

            wb = openpyxl.load_workbook(read_path, data_only=True, read_only=True)
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            cur = conn.cursor()

            # 1. Sheet SOBREPESOS (Fixed dehydration overweight % per packaging technology)
            if 'SOBREPESOS' in wb.sheetnames:
                cur.execute('DROP TABLE IF EXISTS sobrepesos_tecnologia')
                cur.execute('''
                    CREATE TABLE sobrepesos_tecnologia (
                        tecnologia TEXT PRIMARY KEY,
                        pct_deshidratacion REAL
                    )
                ''')
                ws_sobre = wb['SOBREPESOS']
                for r in list(ws_sobre.iter_rows(values_only=True))[1:]:
                    if r[0]:
                        tech_name = str(r[0]).strip()
                        pct_val = float(r[1]) if r[1] is not None else 0.0
                        cur.execute('INSERT OR REPLACE INTO sobrepesos_tecnologia VALUES (?, ?)', (tech_name, pct_val))

            # 2. Sheet Control Pesos (Sample measurements)
            ctrl_sheet_name = 'Control Pesos' if 'Control Pesos' in wb.sheetnames else wb.sheetnames[0]
            ws_ctrl = wb[ctrl_sheet_name]
            rows_iter = ws_ctrl.iter_rows(values_only=True)

            # Skip header/blank rows until header row is reached
            for r in rows_iter:
                if r and len(r) > 1:
                    r0_str = str(r[0]).strip().upper() if r[0] is not None else ''
                    r1_str = str(r[1]).strip().upper() if r[1] is not None else ''
                    if r0_str == 'FECHA' or r1_str == 'SEMANA':
                        break

            cur.execute('DROP TABLE IF EXISTS muestreos')
            t_cols_sql = ', '.join([f't{i} REAL' for i in range(1, 49)])
            cur.execute(f'''
                CREATE TABLE muestreos (
                    id_control TEXT PRIMARY KEY,
                    fecha TEXT,
                    semana INTEGER,
                    turno TEXT,
                    linea TEXT,
                    control_linea TEXT,
                    viaje TEXT,
                    formato TEXT,
                    tara REAL,
                    peso_nominal REAL,
                    et TEXT,
                    variedad TEXT,
                    deshidratacion REAL,
                    tipo_tecnologia TEXT,
                    cliente TEXT,
                    tipo_envio TEXT,
                    peso_minimo REAL,
                    peso_maximo REAL,
                    hora TEXT,
                    {t_cols_sql},
                    promedio_pesos REAL,
                    sobrepeso REAL,
                    observacion TEXT
                )
            ''')

            insert_sql = f'''
                INSERT INTO muestreos VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    {', '.join(['?' for _ in range(48)])},
                    ?, ?, ?
                )
            '''

            batch = []
            for idx, r in enumerate(rows_iter):
                if not any(r):
                    continue
                # Ignore duplicate headers or non-numeric week
                if r[1] is not None and not str(r[1]).strip().replace('.', '', 1).isdigit():
                    continue

                id_ctrl = f'ctrl_{idx+1}'
                f = r[0].strftime('%Y-%m-%d') if hasattr(r[0], 'strftime') else (str(r[0])[:10] if r[0] else None)
                try:
                    sem = int(float(r[1])) if r[1] is not None else None
                except (ValueError, TypeError):
                    continue

                turno = str(r[2]) if r[2] is not None else None
                linea = str(r[3]) if r[3] is not None else None
                ctrl_linea = str(r[4]) if r[4] is not None else None
                viaje = str(r[5]) if r[5] is not None else None
                formato = str(r[6]) if r[6] is not None else None
                tara = float(r[7]) if (r[7] is not None and not isinstance(r[7], str)) else None
                nom = float(r[8]) if (r[8] is not None and not isinstance(r[8], str)) else None
                et = str(r[9]) if r[9] is not None else None
                variedad = str(r[10]) if r[10] is not None else None
                desh = float(r[11]) if (r[11] is not None and not isinstance(r[11], str)) else None
                tech = str(r[12]).strip() if r[12] is not None else None
                cliente = str(r[13]) if r[13] is not None else None
                tipo_envio = str(r[14]) if r[14] is not None else None
                p_min = float(r[15]) if (r[15] is not None and not isinstance(r[15], str)) else None
                p_max = float(r[16]) if (r[16] is not None and not isinstance(r[16], str)) else None

                # Recover nominal weight if missing/0 using max weight and dehydration
                if (nom is None or nom == 0) and p_max and p_max > 0:
                    d_val = desh if desh else 0.048
                    nom = round(p_max / (1.0 + d_val), 0)

                hora = None
                t_vals = []
                for i in range(17, 65):
                    val = r[i]
                    t_vals.append(float(val) if (val is not None and not isinstance(val, str)) else None)

                prom = float(r[65]) if (r[65] is not None and not isinstance(r[65], str)) else None

                # Calculate or clean sobrepeso
                sp = r[66] if len(r) > 66 else None
                if isinstance(sp, (int, float)):
                    sp_val = float(sp)
                elif nom and nom > 0 and prom:
                    sp_val = (prom - nom) / nom
                else:
                    sp_val = None

                obs = None
                row_tuple = [id_ctrl, f, sem, turno, linea, ctrl_linea, viaje, formato, tara, nom, et, variedad, desh, tech, cliente, tipo_envio, p_min, p_max, hora] + t_vals + [prom, sp_val, obs]
                batch.append(row_tuple)

            cur.executemany(insert_sql, batch)

            for col in ['fecha', 'semana', 'turno', 'linea', 'viaje', 'formato', 'variedad', 'tipo_tecnologia', 'cliente']:
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{col} ON muestreos({col})')

            # 3. Sheet PRODUCCION (Total fruit production and kilograms per technology)
            if 'PRODUCCION' in wb.sheetnames:
                ws_prod = wb['PRODUCCION']
                cur.execute('DROP TABLE IF EXISTS produccion')
                cur.execute('''
                    CREATE TABLE produccion (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        centro TEXT,
                        almacen TEXT,
                        material TEXT,
                        texto_material TEXT,
                        unidad TEXT,
                        cantidad REAL,
                        fecha_entrada TEXT,
                        clase_mov TEXT,
                        lote TEXT,
                        fecha_contab TEXT,
                        documento_material TEXT,
                        viaje TEXT,
                        peso_caja REAL,
                        kilos REAL,
                        tecnologia TEXT
                    )
                ''')
                prod_iter = ws_prod.iter_rows(values_only=True)
                for r in prod_iter:
                    if r and len(r) > 27:
                        r27_str = str(r[27]).strip().upper() if r[27] is not None else ''
                        r28_str = str(r[28]).strip().upper() if len(r) > 28 and r[28] is not None else ''
                        if r27_str == 'PESO' or r28_str.startswith('TEC'):
                            break

                prod_batch = []
                for r in prod_iter:
                    if not any(r):
                        continue
                    centro = str(r[0]) if r[0] is not None else None
                    almacen = str(r[1]) if r[1] is not None else None
                    material = str(r[2]) if r[2] is not None else None
                    texto_mat = str(r[3]) if r[3] is not None else None
                    unidad = str(r[4]) if r[4] is not None else None
                    cant = float(r[5]) if (r[5] is not None and not isinstance(r[5], str)) else None
                    f_ent = r[6].strftime('%Y-%m-%d') if hasattr(r[6], 'strftime') else (str(r[6])[:10] if r[6] else None)
                    clase_mov = str(r[7]) if r[7] is not None else None
                    lote = str(r[9]) if r[9] is not None else None
                    f_con = r[10].strftime('%Y-%m-%d') if hasattr(r[10], 'strftime') else (str(r[10])[:10] if r[10] else None)
                    doc_mat = str(r[12]) if r[12] is not None else None
                    viaje = str(r[24]).strip() if (len(r) > 24 and r[24] is not None) else None
                    peso_caja = float(r[26]) if (len(r) > 26 and r[26] is not None and not isinstance(r[26], str)) else None
                    kilos = float(r[27]) if (len(r) > 27 and r[27] is not None and not isinstance(r[27], str)) else 0.0
                    tech = str(r[28]).strip() if (len(r) > 28 and r[28] is not None) else 'Sin Tecnología'

                    prod_batch.append((centro, almacen, material, texto_mat, unidad, cant, f_ent, clase_mov, lote, f_con, doc_mat, viaje, peso_caja, kilos, tech))

                cur.executemany('''
                    INSERT INTO produccion (
                        centro, almacen, material, texto_material, unidad, cantidad,
                        fecha_entrada, clase_mov, lote, fecha_contab, documento_material,
                        viaje, peso_caja, kilos, tecnologia
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', prod_batch)

                cur.execute('CREATE INDEX IF NOT EXISTS idx_prod_fecha ON produccion(fecha_contab)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_prod_viaje ON produccion(viaje)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_prod_tech ON produccion(tecnologia)')

            conn.commit()
            conn.close()
            print("Database sync complete.")
        except Exception as err:
            print(f"Notice: Excel sync encountered an issue ({err}). Using existing database without interruption.")
            try:
                os.utime(DB_PATH, None)
            except Exception:
                pass

def init_users_table(conn=None):
    """Ensure the usuarios table exists and has a default administrator user."""
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        should_close = True

    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT,
            rol TEXT DEFAULT 'analista',
            activo INTEGER DEFAULT 1,
            creado_el TEXT
        )
    ''')

    # Seed default admin user if table is empty
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        import datetime
        from werkzeug.security import generate_password_hash
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pwd_hash = generate_password_hash('camposol2026')
        cur.execute('''
            INSERT INTO usuarios (usuario, password, nombre, rol, activo, creado_el)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', ('admin', pwd_hash, 'Administrador Calidad', 'admin', now_str))
        conn.commit()
        print("Default user 'admin' created in table 'usuarios'.")

    if should_close:
        conn.close()

def verify_user_credentials(username, password):
    """
    Verify user login credentials.
    Supports both hashed passwords and plain text passwords (in case the user manually
    edits the SQL table and inserts plain text passwords).
    Returns (success: bool, user_dict_or_error: dict/str).
    """
    if not username or not password:
        return False, "Por favor, ingresa tu usuario y contraseña."

    init_users_table()
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = LOWER(?)", (username.strip(),))
    user = cur.fetchone()

    if not user:
        conn.close()
        return False, "Usuario o contraseña incorrectos."

    if not user["activo"]:
        conn.close()
        return False, "Este usuario se encuentra inactivo. Contacta al administrador."

    stored_pwd = str(user["password"])
    is_valid = False

    # Check if hashed password
    if stored_pwd.startswith(('pbkdf2:', 'scrypt:', 'argon2:')):
        from werkzeug.security import check_password_hash
        is_valid = check_password_hash(stored_pwd, password)
    else:
        # Plain text match for direct SQL table edits
        if stored_pwd == password:
            is_valid = True
            try:
                from werkzeug.security import generate_password_hash
                new_hash = generate_password_hash(password)
                cur.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_hash, user["id"]))
                conn.commit()
            except Exception:
                pass

    if is_valid:
        user_dict = {
            "id": user["id"],
            "usuario": user["usuario"],
            "nombre": user["nombre"] or user["usuario"],
            "rol": user["rol"] or "analista"
        }
        conn.close()
        return True, user_dict

    conn.close()
    return False, "Usuario o contraseña incorrectos."

def create_or_update_user(usuario, password, nombre, rol='analista', activo=1):
    """
    Creates or updates a user in the SQL 'usuarios' table.
    """
    init_users_table()
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cur = conn.cursor()
    import datetime
    from werkzeug.security import generate_password_hash
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pwd_hash = generate_password_hash(password)
    cur.execute('''
        INSERT INTO usuarios (usuario, password, nombre, rol, activo, creado_el)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario) DO UPDATE SET
            password = excluded.password,
            nombre = excluded.nombre,
            rol = excluded.rol,
            activo = excluded.activo
    ''', (usuario.strip(), pwd_hash, nombre.strip(), rol, activo, now_str))
    conn.commit()
    conn.close()
    return True

def get_connection():
    sync_database_if_needed()
    init_users_table()
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def get_filters():
    """Retrieve distinct values and ranges for the 8 filters."""
    conn = get_connection()
    cur = conn.cursor()

    # Date range
    cur.execute("SELECT MIN(fecha), MAX(fecha) FROM muestreos WHERE fecha IS NOT NULL")
    min_date, max_date = cur.fetchone()

    # Distinct Turnos
    cur.execute("SELECT DISTINCT turno FROM muestreos WHERE turno IS NOT NULL ORDER BY turno")
    turnos = [row[0] for row in cur.fetchall()]

    # Distinct Lineas
    cur.execute("SELECT DISTINCT linea FROM muestreos WHERE linea IS NOT NULL AND linea != '' ORDER BY linea")
    lineas = [row[0] for row in cur.fetchall()]

    # Distinct Formatos
    cur.execute("SELECT DISTINCT formato FROM muestreos WHERE formato IS NOT NULL AND formato != '' ORDER BY formato")
    formatos = [row[0] for row in cur.fetchall()]

    # Distinct Variedades
    cur.execute("SELECT DISTINCT variedad FROM muestreos WHERE variedad IS NOT NULL AND variedad != '' ORDER BY variedad")
    variedades = [row[0] for row in cur.fetchall()]

    # Distinct Tipo Tecnologia
    cur.execute("SELECT DISTINCT tipo_tecnologia FROM muestreos WHERE tipo_tecnologia IS NOT NULL AND tipo_tecnologia != '' ORDER BY tipo_tecnologia")
    tecnologias = [row[0] for row in cur.fetchall()]

    # Top Clientes
    cur.execute("SELECT DISTINCT cliente FROM muestreos WHERE cliente IS NOT NULL AND cliente != '' ORDER BY cliente")
    clientes = [row[0] for row in cur.fetchall()]

    # Top Viajes (sample recent or most frequent)
    cur.execute("SELECT DISTINCT viaje FROM muestreos WHERE viaje IS NOT NULL AND viaje != '' ORDER BY viaje DESC LIMIT 100")
    viajes = [row[0] for row in cur.fetchall()]

    conn.close()
    return {
        "date_range": {"min": min_date, "max": max_date},
        "turnos": turnos,
        "lineas": lineas,
        "formatos": formatos,
        "variedades": variedades,
        "tecnologias": tecnologias,
        "clientes": clientes,
        "viajes": viajes
    }

def build_where_clause(filters, prefix=""):
    """Build SQL WHERE clause and parameters from filter dictionary."""
    conditions = []
    params = []
    p = prefix

    if filters.get("fecha_desde"):
        conditions.append(f"{p}fecha >= ?")
        params.append(filters["fecha_desde"])
    if filters.get("fecha_hasta"):
        conditions.append(f"{p}fecha <= ?")
        params.append(filters["fecha_hasta"])
    if filters.get("turno"):
        conditions.append(f"{p}turno = ?")
        params.append(int(filters["turno"]))
    if filters.get("linea"):
        conditions.append(f"{p}linea = ?")
        params.append(filters["linea"])
    if filters.get("viaje"):
        conditions.append(f"{p}viaje = ?")
        params.append(str(filters["viaje"]))
    if filters.get("formato"):
        conditions.append(f"{p}formato = ?")
        params.append(filters["formato"])
    if filters.get("variedad"):
        conditions.append(f"{p}variedad = ?")
        params.append(filters["variedad"])
    if filters.get("tipo_tecnologia"):
        conditions.append(f"{p}tipo_tecnologia = ?")
        params.append(filters["tipo_tecnologia"])
    if filters.get("cliente"):
        conditions.append(f"{p}cliente = ?")
        params.append(filters["cliente"])

    where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_sql, params

def get_kpis_and_summary(filters):
    """Calculate executive KPIs, process capability Cp/Cpk, giveaway, and compliance rates."""
    conn = get_connection()
    where_sql, params = build_where_clause(filters)

    # Fetch rows to compute sample stats
    query = f"""
        SELECT id_control, fecha, hora, turno, linea, formato, variedad, cliente, 
               peso_nominal, peso_minimo, peso_maximo, promedio_pesos,
               {', '.join(T_COLS)}
        FROM muestreos {where_sql}
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    total_muestreos = len(df)
    if total_muestreos == 0:
        return {
            "total_muestreos": 0,
            "total_clamshells": 0,
            "peso_promedio": 0,
            "desv_estandar": 0,
            "peso_min_promedio": 0,
            "peso_max_promedio": 0,
            "pct_en_rango": 0,
            "pct_bajo_peso": 0,
            "pct_sobrepeso": 0,
            "giveaway_total_g": 0,
            "giveaway_promedio_g": 0,
            "cp": 0,
            "cpk": 0,
            "cpk_status": "Sin datos"
        }

    # Extract all measured weights
    t_data = df[T_COLS].values
    min_arr = df['peso_minimo'].values[:, np.newaxis]
    max_arr = df['peso_maximo'].values[:, np.newaxis]
    nom_arr = df['peso_nominal'].values[:, np.newaxis]

    valid_mask = ~np.isnan(t_data) & (t_data > 0)
    total_clamshells = int(np.sum(valid_mask))

    weights = t_data[valid_mask]
    if len(weights) == 0:
        return {
            "total_muestreos": total_muestreos,
            "total_clamshells": 0,
            "peso_promedio": 0,
            "desv_estandar": 0,
            "pct_en_rango": 0,
            "pct_bajo_peso": 0,
            "pct_sobrepeso": 0,
            "giveaway_total_g": 0,
            "giveaway_promedio_g": 0,
            "cp": 0,
            "cpk": 0,
            "cpk_status": "Sin datos"
        }

    mean_weight = float(np.mean(weights))
    std_weight = float(np.std(weights, ddof=1)) if len(weights) > 1 else 0.0

    # Repeat min/max arrays to match valid_mask
    min_matrix = np.repeat(min_arr, 48, axis=1)
    max_matrix = np.repeat(max_arr, 48, axis=1)
    nom_matrix = np.repeat(nom_arr, 48, axis=1)

    valid_mins = min_matrix[valid_mask]
    valid_maxs = max_matrix[valid_mask]
    valid_noms = nom_matrix[valid_mask]

    # Classification:
    # Underweight: valid_mins > 0 and weight < valid_mins
    under_mask = (valid_mins > 0) & (weights < valid_mins)
    # Overweight: weight > valid_maxs
    over_mask = (weights > valid_maxs)
    # In range: otherwise
    in_range_mask = ~under_mask & ~over_mask

    count_under = int(np.sum(under_mask))
    count_over = int(np.sum(over_mask))
    count_in_range = int(np.sum(in_range_mask))

    pct_under = round((count_under / total_clamshells) * 100, 2)
    pct_over = round((count_over / total_clamshells) * 100, 2)
    pct_in = round((count_in_range / total_clamshells) * 100, 2)

    # Giveaway: excess grams above target/max_weight
    # If nominal is present, giveaway is weight - nominal when weight > nominal
    # or excess over max weight
    excess_grams = np.maximum(0, weights - valid_maxs)
    total_giveaway_g = float(np.sum(excess_grams))
    avg_giveaway_g = float(np.mean(excess_grams))

    # Cp and Cpk calculation
    # Average LSL and USL
    valid_lsl_candidates = valid_mins[valid_mins > 0]
    avg_lsl = float(np.median(valid_lsl_candidates)) if len(valid_lsl_candidates) > 0 else 0.0
    avg_usl = float(np.median(valid_maxs)) if len(valid_maxs) > 0 else 0.0

    cp = 0.0
    cpk = 0.0
    cpk_status = "Incapaz"
    if std_weight > 0 and avg_usl > avg_lsl and avg_lsl > 0:
        cp = (avg_usl - avg_lsl) / (6 * std_weight)
        cpu = (avg_usl - mean_weight) / (3 * std_weight)
        cpl = (mean_weight - avg_lsl) / (3 * std_weight)
        cpk = min(cpu, cpl)
        if cpk >= 1.33:
            cpk_status = "Excelente (Capaz)"
        elif cpk >= 1.0:
            cpk_status = "Aceptable"
        elif cpk >= 0.67:
            cpk_status = "Bajo control marginal"
        else:
            cpk_status = "Incapaz (Alta dispersión)"
    elif std_weight > 0 and avg_usl > 0:
        # Only USL defined
        cpu = (avg_usl - mean_weight) / (3 * std_weight)
        cpk = max(0, cpu)
        cpk_status = "Aceptable (Límite superior)" if cpk >= 1.0 else "Incapaz"

    return {
        "total_muestreos": total_muestreos,
        "total_clamshells": total_clamshells,
        "peso_promedio": round(mean_weight, 2),
        "desv_estandar": round(std_weight, 2),
        "peso_min_promedio": round(avg_lsl, 1),
        "peso_max_promedio": round(avg_usl, 1),
        "pct_en_rango": pct_in,
        "pct_bajo_peso": pct_under,
        "pct_sobrepeso": pct_over,
        "count_en_rango": count_in_range,
        "count_bajo_peso": count_under,
        "count_sobrepeso": count_over,
        "giveaway_total_g": round(total_giveaway_g, 1),
        "giveaway_promedio_g": round(avg_giveaway_g, 2),
        "cp": round(max(0, cp), 2),
        "cpk": round(max(-2, cpk), 2),
        "cpk_status": cpk_status
    }

def get_scatter_data(filters, max_points=4000):
    """
    Retrieve individual clamshell weights for dispersion plot.
    Points include: [x_index, weight, status, sample_id, date, line, format, min_val, max_val, t_num]
    Limits (LSL, USL, Target) returned as threshold reference lines.
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters)

    query = f"""
        SELECT id_control, fecha, hora, turno, linea, formato, variedad,
               peso_nominal, peso_minimo, peso_maximo, promedio_pesos,
               {', '.join(T_COLS)}
        FROM muestreos {where_sql}
        ORDER BY fecha ASC, hora ASC
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if len(df) == 0:
        return {"points": [], "lsl": 0, "usl": 0, "nominal": 0, "total_points": 0}

    # If dataset has many rows, sample proportionally to stay within max_points
    n_rows = len(df)
    stride = max(1, int((n_rows * 48) / max_points))

    points = []
    pt_idx = 0

    median_min = float(df['peso_minimo'][df['peso_minimo'] > 0].median()) if (df['peso_minimo'] > 0).any() else 0.0
    median_max = float(df['peso_maximo'].median()) if not df['peso_maximo'].empty else 0.0
    median_nom = float(df['peso_nominal'].dropna().median()) if not df['peso_nominal'].dropna().empty else 0.0

    raw_counter = 0
    for row_idx, row in df.iterrows():
        p_min = row['peso_minimo']
        p_max = row['peso_maximo']
        f_date = str(row['fecha'])
        f_time = str(row['hora']) if row['hora'] else ''
        f_line = str(row['linea'])
        f_fmt = str(row['formato'])
        ctrl_id = str(row['id_control'])

        for t_idx, t_col in enumerate(T_COLS, 1):
            val = row[t_col]
            if pd.isna(val) or val <= 0:
                continue
            
            raw_counter += 1
            if stride > 1 and (raw_counter % stride != 0):
                continue

            pt_idx += 1
            status = 'in_spec'
            if p_min > 0 and val < p_min:
                status = 'underweight'
            elif val > p_max:
                status = 'overweight'

            points.append({
                "x": pt_idx,
                "y": float(val),
                "status": status,
                "date": f"{f_date} {f_time}".strip(),
                "line": f_line,
                "format": f_fmt,
                "id": ctrl_id,
                "t": f"T{t_idx}",
                "min": float(p_min),
                "max": float(p_max)
            })

    return {
        "points": points,
        "total_points": raw_counter,
        "lsl": median_min,
        "usl": median_max,
        "nominal": median_nom
    }

def get_distribution_data(filters, num_bins=35):
    """
    Generate histogram and fitted Gaussian curve for clamshell weights.
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters)

    query = f"""
        SELECT peso_minimo, peso_maximo, {', '.join(T_COLS)}
        FROM muestreos {where_sql}
        ORDER BY id_control DESC LIMIT 4000
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if len(df) == 0:
        return {"bins": [], "counts": [], "normal_curve": [], "mu": 0, "sigma": 0, "lsl": 0, "usl": 0}

    # If dataset has many rows, sample up to 4000 rows (up to 192,000 clamshells) for ultra-fast response
    if len(df) > 4000:
        df = df.sample(4000, random_state=42)

    t_data = df[T_COLS].values
    valid_weights = t_data[~np.isnan(t_data) & (t_data > 0)]

    if len(valid_weights) < 5:
        return {"bins": [], "counts": [], "normal_curve": [], "mu": 0, "sigma": 0, "lsl": 0, "usl": 0}

    # Filter out extreme outliers for clean plotting (1st to 99th percentile or 3 IQR)
    q1 = np.percentile(valid_weights, 1)
    q99 = np.percentile(valid_weights, 99)
    plot_weights = valid_weights[(valid_weights >= q1) & (valid_weights <= q99)]

    counts, bin_edges = np.histogram(plot_weights, bins=num_bins)
    bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]

    mu = float(np.mean(valid_weights))
    sigma = float(np.std(valid_weights, ddof=1))

    # Fitted normal PDF
    normal_curve = []
    if sigma > 0:
        bin_width = bin_edges[1] - bin_edges[0]
        total_count = len(plot_weights)
        for x in bin_centers:
            pdf_val = stats.norm.pdf(x, mu, sigma)
            # Scale to histogram frequency
            freq_val = pdf_val * total_count * bin_width
            normal_curve.append(round(float(freq_val), 1))

    median_min = float(df['peso_minimo'][df['peso_minimo'] > 0].median()) if (df['peso_minimo'] > 0).any() else 0.0
    median_max = float(df['peso_maximo'].median()) if not df['peso_maximo'].empty else 0.0

    return {
        "bins": [round(float(b), 1) for b in bin_centers],
        "counts": [int(c) for c in counts],
        "normal_curve": normal_curve,
        "mu": round(mu, 2),
        "sigma": round(sigma, 2),
        "lsl": round(median_min, 1),
        "usl": round(median_max, 1)
    }

def get_control_chart_data(filters, max_samples=150):
    """
    X-bar Control Chart: sample averages with Grand Mean and UCL/LCL control limits.
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters)

    query = f"""
        SELECT id_control, fecha, hora, linea, formato, promedio_pesos, peso_minimo, peso_maximo
        FROM muestreos {where_sql} AND promedio_pesos IS NOT NULL AND promedio_pesos > 0
        ORDER BY fecha ASC, hora ASC
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if len(df) == 0:
        return {"samples": [], "grand_mean": 0, "ucl": 0, "lcl": 0}

    n_samples = len(df)
    if n_samples > max_samples:
        step = int(np.ceil(n_samples / max_samples))
        df = df.iloc[::step].copy()

    means = df['promedio_pesos'].values
    grand_mean = float(np.mean(means))
    sample_std = float(np.std(means, ddof=1)) if len(means) > 1 else 0.0

    # 3-sigma control limits
    ucl = grand_mean + 3 * sample_std
    lcl = max(0, grand_mean - 3 * sample_std)

    samples = []
    for idx, row in df.iterrows():
        mean_val = float(row['promedio_pesos'])
        samples.append({
            "label": f"{row['fecha']} {row['linea']}",
            "mean": round(mean_val, 2),
            "date": str(row['fecha']),
            "line": str(row['linea']),
            "format": str(row['formato']),
            "out_of_control": bool(mean_val > ucl or mean_val < lcl)
        })

    return {
        "samples": samples,
        "grand_mean": round(grand_mean, 2),
        "ucl": round(ucl, 2),
        "lcl": round(lcl, 2)
    }

def get_lines_comparison(filters):
    """
    Compare packaging lines: box plot stats (Min, Q1, Median, Q3, Max) and % compliance.
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters)

    query = f"""
        SELECT linea, peso_minimo, peso_maximo, {', '.join(T_COLS)}
        FROM muestreos {where_sql}
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if len(df) == 0:
        return {"lines": [], "boxplot_data": [], "compliance": []}

    grouped = df.groupby('linea')
    lines = []
    boxplot_data = []
    compliance = []

    for line_name, group in grouped:
        t_vals = group[T_COLS].values
        valid_w = t_vals[~np.isnan(t_vals) & (t_vals > 0)]
        if len(valid_w) < 10:
            continue

        q1 = float(np.percentile(valid_w, 25))
        median = float(np.median(valid_w))
        q3 = float(np.percentile(valid_w, 75))
        iqr = q3 - q1
        low_whisker = float(max(np.min(valid_w), q1 - 1.5 * iqr))
        high_whisker = float(min(np.max(valid_w), q3 + 1.5 * iqr))

        lines.append(str(line_name))
        boxplot_data.append([
            round(low_whisker, 1),
            round(q1, 1),
            round(median, 1),
            round(q3, 1),
            round(high_whisker, 1)
        ])

        # Compliance per line
        min_arr = group['peso_minimo'].values[:, np.newaxis]
        max_arr = group['peso_maximo'].values[:, np.newaxis]
        min_matrix = np.repeat(min_arr, 48, axis=1)
        max_matrix = np.repeat(max_arr, 48, axis=1)

        mask = ~np.isnan(t_vals) & (t_vals > 0)
        w_line = t_vals[mask]
        min_line = min_matrix[mask]
        max_line = max_matrix[mask]

        total = len(w_line)
        under = int(np.sum((min_line > 0) & (w_line < min_line)))
        over = int(np.sum(w_line > max_line))
        in_spec = total - under - over

        compliance.append({
            "line": str(line_name),
            "pct_in": round((in_spec / total) * 100, 1) if total > 0 else 0,
            "pct_under": round((under / total) * 100, 1) if total > 0 else 0,
            "pct_over": round((over / total) * 100, 1) if total > 0 else 0
        })

    return {
        "lines": lines,
        "boxplot_data": boxplot_data,
        "compliance": compliance
    }

def get_available_technologies(filters=None):
    """
    Retrieve distinct technologies available for the active filters
    with their theoretical overweight percentages and sample counts.
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters, prefix="m.")
    extra_filter = "m.tipo_tecnologia IS NOT NULL AND m.tipo_tecnologia != ''"
    if where_sql:
        where_sql += f" AND {extra_filter}"
    else:
        where_sql = f" WHERE {extra_filter}"

    query = f"""
        SELECT 
            m.tipo_tecnologia as tecnologia,
            ROUND(COALESCE(s.pct_deshidratacion * 100.0, 0.0), 2) as pct_teorico,
            COUNT(m.id_control) as n_muestreos
        FROM muestreos m
        LEFT JOIN sobrepesos_tecnologia s ON TRIM(s.tecnologia) = TRIM(m.tipo_tecnologia)
        {where_sql}
        GROUP BY m.tipo_tecnologia
        HAVING n_muestreos > 0
        ORDER BY n_muestreos DESC, m.tipo_tecnologia ASC
    """
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "tecnologia": str(r[0]),
            "pct_teorico": float(r[1]) if r[1] is not None else 0.0,
            "n_muestreos": int(r[2])
        })
    return result

def get_technology_comparison(filters):
    """
    Analyze packaging technology deviations using global sums:
    - S_venta = SUM(m.peso_nominal) -> 100.0%
    - S_min = SUM(m.peso_minimo) -> pct_minimo (e.g. 102.5%)
    - S_max = SUM(m.peso_maximo) -> pct_maximo (e.g. 103.7%)
    - S_real = SUM(m.promedio_pesos) -> pct_real (e.g. 102.0%)
    - status: 'under' (if real < min), 'over' (if real > max), 'in_range'
    - diff_pct: difference vs target range
    - signal: short human-readable status badge
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters, prefix="m.")

    extra_filter = "m.tipo_tecnologia IS NOT NULL AND m.tipo_tecnologia != ''"
    if where_sql:
        where_sql += f" AND {extra_filter}"
    else:
        where_sql = f" WHERE {extra_filter}"

    query = f"""
        SELECT 
            m.tipo_tecnologia as tecnologia,
            COUNT(*) as n_muestreos,
            ROUND(SUM(m.peso_nominal), 2) as sum_venta,
            ROUND(SUM(m.peso_minimo), 2) as sum_min,
            ROUND(SUM(m.peso_maximo), 2) as sum_max,
            ROUND(SUM(m.promedio_pesos), 2) as sum_real
        FROM muestreos m
        {where_sql}
        GROUP BY m.tipo_tecnologia
        HAVING sum_venta > 0
        ORDER BY n_muestreos DESC
    """
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()

    # Load nominal sobrepeso percentages from the SOBREPESOS sheet
    sobrepesos_map = {}
    try:
        cur.execute("SELECT TRIM(tecnologia), pct_deshidratacion FROM sobrepesos_tecnologia")
        for sr in cur.fetchall():
            sobrepesos_map[sr[0]] = float(sr[1]) if sr[1] is not None else 0.0
    except Exception:
        pass

    conn.close()

    technologies = []
    for r in rows:
        tec = str(r[0])
        n_muest = int(r[1])
        s_v = float(r[2]) if r[2] is not None else 0.0
        s_min = float(r[3]) if r[3] is not None else 0.0
        s_max = float(r[4]) if r[4] is not None else 0.0
        s_real = float(r[5]) if r[5] is not None else 0.0

        if s_v <= 0:
            continue

        # Look up nominal sobrepeso from the SOBREPESOS sheet (no extra calculations)
        pct_deshidratacion_nominal = sobrepesos_map.get(tec.strip(), 0.0)

        pct_venta = 100.0
        pct_minimo = round(100.0 + pct_deshidratacion_nominal * 100.0, 1)
        pct_maximo = round((s_max / s_v) * 100.0, 1)
        pct_real = round((s_real / s_v) * 100.0, 1)

        pct_min_raw = 100.0 + pct_deshidratacion_nominal * 100.0
        pct_max_raw = (s_max / s_v) * 100.0
        pct_real_raw = (s_real / s_v) * 100.0

        # Deviation view (relative to sales weight = 0%)
        dev_venta = 0.0
        dev_minimo = round(pct_minimo - 100.0, 1)
        dev_maximo = round(pct_maximo - 100.0, 1)
        dev_real = round(pct_real - 100.0, 1)

        if pct_real_raw < pct_min_raw - 0.01:
            status = 'under'
            diff_pct = round(pct_real - pct_minimo, 1)
            signal_text = f"Bajo Mínimo ({diff_pct:+.1f}%)"
            badge_text = f"{diff_pct:+.1f}%"
        elif pct_real_raw > pct_max_raw + 0.01:
            status = 'over'
            diff_pct = round(pct_real - pct_maximo, 1)
            signal_text = f"Sobre Máximo ({diff_pct:+.1f}%)"
            badge_text = f"{diff_pct:+.1f}%"
        else:
            status = 'in_range'
            diff_pct = 0.0
            signal_text = "En Rango Conforme"
            badge_text = "✓ OK"

        technologies.append({
            "tecnologia": tec,
            "n_muestreos": n_muest,
            "pct_venta": pct_venta,
            "pct_minimo": pct_minimo,
            "pct_maximo": pct_maximo,
            "pct_real": pct_real,
            "dev_venta": dev_venta,
            "dev_minimo": dev_minimo,
            "dev_maximo": dev_maximo,
            "dev_real": dev_real,
            "status": status,
            "diff_pct": diff_pct,
            "signal": signal_text,
            "badge": badge_text
        })

    return {
        "technologies": technologies,
        "total_technologies": len(technologies),
        "total_muestreos": sum(t["n_muestreos"] for t in technologies)
    }

def get_technology_evolution(filters, technology=None, time_unit='day'):
    """
    Analyze temporal evolution for a single selected technology using global sums:
    - S_venta = SUM(m.peso_nominal) -> 100.0%
    - S_min = SUM(m.peso_minimo) -> pct_minimo
    - S_max = SUM(m.peso_maximo) -> pct_maximo
    - S_real = SUM(m.promedio_pesos) -> pct_real
    - Aggregates by day, week, or month.
    """
    conn = get_connection()
    cur = conn.cursor()

    # If no technology specified, pick the top technology
    if not technology:
        cur.execute("SELECT tipo_tecnologia FROM muestreos WHERE tipo_tecnologia IS NOT NULL AND tipo_tecnologia != '' GROUP BY tipo_tecnologia ORDER BY COUNT(*) DESC LIMIT 1")
        top_row = cur.fetchone()
        technology = top_row[0] if top_row else "AC 0.1%"

    where_sql, params = build_where_clause(filters, prefix="m.")
    extra_filter = "TRIM(m.tipo_tecnologia) = TRIM(?) AND m.peso_nominal > 0"
    if where_sql:
        where_sql += f" AND {extra_filter}"
    else:
        where_sql = f" WHERE {extra_filter}"
    params.append(technology)

    unit = str(time_unit).lower().strip()
    if unit in ['week', 'semana']:
        unit = 'week'
        period_expr = "'Semana ' || m.semana"
        group_expr = "m.semana"
        order_expr = "m.semana ASC"
    elif unit in ['month', 'mes']:
        unit = 'month'
        period_expr = "substr(m.fecha, 1, 7)"
        group_expr = "substr(m.fecha, 1, 7)"
        order_expr = "substr(m.fecha, 1, 7) ASC"
    else:
        unit = 'day'
        period_expr = "m.fecha"
        group_expr = "m.fecha"
        order_expr = "m.fecha ASC"

    # Compute technology-wide global min and max percentages across the entire filtered period
    cur.execute(f"""
        SELECT 
            ROUND(SUM(m.peso_nominal), 2) as s_v,
            ROUND(SUM(m.peso_minimo), 2) as s_min,
            ROUND(SUM(m.peso_maximo), 2) as s_max,
            ROUND(SUM(m.promedio_pesos), 2) as s_real
        FROM muestreos m
        {where_sql}
    """, params)
    overall_row = cur.fetchone()
    if overall_row and overall_row[0] and overall_row[0] > 0:
        overall_v = float(overall_row[0])
        overall_min = float(overall_row[1]) if overall_row[1] else 0.0
        overall_max = float(overall_row[2]) if overall_row[2] else 0.0
        overall_real = float(overall_row[3]) if overall_row[3] else 0.0
        global_pct_min = round((overall_min / overall_v) * 100.0, 1)
        global_pct_max = round((overall_max / overall_v) * 100.0, 1)
        global_pct_real = round((overall_real / overall_v) * 100.0, 1)
    else:
        global_pct_min = 100.0
        global_pct_max = 100.0
        global_pct_real = 100.0

    query = f"""
        SELECT 
            {period_expr} as periodo,
            COUNT(*) as n_muestreos,
            ROUND(SUM(m.peso_nominal), 2) as sum_venta,
            ROUND(SUM(m.peso_minimo), 2) as sum_min,
            ROUND(SUM(m.peso_maximo), 2) as sum_max,
            ROUND(SUM(m.promedio_pesos), 2) as sum_real
        FROM muestreos m
        {where_sql}
        GROUP BY {group_expr}
        HAVING sum_venta > 0
        ORDER BY {order_expr}
    """
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    series = []
    for r in rows:
        per = str(r[0])
        n_m = int(r[1])
        s_v = float(r[2]) if r[2] is not None else 0.0
        s_min = float(r[3]) if r[3] is not None else 0.0
        s_max = float(r[4]) if r[4] is not None else 0.0
        s_real = float(r[5]) if r[5] is not None else 0.0

        if s_v <= 0:
            continue

        pct_v = 100.0
        pct_min = round((s_min / s_v) * 100.0, 1)
        pct_max = round((s_max / s_v) * 100.0, 1)
        pct_real = round((s_real / s_v) * 100.0, 1)

        pct_min_raw = (s_min / s_v) * 100.0
        pct_max_raw = (s_max / s_v) * 100.0
        pct_real_raw = (s_real / s_v) * 100.0

        if pct_real_raw < pct_min_raw - 0.01:
            status = 'under'
            diff_pct = round(pct_real - pct_min, 1)
            signal_text = f"Bajo Mínimo ({diff_pct:+.1f}%)"
            badge_text = f"{diff_pct:+.1f}%"
        elif pct_real_raw > pct_max_raw + 0.01:
            status = 'over'
            diff_pct = round(pct_real - pct_max, 1)
            signal_text = f"Sobre Máximo ({diff_pct:+.1f}%)"
            badge_text = f"{diff_pct:+.1f}%"
        else:
            status = 'in_range'
            diff_pct = 0.0
            signal_text = "En Rango Conforme"
            badge_text = "✓ OK"

        series.append({
            "periodo": per,
            "n_muestreos": n_m,
            "pct_venta": pct_v,
            "pct_minimo": pct_min,
            "pct_maximo": pct_max,
            "pct_real": pct_real,
            "status": status,
            "diff_pct": diff_pct,
            "signal": signal_text,
            "badge": badge_text
        })

    return {
        "technology": technology,
        "time_unit": unit,
        "global_pct_minimo": global_pct_min,
        "global_pct_maximo": global_pct_max,
        "global_pct_real": global_pct_real,
        "series": series,
        "total_muestreos": sum(s["n_muestreos"] for s in series)
    }

def get_samples_table(filters, page=1, page_size=25, sort_by='fecha', sort_order='desc'):
    """
    Paginated sampling inspections with individual T1..T48 array.
    """
    conn = get_connection()
    where_sql, params = build_where_clause(filters)

    allowed_sort = {
        'fecha': 'fecha',
        'hora': 'hora',
        'turno': 'turno',
        'linea': 'linea',
        'formato': 'formato',
        'variedad': 'variedad',
        'cliente': 'cliente',
        'promedio_pesos': 'promedio_pesos'
    }
    order_col = allowed_sort.get(sort_by, 'fecha')
    order_dir = 'ASC' if sort_order.lower() == 'asc' else 'DESC'

    # Count total
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM muestreos {where_sql}", params)
    total_count = cur.fetchone()[0]

    offset = (page - 1) * page_size
    query = f"""
        SELECT id_control, fecha, hora, turno, linea, control_linea, viaje, formato, 
               variedad, tipo_tecnologia, peso_nominal, peso_minimo, peso_maximo, 
               cliente, promedio_pesos, observacion,
               {', '.join(T_COLS)}
        FROM muestreos {where_sql}
        ORDER BY {order_col} {order_dir}, hora DESC
        LIMIT ? OFFSET ?
    """
    rows = cur.execute(query, params + [page_size, offset]).fetchall()
    conn.close()

    items = []
    for r in rows:
        row_dict = dict(r)
        # Extract T weights
        weights = [row_dict[f't{i}'] for i in range(1, 49) if row_dict.get(f't{i}') is not None and not np.isnan(row_dict[f't{i}'])]
        
        # Clean dict
        for i in range(1, 49):
            row_dict.pop(f't{i}', None)
        
        p_min = row_dict.get('peso_minimo', 0) or 0
        p_max = row_dict.get('peso_maximo', 0) or 0
        
        count_under = sum(1 for w in weights if p_min > 0 and w < p_min)
        count_over = sum(1 for w in weights if w > p_max)
        count_in = len(weights) - count_under - count_over

        row_dict['weights'] = weights
        row_dict['total_tested'] = len(weights)
        row_dict['count_in'] = count_in
        row_dict['count_under'] = count_under
        row_dict['count_over'] = count_over
        row_dict['pct_compliance'] = round((count_in / len(weights)) * 100, 1) if weights else 0
        row_dict['std_dev'] = round(float(np.std(weights, ddof=1)), 2) if len(weights) > 1 else 0
        items.append(row_dict)

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_count,
        "total_pages": int(np.ceil(total_count / page_size)) if total_count > 0 else 1,
        "items": items
    }

def get_production_technology_distribution(filters=None):
    """
    Returns total kilos and percentage distribution per technology from PRODUCCION sheet.
    Dynamically links with muestreos using the 8 dashboard filters (fecha, turno, linea,
    viaje, formato, variedad, tipo_tecnologia, cliente).
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produccion'")
    if not cur.fetchone():
        conn.close()
        return {"items": [], "total_kilos": 0, "total_registros": 0}

    where_sql, params = build_where_clause(filters) if filters else ("", [])

    if where_sql:
        m_viaje_sql = f"""
            SELECT DISTINCT TRIM(viaje) 
            FROM muestreos 
            {where_sql} 
              AND viaje IS NOT NULL 
              AND TRIM(viaje) != ''
        """
        prod_conditions = [
            "p.kilos IS NOT NULL",
            f"TRIM(p.viaje) IN ({m_viaje_sql})"
        ]
        prod_params = list(params)

        if filters and filters.get("tipo_tecnologia"):
            prod_conditions.append("LOWER(p.tecnologia) = LOWER(?)")
            prod_params.append(filters["tipo_tecnologia"])

        query = f"""
            SELECT 
                p.tecnologia,
                SUM(p.kilos) as total_kg,
                COUNT(*) as reg_count
            FROM produccion p
            WHERE {' AND '.join(prod_conditions)}
            GROUP BY p.tecnologia
            ORDER BY total_kg DESC
        """
    else:
        prod_params = []
        query = """
            SELECT 
                p.tecnologia,
                SUM(p.kilos) as total_kg,
                COUNT(*) as reg_count
            FROM produccion p
            WHERE p.kilos IS NOT NULL
            GROUP BY p.tecnologia
            ORDER BY total_kg DESC
        """

    cur.execute(query, prod_params)
    rows = cur.fetchall()

    items = []
    grand_total_kg = sum(r["total_kg"] for r in rows if r["total_kg"] is not None) if rows else 0.0
    grand_total_reg = sum(r["reg_count"] for r in rows) if rows else 0

    for r in rows:
        tech = r["tecnologia"] or "Sin Tecnología"
        kg = round(float(r["total_kg"]), 2) if r["total_kg"] is not None else 0.0
        pct = round((kg / grand_total_kg * 100), 2) if grand_total_kg > 0 else 0.0
        items.append({
            "tecnologia": tech,
            "kilos": kg,
            "porcentaje": pct,
            "registros": r["reg_count"]
        })

    conn.close()
    return {
        "items": items,
        "total_kilos": round(grand_total_kg, 2),
        "total_registros": grand_total_reg
    }


