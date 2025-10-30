# TALLER BBVA - SESIÓN 3
## Data & Analytics: AWS Glue + Athena

**Duración:** 3 horas  
**Nivel:** Intermedio  
**Caso:** Abandono y reactivación de clientes

---

## 🎯 OBJETIVO

Construir un pipeline de datos que procese transacciones bancarias para identificar:
- Clientes abandonados (60+ días sin transacción)
- Clientes reactivados (vuelven después de abandono)
- Métricas de comportamiento

---

## 🏗️ ARQUITECTURA

![Arquitectura Pipeline Data Analytics](images/hoc-sesion-3-arq.png)

---

## 📊 CAPAS DE DATOS

```mermaid
flowchart LR
    A[RDV<br/>Raw Data Value] -->|Limpieza| B[Datos técnicamente<br/>correctos]
    C[UDV<br/>Universal Data Value] -->|Integración| D[Vista 360<br/>del cliente]
    E[DDV<br/>Dimensional Data Value] -->|Modelo estrella| F[Optimizado<br/>para BI]
    
    style A fill:#E5F5FF
    style C fill:#E5FFE5
    style E fill:#FFE5FF
```

| Capa | Qué hace | Input | Output |
|------|----------|-------|--------|
| **RDV** | Limpieza técnica | CSV crudos | Parquet válido |
| **UDV** | Integración | RDV separado | Vista unificada |
| **DDV** | Modelo dimensional | UDV plano | Fact + Dims |

---

## 📦 MATERIALES

**Repo GitHub:**
```
https://github.com/ANALITIKACLOUD/hands-on-cloud
Carpeta: sesion-03-data-analytics/
```

**Datasets:**
- `maestra_clientes.csv` (1,000 clientes)
- `clientes_transacciones.csv` (10,000 transacciones)

---

# LAB 1: Setup (15 min)

## Objetivo
Crear buckets S3 + IAM Role + Subir datos

---

## PASO 1: Crear Buckets S3

```mermaid
flowchart LR
    A[Console AWS] --> B[S3]
    B --> C[Create bucket]
    C --> D[Repetir 4 veces]
```

### Crear 4 buckets:

| # | Nombre | Propósito |
|---|--------|-----------|
| 1 | `bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]` | Archivos CSV crudos |
| 2 | `bbva-rdv-[PRIMERNOMBRE-APELLIDOPATERNO]` | Parquet limpio |
| 3 | `bbva-udv-[PRIMERNOMBRE-APELLIDOPATERNO]` | Parquet integrado |
| 4 | `bbva-ddv-[PRIMERNOMBRE-APELLIDOPATERNO]` | Parquet dimensional |

**Configuración (para los 4):**
```
Region: us-east-2 (Ohio)
Block public access: ENABLED
Versioning: Disabled
Encryption: SSE-S3
```

> ⚠️ Reemplaza `[PRIMERNOMBRE-APELLIDOPATERNO]` con tus iniciales (ej: `bbva-landing-juan-perez`)

---

## PASO 2: Subir Datasets

### 2.1 Descargar CSVs
Ir al repo → `sesion-03-data-analytics/datos/landing/`

Descargar:
- `maestra_clientes.csv`
- `clientes_transacciones.csv`

### 2.2 Subir a S3
```
1. Abrir bucket: bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]
2. Click "Upload"
3. Arrastrar los 2 CSVs
4. Click "Upload"
```

✅ **Verificar:** 2 archivos en Landing

---

## PASO 3: Usar IAM Role Existente

```mermaid
flowchart TD
    A[IAM Console] --> B[Roles]
    B --> C[Buscar rol existente]
    C --> D[GlueServiceRole-BBVA]
    
    style D fill:#E5FFE5
```

### 3.1 Verificar Role

El rol `GlueServiceRole-BBVA` ya está creado y configurado con los permisos necesarios:

- **Política 1:** `AWSGlueServiceRole` (managed)
- **Política 2:** Custom S3 access (inline) para buckets `bbva-*`

