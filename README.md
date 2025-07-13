# SOMYL System - Gestión de Compras y Pagos

Sistema moderno de gestión de órdenes de compra, pagos y presupuestos para empresas.

## 🚀 Características Principales

### ✨ Modernización Completa 2025
- **Interfaz moderna** con diseño responsivo y animaciones suaves
- **Dashboard de usuarios** con gestión avanzada de permisos
- **Formularios inteligentes** con validación en tiempo real
- **Búsqueda avanzada** y filtros en todos los módulos
- **Exportación** a Excel de reportes
- **Feedback visual** mejorado para mejor UX

### 📋 Módulos Principales
- **Usuarios**: Gestión completa con dashboard, roles y permisos
- **Órdenes de Compra**: Formularios modernos con validaciones
- **Órdenes de Pago**: Cálculo automático de IVA y gestión de facturas
- **Ingresos**: Registro con opción de documentos pendientes
- **Pagos**: Informe con filtros avanzados y estados visuales
- **Proveedores**: Gestión completa de proveedores y cuentas
- **Presupuestos**: Planificación con tabla editable de gastos
- **Estado Presupuesto**: Dashboard con gráficos y comparativas
- **Gastos Directos**: Registro y seguimiento de gastos

### 🛠️ Mejoras Técnicas
- **Corrección IVA**: Cálculo y visualización correcta en formularios y PDFs
- **Sin Documento**: Permite ingresos urgentes sin factura
- **Números OC**: Guardado correcto de números de órdenes de compra
- **Cache inteligente**: Mejor rendimiento en consultas
- **Validaciones**: Controles de integridad de datos mejorados

## 🔧 Tecnologías

- **Backend**: Python 3.12.8, Flask 3.1.1
- **Base de Datos**: Supabase (PostgreSQL)
- **Frontend**: Bootstrap 5, jQuery, Select2
- **PDFs**: ReportLab, PDFKit
- **Deployment**: Railway, Gunicorn

## 📦 Instalación

### Requisitos
- Python 3.12+
- pip
- Git

### Setup Local
```bash
# Clonar repositorio
git clone https://github.com/CarlosATO/seguimiento_ordenes.git
cd seguimiento_ordenes

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase

# Ejecutar aplicación
python run.py
```

### Deploy en Railway
1. Fork del repositorio
2. Conectar con Railway
3. Configurar variables de entorno
4. Deploy automático desde main

## 🗂️ Estructura del Proyecto

```
seguimiento_ordenes/
├── app/                      # Aplicación principal
│   ├── modules/             # Módulos de funcionalidad
│   ├── templates/           # Templates HTML
│   └── utils/              # Utilidades y helpers
├── scripts/                 # Scripts SQL y migraciones
├── utils/                   # Herramientas de desarrollo
├── docs/                    # Documentación
├── requirements.txt         # Dependencias Python
├── runtime.txt             # Versión Python para Railway
├── Procfile                # Configuración Railway
└── run.py                  # Punto de entrada

```

## 🔒 Variables de Entorno

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SECRET_KEY=your_secret_key
FLASK_ENV=production
```

## 📱 Uso

### Acceso
1. Acceder al sistema con credenciales
2. Dashboard principal con accesos rápidos
3. Navegación por módulos según permisos

### Flujo Principal
1. **Crear Orden de Compra** → Formulario moderno con validaciones
2. **Registrar Ingreso** → Con o sin documento inicial
3. **Generar Orden de Pago** → Cálculo automático de totales
4. **Seguimiento** → Dashboard con estados y filtros

## 🚀 Nuevas Funcionalidades

### Dashboard de Usuarios
- Vista completa de usuarios activos
- Edición inline de permisos
- Gestión de contraseñas temporales
- Estadísticas de acceso

### Documentos Pendientes
- Permite ingresos urgentes sin factura
- Advertencias visuales
- Completado posterior de documentos

### Filtros Avanzados
- Búsqueda en tiempo real
- Filtros múltiples combinables
- Exportación de resultados filtrados

### Interfaz Moderna
- Diseño SOMYL limpio y profesional
- Animaciones suaves
- Feedback visual inmediato
- Responsive design completo

## 🔧 Mantenimiento

### Scripts Disponibles
- `utils/check_database.py` - Verificar estado de BD
- `utils/reset_passwords.py` - Resetear contraseñas
- `scripts/` - Migraciones y optimizaciones SQL

### Logs y Monitoreo
- Logs automáticos en Railway
- Verificaciones de salud en `/health`
- Métricas de rendimiento

## 📈 Optimizaciones

- **Base de datos**: Índices optimizados para consultas frecuentes
- **Frontend**: Lazy loading y caching inteligente
- **API**: Consultas optimizadas con cache
- **Assets**: Compresión y minificación automática

## 🤝 Contribuir

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto es de uso interno de SOMYL.

## 📞 Soporte

Para soporte técnico, contactar:
- **Desarrollador**: Carlos Alegría
- **Sistema**: SOMYL 2025
- **Versión**: 1.0.0

---

*Sistema desarrollado con ❤️ para optimizar la gestión empresarial*
