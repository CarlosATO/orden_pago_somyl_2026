from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    current_app,
    jsonify
)
from flask_login import login_required
from datetime import datetime
from app.modules.usuarios import require_modulo
from flask_login import current_user
from utils.logger import registrar_log_actividad

bp_nota_credito = Blueprint(
    "nota_credito", __name__,
    template_folder="../templates/nota_credito"
)

@login_required
@bp_nota_credito.route("/nota_credito", methods=["GET"])
@require_modulo('nota_credito')
def list_nota_credito():
    # ... Lógica similar a list_pendientes, adaptada para nota de crédito ...
    return render_template(
        "nota_credito/nota_credito.html",
        filas=[],
        stats={},
        fecha_actualizacion=datetime.now().strftime('%d/%m/%Y %H:%M')
    )

@login_required
@bp_nota_credito.route("/nota_credito/update", methods=["POST"])
@require_modulo('nota_credito')
def update_nota_credito():
    # ... Lógica similar a update_pendiente, adaptada para nota de crédito ...
    return redirect(url_for("nota_credito.list_nota_credito"))