### Asignar Role en Glue Jobs

Cuando crees los Glue Jobs, usa este rol:

```
IAM Role: GlueServiceRole-BBVA
```

✅ **Verificar:** Role existe y está disponible

---

## CHECKPOINT LAB 1

- [ ] 4 buckets S3 creados
- [ ] 2 CSVs en `bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]`
- [ ] Verificado que el IAM Role `GlueServiceRole-BBVA` está disponible

---

# LAB 2: Glue Job - Landing → RDV (30 min)

## Objetivo
Limpiar y validar datos crudos

```mermaid
flowchart LR
    A[CSV<br/>Landing] -->|Leer| B[Validar<br/>datos]
    B -->|Limpiar| C[Normalizar<br/>texto]
    C -->|Particionar| D[Parquet<br/>RDV]
    
    style A fill:#FFE5E5
    style D fill:#E5F5FF
```

---

## PASO 1: Crear Glue Job

### 1.1 Navegación
```
AWS Console → AWS Glue → ETL jobs → Script editor
```

### 1.2 Configuración

**Job details:**
```
Name: landing-to-rdv
IAM Role: GlueServiceRole-BBVA
Type: Spark
Glue version: 4.0
Language: Python 3
Worker type: G.1X
Number of workers: 2
```

### 1.3 Job Parameters

En la sección **"Job parameters"** (expandir si está colapsada), agregar los siguientes parámetros uno por uno:

**Job parameters (agregar en la sección "Job parameters"):**
```
--JOB_NAME = bbva-etl-transacciones-rdv
--AWS_REGION = us-east-2
--S3_INPUT = s3://bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]/maestra_clientes.csv
--S3_OUTPUT_BASE = s3://bbva-rdv-[PRIMERNOMBRE-APELLIDOPATERNO]/data/
--FECHA_RUTINA = 2025-10-22
--FILE_NAME = maestra_clientes.csv
--CRAWLER_NAME = crw_rdv
--DATABASE_RDV = banca_rdv
--UDV_JOB_NAME = bbva-etl-transacciones-udv
--UDV_S3_OUTPUT_BASE = s3://bbva-udv-[PRIMERNOMBRE-APELLIDOPATERNO]/data/
--UDV_CRAWLER_NAME = crw_udv
```

> 💡 **Nota:** Reemplaza `[PRIMERNOMBRE-APELLIDOPATERNO]` con tus iniciales y ajusta `FECHA_RUTINA` según corresponda. Si procesas `clientes_transacciones.csv`, cambia `--S3_INPUT` y `--FILE_NAME` según corresponda.

---

## PASO 2: Script PySpark

### Descargar script
```
Repo → sesion-03-data-analytics/glue-jobs/
```

### Copiar al editor de Glue
Pegar todo el contenido en el script editor

### Guardar
Click "Save" (arriba a la derecha)

---

## PASO 3: Ejecutar

### 3.1 Run
Click "Run"

### 3.2 Monitorear
```
Tab: Runs
Status: Running → Succeeded (2-3 min)
```

### 3.3 Logs
```
Click en Run ID
Ver: Logs tab
```

**Buscar en logs:**
```
✅ Clientes leídos: 1000
✅ Transacciones leídas: 10000
✅ JOB COMPLETADO
```

---

## PASO 4: Verificar Output

### Abrir S3
```
Bucket: bbva-rdv-[PRIMERNOMBRE-APELLIDOPATERNO]
```

### Estructura esperada
```
rdv/
├── clientes_transacciones/
│   └── fecha_rutina=2025-10-22/
│       └── *.parquet
```

✅ **Verificar:** Carpetas particionadas con archivos .parquet

---

## 🎓 CONCEPTO: Parquet vs CSV

