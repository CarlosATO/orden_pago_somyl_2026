# app/modules/presupuestos.py

import io
import pandas as pd
from flask import send_file, jsonify
from difflib import get_close_matches
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from datetime import date, datetime
from app.modules.usuarios import require_modulo
from app.utils.static_data import get_cached_proyectos, get_cached_items, get_cached_trabajadores

bp_presupuestos = Blueprint("presupuestos", __name__, url_prefix="/presupuestos")

@bp_presupuestos.route("/", methods=["GET", "POST"])
@require_modulo('presupuesto')
def form_presupuesto():
    supabase = current_app.config["SUPABASE"]
    
    # Usar datos cacheados para mejorar performance
    proyectos = get_cached_proyectos()
    items = get_cached_items()
    trabajadores = get_cached_trabajadores()

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
            try:
                monto_int = int(float(monto))
                if monto_int <= 0:
                    flash("El monto debe ser mayor a cero", "danger")
                else:
                    # Buscar proyecto_id
                    from app.utils.static_data import get_cached_proyectos_with_id
                    proyectos_id = get_cached_proyectos_with_id()
                    proyecto_id = None
                    for p in proyectos_id:
                        if str(p["proyecto"]).strip().lower() == str(proyecto).strip().lower():
                            proyecto_id = p["id"]
                            break
                    if proyecto_id is None:
                        flash("No se encontró el proyecto en la base de datos.", "danger")
                        return redirect(url_for("presupuestos.form_presupuesto"))

                    # Extraer mes y año
                    try:
                        fecha_dt = datetime.fromisoformat(fecha)
                    except Exception:
                        try:
                            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
                        except Exception:
                            flash("Formato de fecha inválido", "danger")
                            return redirect(url_for("presupuestos.form_presupuesto"))
                    mes_numero = fecha_dt.month
                    mes_nombre = fecha_dt.strftime("%B")  # Inglés, ej: "July"
                    anio = fecha_dt.year

                    # Guardar en la base de datos
                    supabase.table("presupuesto").insert({
                        "proyecto": proyecto,
                        "item": item,
                        "detalle": detalle,
                        "fecha": fecha,
                        "monto": monto_int,
                        "proyecto_id": proyecto_id,
                        "mes_numero": mes_numero,
                        "mes_nombre": mes_nombre,
                        "anio": anio
                    }).execute()
                    flash("Presupuesto guardado correctamente", "success")
                    return redirect(url_for("presupuestos.form_presupuesto"))
            except (ValueError, TypeError):
                flash("El monto debe ser un número válido", "danger")

    return render_template("presupuestos/form.html",
                           proyectos=proyectos,
                           items=items,
                           trabajadores=trabajadores,
                           hoy=date.today())


