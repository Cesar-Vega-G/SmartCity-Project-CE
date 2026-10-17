# SmartCity-Project-CE

Proyecto de Bases de Datos (CE-3101, TEC): SmartCity Analytics con datos abiertos de Madrid.
Avance 1: PostgreSQL + MongoDB.

## Requisitos

- Docker Desktop
- Python 3.11 o superior

## Cómo levantar todo

1. Copiar las variables de entorno y levantar las bases:
   ```
   copy .env.example .env
   docker compose up -d
   ```
2. Instalar las librerías de Python:
   ```
   pip install -r requirements.txt
   ```
3. Descargar los datos crudos en `data/raw/` (ver `docs/generacion_datos.md`).
4. Correr los scripts en este orden:
   ```
   python data/generators/catalogo.py
   python data/generators/clima.py
   python data/generators/cargar_mongo.py
   python data/generators/cargar_postgres.py
   ```

## Estructura

| Carpeta | Contenido |
| --- | --- |
| `postgres/init` | DDL que crea las tablas (se ejecuta solo al levantar Docker) |
| `postgres/consultas` | Consultas de PostgreSQL |
| `postgres/vistas_funciones` | Vistas, vista materializada y funciones |
| `mongo/consultas` | Consultas de MongoDB |
| `data/generators` | Scripts de carga de datos |
| `docs` | Contrato de datos, generación de datos y documentación |