```mermaid
flowchart LR
    A[CSV 100 MB] -->|Glue Job| B[Parquet 10 MB]
    B --> C[Lectura columnar]
    B --> D[Compresión]
    B --> E[Athena 10x faster]
    
    style A fill:#FFE5E5
    style B fill:#E5FFE5
```

| Aspecto | CSV | Parquet |
|---------|-----|---------|
| Tamaño | 100 MB | 10 MB |
| Lectura | Completa | Solo columnas necesarias |
| Athena | Lento + caro | Rápido + barato |
| Compresión | No | Sí (Snappy) |

---

## 🎓 CONCEPTO: Particionamiento

```mermaid
flowchart TD
    A[Query: WHERE fecha_rutina='2024-12-15'] --> B{Particionado?}
    B -->|NO| C[Escanea TODO<br/>100 GB]
    B -->|SÍ| D[Escanea SOLO<br/>fecha_rutina=2024-12-15<br/>8 GB]
    
    C --> E[Costo: $5]
    D --> F[Costo: $0.40]
    
    style C fill:#FFE5E5
    style D fill:#E5FFE5
```

**Ventaja:** Athena solo lee particiones necesarias
**Ahorro:** 90% menos datos escaneados = 90% menos costo

---

# LAB 3: Glue Job - RDV → UDV (30 min)

## Objetivo
Integrar clientes + transacciones + Calcular métricas

```mermaid
flowchart LR
    A[Clientes<br/>RDV] -->|JOIN| C[Vista 360°<br/>cliente]
    B[Transacciones<br/>RDV] -->|JOIN| C
    C -->|Calcular| D[Edad<br/>Antigüedad<br/>Estado]
    D -->|Parquet| E[UDV]
    
    style A fill:#E5F5FF
    style B fill:#E5F5FF
    style E fill:#E5FFE5
```

---

## PASO 1: Crear Job

### Configuración
```
Name: rdv-to-udv
IAM Role: GlueServiceRole-BBVA
Type: Spark
Glue version: 4.0
```

### Job Parameters

En la sección **"Job parameters"** (expandir si está colapsada), agregar los siguientes parámetros uno por uno:

**Job parameters (agregar en la sección "Job parameters"):**
```
--JOB_NAME = bbva-etl-transacciones-udv
--AWS_REGION = us-east-2
--DATABASE_RDV = banca_rdv
--TABLE_NAME = clientes_transacciones
--FECHA_RUTINA = 2025-10-23
--S3_OUTPUT_BASE = s3://bbva-udv-[PRIMERNOMBRE-APELLIDOPATERNO]/data/
--CRAWLER_NAME_UDV = crw_udv
```

> 💡 **Nota:** Reemplaza `[PRIMERNOMBRE-APELLIDOPATERNO]` con tus iniciales y ajusta `FECHA_RUTINA` según corresponda.

---

## PASO 2: Script

Descargar: `sesion-03-data-analytics/glue-jobs/`

Copiar al editor → Guardar

---

## PASO 3: Ejecutar

Run → Esperar Succeeded (3-4 min)

---

## PASO 4: Verificar

### S3 Output
```
Bucket: bbva-udv-[PRIMERNOMBRE-APELLIDOPATERNO]

Estructura:
udv/
└── clientes_360/
    └── fecha_rutina=2025-10-22/
        └── *.parquet
```

### Verificar en logs
```
✅ Clientes con transacciones
✅ Métricas calculadas:
   - edad
   - antiguedad_dias
   - total_transacciones
   - dias_sin_transaccion
   - estado_cliente (activo/inactivo/abandonado)
```

---

## 🎓 CONCEPTO: Vista 360°

```mermaid
flowchart TD
    A[Cliente ID: C100001] --> B[Datos maestros]
    A --> C[Transacciones agregadas]
    A --> D[Métricas calculadas]
    
    B --> E[Nombre<br/>Edad<br/>Segmento]
    C --> F[Total transacciones<br/>Monto total<br/>Última transacción]
    D --> G[Días sin transacción<br/>Estado: activo/abandonado<br/>Frecuencia mensual]
    
    E --> H[UDV<br/>1 registro = 1 cliente]
    F --> H
    G --> H
    
    style H fill:#E5FFE5
```