@bp_presupuestos.route("/gastos_proyecto", methods=["GET"])
@require_modulo('presupuesto')
def gastos_proyecto():
    """Obtiene los gastos ingresados para un proyecto específico"""
    supabase = current_app.config["SUPABASE"]
    proyecto = request.args.get("proyecto")
    
    if not proyecto:
        return jsonify({"error": "Proyecto no especificado"}), 400
    
    try:
        # Obtener todos los gastos del proyecto usando paginación manual
        page_size = 1000
        offset = 0
        gastos = []
        while True:
            batch = (
                supabase.table("presupuesto")
                .select("id, proyecto, item, detalle, fecha, monto")
                .eq("proyecto", proyecto)
                .order("fecha", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
                .data or []
            )
            gastos.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        # Calcular estadísticas
        total_amount = sum(g.get("monto", 0) for g in gastos)
        unique_items = len(set(g.get("item") for g in gastos if g.get("item")))
        last_entry = gastos[0].get("fecha") if gastos else None

        # Formatear fecha de último registro
        if last_entry:
            try:
                last_entry_date = datetime.fromisoformat(last_entry)
                last_entry = last_entry_date.strftime("%d/%m/%Y")
            except:
                last_entry = last_entry

        stats = {
            "total_entries": len(gastos),
            "total_amount": total_amount,
            "unique_items": unique_items,
            "last_entry": last_entry
        }

        return jsonify({
            "gastos": gastos,
            "stats": stats
        })

    except Exception as e:
        return jsonify({"error": "Error interno del servidor"}), 500


@bp_presupuestos.route("/actualizar_gasto", methods=["POST"])
@require_modulo('presupuesto')
def actualizar_gasto():
    """Actualiza un campo específico de un gasto"""
    supabase = current_app.config["SUPABASE"]
    data = request.get_json()
    
    gasto_id = data.get("id")
    campo = data.get("campo")
    valor = data.get("valor")
    
    if not all([gasto_id, campo, valor is not None]):
        return jsonify({"success": False, "error": "Datos incompletos"}), 400
    
    # Campos permitidos para actualizar
    campos_permitidos = ["item", "detalle", "fecha", "monto"]
    if campo not in campos_permitidos:
        return jsonify({"success": False, "error": "Campo no permitido"}), 400
    
    try:
        # Validaciones específicas por campo
        if campo == "monto":
            valor = int(float(valor))
            if valor <= 0:
                return jsonify({"success": False, "error": "El monto debe ser mayor a cero"}), 400
        elif campo == "fecha":
            # Validar formato de fecha
            datetime.strptime(valor, "%Y-%m-%d")
        elif campo == "detalle":
            valor = valor[:200]  # Limitar a 200 caracteres
        
        # Actualizar en la base de datos
        res = supabase.table("presupuesto") \
            .update({campo: valor}) \
            .eq("id", gasto_id) \
            .execute()
        
        if hasattr(res, 'error') and res.error:
            return jsonify({"success": False, "error": "Error al actualizar"}), 500
        
        return jsonify({"success": True})
        
    except ValueError as e:
        return jsonify({"success": False, "error": "Valor inválido"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": "Error interno del servidor"}), 500


@bp_presupuestos.route("/eliminar_gasto", methods=["POST"])
@require_modulo('presupuesto')
def eliminar_gasto():
    """Elimina un gasto específico"""
    supabase = current_app.config["SUPABASE"]
    data = request.get_json()
    
    gasto_id = data.get("id")
    
    if not gasto_id:
        return jsonify({"success": False, "error": "ID no especificado"}), 400
    
    try:
        # Eliminar de la base de datos
        res = supabase.table("presupuesto") \
            .delete() \
            .eq("id", gasto_id) \
            .execute()
        
        if hasattr(res, 'error') and res.error:
            return jsonify({"success": False, "error": "Error al eliminar"}), 500
        
        return jsonify({"success": True})
        
    except Exception as e:
        current_app.logger.error(f"Error eliminando gasto {gasto_id}: {e}")
        return jsonify({"success": False, "error": "Error interno del servidor"}), 500


# Rutas para descargar plantilla e importar presupuesto

@bp_presupuestos.route("/plantilla", methods=["GET"])
@require_modulo('presupuesto')
def descargar_plantilla():
    """Crea un Excel en memoria con sólo cabeceras"""
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
    """Importa presupuestos desde un archivo Excel"""
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

    # Usar datos cacheados para validación
    proyectos = get_cached_proyectos()
    items = get_cached_items()

    records = []
    seen = set()
    errores = []

    from app.utils.static_data import get_cached_proyectos_with_id
    proyectos_id = get_cached_proyectos_with_id()

    for idx, row in df.iterrows():
        fila = idx + 2  # correspondencia de fila Excel
        pr = row["proyecto"]
        it = row["item"]
        detalle = row["detalle"]
        fecha = row["fecha"]
        monto = row["monto"]

        # Validar proyecto
        match_pr = get_close_matches(str(pr), proyectos, n=1, cutoff=0.6)
        if not match_pr:
            errores.append(f"Proyecto no encontrado en fila {fila}: {pr}")
            continue
        pr = match_pr[0]

        # Buscar proyecto_id
        proyecto_id = None
        for p in proyectos_id:
            if str(p["proyecto"]).strip().lower() == str(pr).strip().lower():
                proyecto_id = p["id"]
                break
        if proyecto_id is None:
            errores.append(f"No se encontró el proyecto en la base de datos en fila {fila}: {pr}")
            continue

        # Validar item
        match_it = get_close_matches(str(it), items, n=1, cutoff=0.6)
        if not match_it:
            errores.append(f"Item no encontrado en fila {fila}: {it}")
            continue
        it = match_it[0]

        # Validar fecha
        if pd.isna(fecha):
            errores.append(f"Fecha inválida en fila {fila}.")
            continue
        
        try:
            if hasattr(fecha, "isoformat"):
                fecha_dt = fecha
            else:
                fecha_dt = pd.to_datetime(fecha)
            fecha_iso = fecha_dt.isoformat()
        except Exception:
            errores.append(f"Formato de fecha inválido en fila {fila}.")
            continue

        mes_numero = fecha_dt.month
        mes_nombre = fecha_dt.strftime("%B")  # Inglés, ej: "July"
        anio = fecha_dt.year

        # Validar monto
        try:
            monto_int = int(float(monto))
            if monto_int <= 0:
                errores.append(f"Monto debe ser mayor a cero en fila {fila}: {monto}")
                continue
        except (ValueError, TypeError):
            errores.append(f"Monto inválido en fila {fila}: {monto}")
            continue

        # Verificar duplicados
        key = (pr, it, str(detalle), fecha_iso, monto_int)
        if key in seen:
            errores.append(f"Línea duplicada en fila {fila}.")
            continue
        seen.add(key)

        records.append({
            "proyecto": pr,
            "item": it,
            "detalle": str(detalle) if not pd.isna(detalle) else "",
            "fecha": fecha_iso,
            "monto": monto_int,
            "proyecto_id": proyecto_id,
            "mes_numero": mes_numero,
            "mes_nombre": mes_nombre,
            "anio": anio
        })

    # Si hay errores, mostrarlos y no importar nada
    if errores:
        for error in errores[:5]:  # Mostrar solo los primeros 5 errores
            flash(error, "danger")
        if len(errores) > 5:
            flash(f"... y {len(errores) - 5} errores más.", "warning")
        return redirect(url_for("presupuestos.form_presupuesto"))

    # Insertar registros válidos
    if records:
        try:
            supabase.table("presupuesto").insert(records).execute()
            flash(f"Importación exitosa: {len(records)} registros guardados.", "success")
        except Exception as e:
            current_app.logger.error(f"Error en importación: {e}")
            flash("Error al guardar los registros en la base de datos.", "danger")
    else:
        flash("No se encontraron registros válidos para importar.", "warning")
    
    return redirect(url_for("presupuestos.form_presupuesto"))


@bp_presupuestos.route("/exportar", methods=["GET"])
@require_modulo('presupuesto')
def exportar_presupuesto():
    """Exporta todos los presupuestos a Excel"""
    supabase = current_app.config["SUPABASE"]
    
    try:
        # Obtener todos los presupuestos usando paginación manual
        page_size = 1000
        offset = 0
        presupuestos = []
        while True:
            batch = (
                supabase.table("presupuesto")
                .select("proyecto, item, detalle, fecha, monto")
                .order("fecha", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
                .data or []
            )
            presupuestos.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        if not presupuestos:
            flash("No hay datos para exportar.", "warning")
            return redirect(url_for("presupuestos.form_presupuesto"))

        # Crear DataFrame
        df = pd.DataFrame(presupuestos)
        
        # Crear archivo Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Presupuestos")
            
            # Obtener worksheet para formato
            worksheet = writer.sheets["Presupuestos"]
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Nombre del archivo con fecha
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"presupuestos_{fecha_actual}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exportando presupuestos: {e}")
        flash("Error al exportar los datos.", "danger")
        return redirect(url_for("presupuestos.form_presupuesto"))