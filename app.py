import os
import io
import csv
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for, flash
import data_engine

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.environ.get("SECRET_KEY", "camposol_control_pesos_session_secret_2026")

@app.before_request
def check_authentication():
    public_endpoints = {"login", "static"}
    if request.endpoint and request.endpoint in public_endpoints:
        return

    if request.path.startswith("/static/"):
        return

    if "user" not in session:
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": "Sesión expirada o no autenticado"}), 401
        return redirect(url_for("login", next=request.path))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("index"))

    error_msg = None
    next_page = request.args.get("next") or request.form.get("next") or url_for("index")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        success, res = data_engine.verify_user_credentials(username, password)
        if success:
            session["user"] = res
            return redirect(next_page)
        else:
            error_msg = res

    return render_template("login.html", error=error_msg, next=next_page)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

def extract_filters():
    return {
        "fecha_desde": request.args.get("fecha_desde", "").strip() or None,
        "fecha_hasta": request.args.get("fecha_hasta", "").strip() or None,
        "turno": request.args.get("turno", "").strip() or None,
        "linea": request.args.get("linea", "").strip() or None,
        "viaje": request.args.get("viaje", "").strip() or None,
        "formato": request.args.get("formato", "").strip() or None,
        "variedad": request.args.get("variedad", "").strip() or None,
        "tipo_tecnologia": request.args.get("tipo_tecnologia", "").strip() or None,
        "cliente": request.args.get("cliente", "").strip() or None
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/filters")
def get_filters():
    try:
        data = data_engine.get_filters()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/kpis")
def get_kpis():
    try:
        filters = extract_filters()
        data = data_engine.get_kpis_and_summary(filters)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/scatter")
def get_scatter():
    try:
        filters = extract_filters()
        max_pts = int(request.args.get("max_points", 3500))
        data = data_engine.get_scatter_data(filters, max_points=max_pts)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/distribution")
def get_distribution():
    try:
        filters = extract_filters()
        num_bins = int(request.args.get("bins", 35))
        data = data_engine.get_distribution_data(filters, num_bins=num_bins)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/control_chart")
def get_control_chart():
    try:
        filters = extract_filters()
        max_samples = int(request.args.get("max_samples", 120))
        data = data_engine.get_control_chart_data(filters, max_samples=max_samples)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/lines_comparison")
def get_lines_comparison():
    try:
        filters = extract_filters()
        data = data_engine.get_lines_comparison(filters)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/technology_comparison")
def get_technology_comparison():
    try:
        filters = extract_filters()
        data = data_engine.get_technology_comparison(filters)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/technologies")
def get_technologies():
    try:
        filters = extract_filters()
        data = data_engine.get_available_technologies(filters)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/technology_evolution")
def get_technology_evolution():
    try:
        filters = extract_filters()
        technology = request.args.get("technology", "").strip() or None
        time_unit = request.args.get("time_unit", "day").strip().lower()
        data = data_engine.get_technology_evolution(filters, technology=technology, time_unit=time_unit)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/production_technology")
def get_production_technology():
    try:
        filters = extract_filters()
        data = data_engine.get_production_technology_distribution(filters)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/samples")
def get_samples():
    try:
        filters = extract_filters()
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        sort_by = request.args.get("sort_by", "fecha")
        sort_order = request.args.get("sort_order", "desc")
        data = data_engine.get_samples_table(filters, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/export")
def export_csv():
    try:
        filters = extract_filters()
        # Fetch up to 10000 rows for export
        conn = data_engine.get_connection()
        where_sql, params = data_engine.build_where_clause(filters)
        query = f"""
            SELECT id_control, fecha, hora, turno, linea, control_linea, viaje, formato, 
                   variedad, tipo_tecnologia, peso_nominal, peso_minimo, peso_maximo, 
                   cliente, promedio_pesos, observacion
            FROM muestreos {where_sql}
            ORDER BY fecha DESC, hora DESC
            LIMIT 10000
        """
        cur = conn.cursor()
        rows = cur.execute(query, params).fetchall()
        col_names = [description[0] for description in cur.description]
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(col_names)
        for r in rows:
            writer.writerow(list(r))

        output.seek(0)
        return Response(
            output.getvalue().encode('utf-8-sig'),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=muestreos_filtrados.csv"}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    data_engine.sync_database_if_needed()
    app.run(host="127.0.0.1", port=5000, debug=False)