**Antes (RDV):**
- Tabla clientes: 1,000 registros
- Tabla transacciones: 10,000 registros
- **Total:** 2 tablas separadas

**Después (UDV):**
- Tabla clientes_360: 1,000 registros
- **Total:** 1 tabla con TODO

---

# LAB 4: Glue Job - UDV → DDV (30 min)

## Objetivo
Crear modelo dimensional (estrella) para BI

```mermaid
flowchart TD
    A[UDV<br/>Tabla plana] --> B[Dimensiones]
    A --> C[Hechos]
    
    B --> D[dim_cliente]
    B --> E[dim_tiempo]
    B --> F[dim_canal]
    B --> G[dim_tipo_transaccion]
    
    C --> H[fact_transacciones]
    C --> I[fact_abandono]
    C --> J[fact_reactivacion]
    
    D --> K[DDV<br/>Modelo estrella]
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
    
    style A fill:#E5FFE5
    style K fill:#FFE5FF
```

---

## PASO 1: Crear Job

### Configuración
```
Name: udv-to-ddv
IAM Role: GlueServiceRole-BBVA
Type: Spark
Glue version: 4.0
```

### Job Parameters

En la sección **"Job parameters"** (expandir si está colapsada), agregar los siguientes parámetros uno por uno:

**Job parameters (agregar en la sección "Job parameters"):**
```
--JOB_NAME = udv-to-ddv
--AWS_REGION = us-east-2
--SOURCE_BUCKET = bbva-udv-[PRIMERNOMBRE-APELLIDOPATERNO]
--TARGET_BUCKET = bbva-ddv-[PRIMERNOMBRE-APELLIDOPATERNO]
--FECHA_RUTINA = 2025-10-23
```

> 💡 **Nota:** Reemplaza `[PRIMERNOMBRE-APELLIDOPATERNO]` con tus iniciales y ajusta `FECHA_RUTINA` según corresponda.

---

## PASO 2: Script

Descargar: `sesion-03-data-analytics/glue-jobs/`

---

## PASO 3: Ejecutar

Run → Esperar (4-5 min)

---

## PASO 4: Verificar

### S3 Structure
```
ddv/
├── dim_cliente/
├── dim_tiempo/
├── dim_canal/
├── dim_tipo_transaccion/
├── fact_transacciones/
├── fact_abandono/
└── fact_reactivacion/
```

✅ **Verificar:** 7 carpetas con archivos .parquet

---

## 🎓 CONCEPTO: Modelo Estrella

```mermaid
erDiagram
    FACT_TRANSACCIONES ||--o{ DIM_CLIENTE : "id_cliente"
    FACT_TRANSACCIONES ||--o{ DIM_TIEMPO : "fecha_id"
    FACT_TRANSACCIONES ||--o{ DIM_CANAL : "canal_id"
    FACT_TRANSACCIONES ||--o{ DIM_TIPO : "tipo_id"
    
    FACT_TRANSACCIONES {
        bigint id_cliente
        int fecha_id
        int canal_id
        int tipo_id
        decimal monto
        decimal saldo
    }
    
    DIM_CLIENTE {
        bigint id_cliente PK
        string nombre
        int edad
        string segmento
    }
    
    DIM_TIEMPO {
        int fecha_id PK
        date fecha
        int año
        int mes
        int dia
        string nombre_mes
    }
    
    DIM_CANAL {
        int canal_id PK
        string canal
        string categoria
    }
    
    DIM_TIPO {
        int tipo_id PK
        string tipo_transaccion
        string categoria
    }
```

**Ventajas:**
- Queries más rápidos (JOINs simples)
- Agregaciones eficientes
- Fácil de entender para negocio
- Optimizado para BI tools

---

