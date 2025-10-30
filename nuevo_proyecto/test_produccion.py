"""
Script de prueba para obtener Producción Actual desde Nhost
"""
import os
from dotenv import load_dotenv
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Cargar variables de entorno
load_dotenv()

# Configurar conexión a Nhost
nhost_url = os.environ.get("NHOST_GRAPHQL_URL")
nhost_secret = os.environ.get("NHOST_ADMIN_SECRET")

# Configurar transporte
transport = RequestsHTTPTransport(
    url=nhost_url,
    headers={'x-hasura-admin-secret': nhost_secret},
    verify=True,
    retries=3,
)

client = Client(transport=transport, fetch_schema_from_transport=False)

print("\n" + "=" * 80)
print("PRUEBA - Obtener Producción Actual desde Nhost")
print("=" * 80)

# ID de Supabase del proyecto a probar (BORGOÑO = 30)
supabase_proyecto_id = 30

print(f"\n🔍 Buscando producción para proyecto Supabase ID: {supabase_proyecto_id}")

try:
    # PASO 1: Buscar el proyecto en Nhost por supabase_proyecto_id
    query_proyecto = gql("""
    query GetProyecto($supabase_id: Int!) {
        proyectos(where: {supabase_proyecto_id: {_eq: $supabase_id}}) {
            id
            nombre
            supabase_proyecto_id
        }
    }
    """)
    
    print("\n📋 PASO 1: Buscando proyecto en Nhost...")
    result_proyecto = client.execute(query_proyecto, variable_values={"supabase_id": supabase_proyecto_id})
    
    if not result_proyecto['proyectos']:
        print(f"❌ No se encontró el proyecto con supabase_proyecto_id = {supabase_proyecto_id}")
        print("   El proyecto no está habilitado en el sistema de producción")
        exit()
    
    proyecto = result_proyecto['proyectos'][0]
    id_local = proyecto['id']
    nombre = proyecto['nombre']
    
    print(f"✅ Proyecto encontrado:")
    print(f"   Nombre: {nombre}")
    print(f"   ID Local (Nhost): {id_local}")
    print(f"   ID Supabase: {proyecto['supabase_proyecto_id']}")
    
    # PASO 2: Buscar datos operativos por id_proyecto (local)
    query_datos = gql("""
    query GetDatosOperativos($id_proyecto: Int!) {
        datos_operativos(where: {id_proyecto: {_eq: $id_proyecto}}) {
            id
            id_proyecto
            venta_total
        }
    }
    """)
    
    print(f"\n📊 PASO 2: Buscando datos operativos con id_proyecto = {id_local}...")
    result_datos = client.execute(query_datos, variable_values={"id_proyecto": id_local})
    
    datos = result_datos['datos_operativos']
    print(f"✅ Registros encontrados: {len(datos)}")
    
    # PASO 3: Sumar venta_total
    total_produccion = 0
    
    if datos:
        print(f"\n💰 Detalle de ventas:")
        for i, dato in enumerate(datos, 1):
            venta = float(dato.get('venta_total', 0) or 0)
            total_produccion += venta
            if i <= 10:  # Mostrar solo los primeros 10
                print(f"   {i}. Registro ID {dato['id']}: ${venta:,.0f}")
        
        if len(datos) > 10:
            print(f"   ... y {len(datos) - 10} registros más")
    else:
        print("⚠️  No hay datos operativos registrados para este proyecto")
    
    print(f"\n" + "=" * 80)
    print(f"🎯 PRODUCCIÓN ACTUAL: ${total_produccion:,.0f}")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ Error:")
    print(f"   {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
