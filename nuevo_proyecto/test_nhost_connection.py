"""
Script de prueba de conexión a Nhost GraphQL
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

print("\n" + "=" * 80)
print("PRUEBA DE CONEXIÓN A NHOST (GraphQL/Hasura)")
print("=" * 80)

print(f"\n📡 URL: {nhost_url}")
print(f"🔑 Secret: {nhost_secret[:20]}..." if nhost_secret else "❌ No configurado")

# Configurar transporte
transport = RequestsHTTPTransport(
    url=nhost_url,
    headers={
        'x-hasura-admin-secret': nhost_secret
    },
    verify=True,
    retries=3,
)

# Crear cliente
client = Client(transport=transport, fetch_schema_from_transport=True)

try:
    # Consulta de prueba - obtener esquema de tablas disponibles
    query = gql("""
    query {
        __schema {
            types {
                name
                kind
            }
        }
    }
    """)
    
    print("\n🔄 Ejecutando consulta de prueba...")
    result = client.execute(query)
    
    # Filtrar solo las tablas (types de tipo OBJECT que no empiezan con __)
    tables = [
        t['name'] for t in result['__schema']['types'] 
        if t['kind'] == 'OBJECT' and not t['name'].startswith('__')
    ]
    
    print(f"\n✅ Conexión exitosa!")
    print(f"\n📊 Tablas disponibles ({len(tables)}):")
    
    # Mostrar tablas que podrían contener info de producción
    relevant_tables = [t for t in tables if any(keyword in t.lower() for keyword in ['prod', 'proyecto', 'obra', 'trabajo'])]
    
    if relevant_tables:
        print("\n🎯 Tablas relevantes (producción/proyectos):")
        for table in relevant_tables[:20]:
            print(f"   - {table}")
    else:
        print("\n📋 Primeras 20 tablas:")
        for table in tables[:20]:
            print(f"   - {table}")
    
    print(f"\n💡 Total de tablas encontradas: {len(tables)}")
    
except Exception as e:
    print(f"\n❌ Error en la conexión:")
    print(f"   {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