# LAB 5: Crawler + Data Catalog (20 min)

## Objetivo
Escanear DDV y crear metadata para Athena

```mermaid
flowchart LR
    A[Glue Crawler] -->|Escanea| B[DDV S3<br/>Parquet]
    B -->|Extrae| C[Schema<br/>Particiones<br/>Ubicación]
    C -->|Registra| D[Data Catalog<br/>Metadata]
    D -->|Lee| E[Athena]
    
    style B fill:#FFE5FF
    style D fill:#E5F5FF
    style E fill:#FFF5E5
```

---

## PASO 1: Crear Crawler

### Navegación
```
AWS Glue → Crawlers → Create crawler
```

### Configuración

**Name:** `ddv-crawler`

**Data source:**
```
Type: S3
Path: s3://bbva-ddv-[PRIMERNOMBRE-APELLIDOPATERNO]/
Subsequent crawler runs: Crawl all folders
```

**IAM Role:** `GlueServiceRole-BBVA`

**Target database:**
```
Database: bbva_analytics (crear si no existe)
Table prefix: ddv_
```

**Schedule:** On demand

---

## PASO 2: Run Crawler

```
1. Seleccionar crawler: ddv-crawler
2. Click "Run"
3. Esperar Status: Completed (2-3 min)
```

---

## PASO 3: Verificar Tables

### Data Catalog
```
AWS Glue → Tables
Database: bbva_analytics
```

**Tablas creadas (7):**
- `ddv_dim_cliente`
- `ddv_dim_tiempo`
- `ddv_dim_canal`
- `ddv_dim_tipo_transaccion`
- `ddv_fact_transacciones`
- `ddv_fact_abandono`
- `ddv_fact_reactivacion`

### Ver Schema
Click en cada tabla → Ver columnas y tipos

✅ **Verificar:** 7 tablas con schemas correctos

---

## 🎓 CONCEPTO: Data Catalog

```mermaid
flowchart TD
    A[Data Catalog] --> B[Metadata]
    B --> C[Schema<br/>Columnas + Tipos]
    B --> D[Location<br/>S3 paths]
    B --> E[Partitions<br/>fecha_rutina]
    B --> F[Stats<br/>Tamaño, registros]
    
    G[Athena] -->|Lee metadata| A
    G -->|Consulta datos| H[S3]
    
    style A fill:#E5F5FF
    style G fill:#FFF5E5
```

**NO almacena datos, solo metadata**

Athena usa el catalog para:
1. Saber dónde están los datos (S3 path)
2. Entender el schema (columnas/tipos)
3. Optimizar queries (particiones)

---

# LAB 6: Queries en Athena (30 min)

## Objetivo
Consultar datos con SQL y analizar métricas

```mermaid
flowchart LR
    A[Athena Query] -->|Lee metadata| B[Data Catalog]
    A -->|Escanea datos| C[DDV S3]
    C -->|Resultados| D[Athena Results]
    D -->|Guarda| E[S3 Results<br/>Bucket]
    
    style A fill:#FFF5E5
    style C fill:#FFE5FF
```

---

## PASO 1: Setup Athena

### Query Editor
```
AWS Console → Athena → Query editor
```

### Configurar Results Location
```
Settings → Manage
Query result location: s3://bbva-ddv-[PRIMERNOMBRE-APELLIDOPATERNO]/athena-results/
Save
```

---

## PASO 2: Query 1 - Exploración

### Objetivo: Ver estructura de datos

```sql
-- Ver primeros 10 clientes
SELECT *
FROM bbva_analytics.ddv_dim_cliente
LIMIT 10;

-- Ver distribución por segmento
SELECT 
    segmento_cliente,
    COUNT(*) as total_clientes
FROM bbva_analytics.ddv_dim_cliente
GROUP BY segmento_cliente
ORDER BY total_clientes DESC;
```

**Ejecutar:** Click "Run"

✅ **Verificar:** Resultados en pantalla

---

