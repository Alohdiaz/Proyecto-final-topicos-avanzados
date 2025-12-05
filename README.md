# Proyecto-final-topicos-avanzados
Argenis Emanuel Aragón López   
Diego Alonso Díaz Palacios

Este proyecto consiste en el desarrollo de una API backend para la trazabilidad de piezas en una línea de producción.
El sistema permite:
Registrar piezas y rastrear su recorrido por diferentes estaciones.
Mantener un histórico detallado de eventos por pieza.
Exponer métricas agregadas para un dashboard de producción y calidad.
Integrar un módulo de analítica inteligente / IA para calcular riesgo de falla o detectar anomalías.
Implementar autenticación, autorización por roles y buenas prácticas de diseño.
El enfoque principal es el backend, su arquitectura, modelos, seguridad, documentación y despliegue.

# Los objetivos de este proyecto son:
Diseñar y construir una API backend estructurada, modular y documentada.
Implementar autenticación con JWT y autorización por roles.
Consumir y exponer datos desde una base de datos real.
Crear endpoints de métricas para dashboards.
Integrar un módulo básico de análisis inteligente.
Desplegar el backend a un servicio en la nube.

# Arquitectura del proyecto:
/app
   /models          # Modelos y tablas (SQLAlchemy)
   /schemas         # Validaciones y DTOs (Pydantic)
   /routers         # Endpoints organizados por módulo
   /services        # Lógica de negocio
   /core            # Seguridad, JWT, configuración
   main.py          # Punto de entrada del API
tests/              # Pruebas unitarias y de integración
.env                # Variables de entorno
requirements.txt

# Entidades principales
- User 
    id
    nombre
    email
    password (encriptado)
    rol (OPERADOR, SUPERVISOR, ADMIN)
    activo
    fecha_registro

-Pieza
    id (serial)
    tipo_pieza
    lote
    status (EN_PROCESO, OK, SCRAP, RETRABAJO)
    fecha_creacion

-Station
    id
    nombre
    tipo 
    linea

-Trace event
    id
    part_id
    station_id
    timestamp_entrada
    timestamp_salida
    resultado (OK, SCRAP, RETRABAJO)
    operador_id
    observaciones

# Funcionalidades implemetadas:
Auth y autorización 
Registro
Login
Protección de endpoints
Roles:
        Operadores
        Supervisor
        Admin

# Trazabilidad de las piezas
Crear piezas
Registrar eventos 
Actualizar estado de una pieza
Historial de una pieza

# Endpoints (Métricas)
GET /metrics/parts-by-status
Retorna conteo de piezas por estado.

GET /metrics/throughput?from&to
Producción diaria en un rango de fechas.

GET /metrics/station-cycle-time
Promedio de ciclo por estación.

GET /metrics/scrap-rate
Tasa de scrap por tipo de pieza o estación.


# Modulo de IA
Implementación mínima:
Motor basado en reglas.
Comparación con promedios en BD.
Alertas por piezas fuera de rango.
Opcional:
GET /ai/anomalies

# Tecnologías utilizadas
FastAPI
Python 
SQLAlchemy
PostgreSQL
JWT
Pydantic
Render

# Deploy
El backend debe estar desplegado en render

Requisitos:
Base de datos activa
Variables de entorno configuradas

Link repositorio:
https://github.com/Alohdiaz/Proyecto-final-topicos-avanzados.git 
 Link deploy render:
 https://proyecto-final-topicos-avanzados.onrender.com

