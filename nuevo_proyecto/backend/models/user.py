from werkzeug.security import check_password_hash

class User:
    def __init__(self, id, nombre, correo, hashed_password, modulos=None):
        self.id = id
        self.nombre = nombre
        self.correo = correo
        self.hashed_password = hashed_password
        self.modulos = modulos if modulos is not None else []

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        """Verifica una contraseña hasheada contra una en texto plano."""
        if not self.hashed_password or not password:
            return False
        # Usar werkzeug para verificar contraseñas hasheadas con scrypt
        return check_password_hash(self.hashed_password, password)

    @classmethod
    def from_db_row(cls, row):
        """Crea una instancia de User desde un registro de la base de datos."""
        return cls(
            id=row.get('id'),
            nombre=row.get('nombre'),
            correo=row.get('email'), # La columna en la BD es 'email'
            hashed_password=row.get('password'), # Asume que la columna se llama 'password'
            modulos=row.get('modulos')
        )