## PASO 3: Query 2 - Clientes Abandonados

### Objetivo: Identificar clientes sin actividad 60+ días

```sql
SELECT 
    c.id_cliente,
    c.nombre_completo,
    c.segmento_cliente,
    a.dias_sin_transaccion,
    a.ultima_transaccion,
    a.transacciones_historicas,
    a.monto_total_historico
FROM bbva_analytics.ddv_fact_abandono a
JOIN bbva_analytics.ddv_dim_cliente c 
    ON a.id_cliente = c.id_cliente
WHERE a.dias_sin_transaccion >= 60
ORDER BY a.dias_sin_transaccion DESC
LIMIT 20;
```

**Analizar:**
- ¿Cuántos clientes abandonados?
- ¿Qué segmento tiene más abandono?
- ¿Cuántos días promedio sin transacción?

---

## PASO 4: Query 3 - Métricas de Abandono por Segmento

```sql
SELECT 
    c.segmento_cliente,
    COUNT(DISTINCT a.id_cliente) as clientes_abandonados,
    AVG(a.dias_sin_transaccion) as promedio_dias_abandono,
    AVG(a.monto_total_historico) as promedio_monto_historico,
    MIN(a.ultima_transaccion) as abandono_mas_antiguo
FROM bbva_analytics.ddv_fact_abandono a
JOIN bbva_analytics.ddv_dim_cliente c 
    ON a.id_cliente = c.id_cliente
GROUP BY c.segmento_cliente
ORDER BY clientes_abandonados DESC;
```

**Insight esperado:**
- Segmento Premium tiene menos abandono
- Segmento Estándar tiene más días de inactividad

---

## PASO 5: Query 4 - Reactivaciones Exitosas

### Objetivo: Clientes que volvieron después de abandonar

```sql
SELECT 
    c.id_cliente,
    c.nombre_completo,
    c.segmento_cliente,
    r.dias_abandono,
    r.fecha_reactivacion,
    r.transacciones_post_reactivacion,
    r.monto_post_reactivacion
FROM bbva_analytics.ddv_fact_reactivacion r
JOIN bbva_analytics.ddv_dim_cliente c 
    ON r.id_cliente = c.id_cliente
WHERE r.transacciones_post_reactivacion >= 2
ORDER BY r.fecha_reactivacion DESC
LIMIT 20;
```

**Analizar:**
- ¿Cuántos se reactivaron?
- ¿Cuántos días estuvieron abandonados?
- ¿Cuánto transaccionan post-reactivación?

---

## PASO 6: Query 5 - Dashboard Ejecutivo

### Objetivo: Métricas consolidadas para negocio

```sql
SELECT 
    'Total Clientes' as metrica,
    COUNT(*) as valor
FROM bbva_analytics.ddv_dim_cliente

UNION ALL

SELECT 
    'Clientes Activos',
    COUNT(*)
FROM bbva_analytics.ddv_fact_transacciones
WHERE fecha_rutina = '2024-12-15'

UNION ALL

SELECT 
    'Clientes Abandonados (60+ dias)',
    COUNT(DISTINCT id_cliente)
FROM bbva_analytics.ddv_fact_abandono
WHERE dias_sin_transaccion >= 60

UNION ALL

SELECT 
    'Clientes Reactivados',
    COUNT(DISTINCT id_cliente)
FROM bbva_analytics.ddv_fact_reactivacion

UNION ALL

SELECT 
    'Monto Total Transaccionado (Dic 2024)',
    ROUND(SUM(monto), 2)
FROM bbva_analytics.ddv_fact_transacciones
WHERE fecha_rutina = '2024-12-15';
```

---

## 🎓 CONCEPTO: Costos Athena

```mermaid
flowchart TD
    A[Costo Athena] --> B[Por TB escaneado]
    B --> C[Sin particiones<br/>Escanea TODO]
    B --> D[Con particiones<br/>Escanea SOLO necesario]
    
    C --> E[100 GB escaneados<br/>$5.00]
    D --> F[10 GB escaneados<br/>$0.50]
    
    style C fill:#FFE5E5
    style D fill:#E5FFE5
```

