# app/modules/presupuestos.py

import io
import pandas as pd
from flask import send_file
from difflib import get_close_matches
# app/modules/presupuestos.py


from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from datetime import date
# from app import db  # Si usas SQLAlchemy
# from app.supabase import supabase  # Si usas Supabase
from app.modules.usuarios import require_modulo

bp_presupuestos = Blueprint("presupuestos", __name__, url_prefix="/presupuestos")

@bp_presupuestos.route("/", methods=["GET", "POST"])
@require_modulo('presupuesto')
def form_presupuesto():
    supabase = current_app.config["SUPABASE"]
    # Traer los proyectos e items ya creados (para los selects)
    proyectos = [p['proyecto'] for p in supabase.table("proyectos").select("proyecto").execute().data]
    items = [i['tipo'] for i in supabase.table("item").select("tipo").execute().data]
    trabajadores = [t['nombre'] for t in supabase.table("trabajadores").select("nombre").execute().data]

    if request.method == "POST":
        proyecto = request.form.get("proyecto")
        item = request.form.get("item")
        detalle = request.form.get("detalle")
        fecha = request.form.get("fecha")
        monto = request.form.get("monto")

        # Validaciones básicas
        if not proyecto or not item or not fecha or not monto:
            flash("Todos los campos marcados son obligatorios", "danger")
        else:
            # Guardar en la base de datos
            supabase.table("presupuesto").insert({
                "proyecto": proyecto,
                "item": item,
                "detalle": detalle,
                "fecha": fecha,
                "monto": monto
            }).execute()
            flash("Presupuesto guardado correctamente", "success")
            return redirect(url_for("presupuestos.form_presupuesto"))

    return render_template("presupuestos/form.html",
                           proyectos=proyectos,
                           items=items,
                           trabajadores=trabajadores,
                           hoy=date.today())


# Rutas para descargar plantilla e importar presupuesto

@bp_presupuestos.route("/plantilla", methods=["GET"])
@require_modulo('presupuesto')
def descargar_plantilla():
    # Crea un Excel en memoria con sólo cabeceras
    df = pd.DataFrame(columns=["proyecto", "item", "detalle", "fecha", "monto"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Plantilla")
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="plantilla_presupuesto.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@bp_presupuestos.route("/importar", methods=["POST"])
@require_modulo('presupuesto')
def importar_presupuesto():
    supabase = current_app.config["SUPABASE"]
    uploaded = request.files.get("archivo")
    if not uploaded:
        flash("No se seleccionó ningún archivo.", "danger")
        return redirect(url_for("presupuestos.form_presupuesto"))

    # Leer el Excel
    try:
        df = pd.read_excel(uploaded)
    except Exception as e:
        flash(f"Error leyendo el archivo: {e}", "danger")
        return redirect(url_for("presupuestos.form_presupuesto"))

    # Validar columnas
    expected = ["proyecto", "item", "detalle", "fecha", "monto"]
    if list(df.columns) != expected:
        flash("El archivo debe tener exactamente las columnas: " + ", ".join(expected), "danger")
        return redirect(url_for("presupuestos.form_presupuesto"))

    # Traer listas válidas
    proyectos = [p["proyecto"] for p in supabase.table("proyectos").select("proyecto").execute().data]
    items = [i["tipo"] for i in supabase.table("item").select("tipo").execute().data]

    records = []
    seen = set()

    for idx, row in df.iterrows():
        fila = idx + 2  # correspondencia de fila Excel
        pr = row["proyecto"]
        it = row["item"]
        detalle = row["detalle"]
        fecha = row["fecha"]
        monto = row["monto"]

        # Match proyecto
        match_pr = get_close_matches(pr, proyectos, n=1, cutoff=0.6)
        if not match_pr:
            flash(f"Proyecto no encontrado en fila {fila}: {pr}", "danger")
            return redirect(url_for("presupuestos.form_presupuesto"))
        pr = match_pr[0]

        # Match item
        match_it = get_close_matches(it, items, n=1, cutoff=0.6)
        if not match_it:
            flash(f"Item no encontrado en fila {fila}: {it}", "danger")
            return redirect(url_for("presupuestos.form_presupuesto"))
        it = match_it[0]

        # Validar fecha y monto
        if pd.isna(fecha):
            flash(f"Fecha inválida en fila {fila}.", "danger")
            return redirect(url_for("presupuestos.form_presupuesto"))
        if not isinstance(monto, (int, float)) or monto <= 0:
            flash(f"Monto inválido en fila {fila}: {monto}", "danger")
            return redirect(url_for("presupuestos.form_presupuesto"))

        key = (pr, it, detalle, fecha, monto)
        if key in seen:
            flash(f"Línea duplicada en fila {fila}.", "danger")
            return redirect(url_for("presupuestos.form_presupuesto"))
        seen.add(key)

        records.append({
            "proyecto": pr,
            "item": it,
            "detalle": detalle,
            "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
            "monto": int(monto)
        })

    # Insertar todo
    supabase.table("presupuesto").insert(records).execute()
    flash(f"Importación exitosa: {len(records)} registros guardados.", "success")
    return redirect(url_for("presupuestos.form_presupuesto"))