**Precio:** $5.00 por TB escaneado

**Optimizaciones:**
1. Particionamiento (ahorro 80-90%)
2. Parquet vs CSV (ahorro 80%)
3. SELECT columnas específicas (no SELECT *)
4. WHERE en particiones (fecha_rutina)

**Ejemplo real:**
```sql
-- ❌ CARO: Escanea 100 GB
SELECT * FROM tabla;

-- ✅ BARATO: Escanea 10 GB
SELECT id, nombre, monto
FROM tabla
WHERE fecha_rutina = '2024-12-15';
```

---

# LAB 7: Lambda Orquestador (15 min)

## Objetivo
Ejecutar Glue Jobs automáticamente cuando se suben archivos CSV a S3

```mermaid
flowchart TD
    A[CSV subido a S3] -->|S3 Event| B[Lambda]
    B -->|StartJobRun| C[Glue Job<br/>configurado]
    C --> D[Output en S3]
    
    style B fill:#FFA500
    style D fill:#E5F5FF
```

---

## PASO 1: Crear Lambda Function

### Navegación
```
AWS Lambda → Functions → Create function
```

### Configuración
```
Function name: glue-pipeline-orchestrator
Runtime: Python 3.12
Architecture: x86_64
```

### IAM Role
```
Execution role: Use an existing role
Existing role: lambda-bbva-etl-role
```

> ⚠️ El rol `lambda-bbva-etl-role` ya está creado con los permisos necesarios para ejecutar Glue Jobs

---

## PASO 2: Script Python

### Descargar código
```
Repo → sesion-03-data-analytics/lambda/lambda_function.py
```

### Copiar al editor Lambda
1. Abrir el archivo `lambda_function.py`
2. Copiar todo el contenido
3. Pegar en el editor de código de Lambda
4. Click "Deploy"

### Variables de Entorno (opcional)
Puedes configurar variables de entorno en la configuración del Lambda:

```
GLUE_JOB_NAME = bbva-etl-transacciones-rdv
S3_OUTPUT_BASE = s3://bbva-rdv-[PRIMERNOMBRE-APELLIDOPATERNO]/data/
CRAWLER_NAME = crw_rdv_clientes_transacciones
GLUE_REGION = us-east-2
```

> 💡 Si no configuras variables de entorno, el Lambda usará valores por defecto

---

## PASO 4: Configurar S3 Trigger

### Navegación
```
Lambda → glue-pipeline-orchestrator → Add trigger
```

### Configuración
```
Source: S3
Bucket: bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]
Event type: PUT
Prefix: (vacío)
Suffix: .csv
```

---

## PASO 5: Probar Pipeline

### Test Manual
```
Lambda → Test tab
Create test event:
{
  "Records": [{
    "s3": {
      "bucket": {
        "name": "bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]"
      },
      "object": {
        "key": "clientes_transacciones.csv"
      }
    }
  }]
}
```

Click "Test"

### Monitorear
```
CloudWatch Logs → Log groups
/aws/lambda/glue-pipeline-orchestrator
```

**Buscar en logs:**
```
🔧 Configuration:
   Job Name: bbva-etl-transacciones-rdv
   Output: s3://bbva-rdv-.../data/...
📋 Job Arguments: {...}
Glue Job started successfully!
Job Run ID: jr_xxxxx
```

---

## Test End-to-End

### Subir CSV nuevo
```
1. Modificar fecha en clientes_transacciones.csv
2. Subir a s3://bbva-landing-[PRIMERNOMBRE-APELLIDOPATERNO]/
3. Esperar 5-10 min
4. Verificar DDV actualizado
```

✅ **Verificar:** Pipeline completo automático

---

# 🎉 CIERRE

## ✅ LO QUE CONSTRUIMOS

```mermaid
flowchart TD
    A[Landing S3] --> B[3 Glue Jobs<br/>secuenciales]
    B --> C[RDV + UDV + DDV<br/>Parquet particionado]
    C --> D[Glue Crawler]
    D --> E[Data Catalog<br/>7 tablas]
    E --> F[Athena<br/>SQL queries]
    F --> G[Métricas de negocio]
    
    H[Lambda] -->|Orquesta| B
    
    style A fill:#FFE5E5
    style C fill:#E5FFE5
    style E fill:#E5F5FF
    style F fill:#FFF5E5
```

---

## 📊 MÉTRICAS CLAVE

| Métrica | Valor |
|---------|-------|
| Clientes procesados | 1,000 |
| Transacciones procesadas | 10,000 |
| Clientes abandonados | ~150 |
| Clientes reactivados | ~30 |
| Ahorro vs CSV | 80-90% |
| Tiempo total pipeline | 8-12 min |

---

## 🎓 CONCEPTOS APRENDIDOS

### Data Engineering
- **ETL con Glue** (Extract, Transform, Load)
- **PySpark** (procesamiento distribuido)
- **Capas de datos** (RDV, UDV, DDV)

### Optimización
- **Parquet** (formato columnar comprimido)
- **Particionamiento** (reducir scan de datos)
- **Catálogo de datos** (metadata centralizada)

### Arquitectura
- **Lambda** (orquestación serverless)
- **Modelo estrella** (dimensional para BI)
- **S3 Events** (triggers automáticos)

---

## 💰 COSTOS APROXIMADOS

### Por ejecución del pipeline:
```
Glue Jobs (3 x 2 DPU x 5 min): $0.15
Lambda (1 invocación): $0.0000002
S3 Storage (100 MB): $0.0023
Athena (5 queries, 50 MB): $0.00025
---
TOTAL por ejecución: ~$0.15
```

### Por mes (1 ejecución diaria):
```
$0.15 x 30 días = $4.50/mes
```

**Optimizaciones aplicadas:**
- Parquet (80% menos storage)
- Particionamiento (90% menos scan)
- Workers: 2 (no 10)

---

## 🚀 PRÓXIMOS PASOS

### Extensiones posibles:
1. **Step Functions** (orquestación visual)
2. **QuickSight** (dashboards visuales)
3. **Redshift Spectrum** (queries a escala)
4. **Glue DataBrew** (limpieza sin código)
5. **EventBridge** (scheduling avanzado)

### Mejoras:
- Alertas SNS por errores
- Dead Letter Queue para retry
- Validación de calidad de datos
- Tests unitarios de transformaciones

---

## 📚 RECURSOS

### Documentación AWS:
- AWS Glue: https://docs.aws.amazon.com/glue/
- Athena: https://docs.aws.amazon.com/athena/
- Lambda: https://docs.aws.amazon.com/lambda/

### Repositorio:
```
https://github.com/ANALITIKACLOUD/hands-on-cloud
```

### Contacto:
- Instructor: Jose Alegre Argomedo
- Soporte: jose.alegre@analitika.cloud

---

## ❓ TROUBLESHOOTING

### Error: "Role not authorized"
```
Verificar IAM policies en GlueServiceRole-BBVA
```

### Error: "Access Denied S3"
```
Verificar nombres de buckets en job parameters
```

### Glue Job falla
```
Ver CloudWatch Logs:
AWS Glue → Jobs → [job-name] → Runs → Error logs
```

### Athena: "Table not found"
```
1. Verificar Crawler corrió exitosamente
2. Refresh tables en Athena
3. Verificar database: bbva_analytics
```

### Lambda no se ejecuta
```
1. Verificar S3 trigger configurado
2. Ver CloudWatch Logs
3. Test manual con event de prueba
```

---

**FIN DEL TALLER**

¡Felicitaciones! 🎉

Has construido un pipeline completo de datos en AWS.
