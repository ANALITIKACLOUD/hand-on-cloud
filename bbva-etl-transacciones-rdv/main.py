import sys, re, time, json
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql import functions as F
import boto3

ARGS = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "S3_INPUT",
    "S3_OUTPUT_BASE",
    "FECHA_RUTINA",
    "CRAWLER_NAME",
    "AWS_REGION",
    "FILE_NAME",
    "UDV_JOB_NAME",          # p.ej. bbva-etl-transacciones-udv
    "DATABASE_RDV",          # p.ej. banca_rdv
    "UDV_S3_OUTPUT_BASE",    # p.ej. s3://.../curated/udv
    "UDV_CRAWLER_NAME"       # p.ej. crw_udv_clientes
])

sc = SparkContext()
glue_ctx = GlueContext(sc)
spark = glue_ctx.spark_session
logger = glue_ctx.get_logger()
job = Job(glue_ctx)
job.init(ARGS["JOB_NAME"], ARGS)

spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

SCHEMA_TRANSACCIONES = StructType([
    StructField("id_cliente",        StringType(), True),
    StructField("fecha_transaccion", StringType(), True),
    StructField("tipo_transaccion",  StringType(), True),
    StructField("monto",             StringType(), True),
    StructField("saldo_cuenta",      StringType(), True),
    StructField("canal",             StringType(), True),
])

SCHEMA_MAESTRA = StructType([
    StructField("id_cliente",         StringType(), True),
    StructField("nombre_completo",    StringType(), True),
    StructField("fecha_nacimiento",   StringType(), True),
    StructField("genero",             StringType(), True),
    StructField("ciudad",             StringType(), True),
    StructField("segmento_cliente",   StringType(), True),
    StructField("fecha_alta_cliente", StringType(), True),
])

file_name = ARGS["FILE_NAME"].strip().lower()
file_name = re.sub(r".*[/]", "", file_name)
file_name = re.sub(r"\.csv$", "", file_name)

if file_name == "clientes_transacciones":
    schema = SCHEMA_TRANSACCIONES
elif file_name == "maestra_clientes":
    schema = SCHEMA_MAESTRA
else:
    raise ValueError(
        f"FILE_NAME no reconocido: {ARGS['FILE_NAME']}. "
        f"Use 'clientes_transacciones.csv' o 'maestra_clientes.csv'."
    )

df = (
    spark.read
         .option("header", "true")
         .option("mode", "PERMISSIVE")
         .option("encoding", "UTF-8")
         .schema(schema)
         .csv(ARGS["S3_INPUT"])
)

df = df.withColumn("fecha_rutina", F.lit(ARGS["FECHA_RUTINA"]))

(
    df.repartition("fecha_rutina")
      .write
      .mode("overwrite")
      .format("parquet")
      .partitionBy("fecha_rutina")
      .option("compression", "snappy")
      .save(ARGS["S3_OUTPUT_BASE"])
)

logger.info(f"RAW escrito en {ARGS['S3_OUTPUT_BASE']}/fecha_rutina={ARGS['FECHA_RUTINA']}/")

glue = boto3.client("glue", region_name=ARGS["AWS_REGION"])
try:
    glue.start_crawler(Name=ARGS["CRAWLER_NAME"])
    logger.info(f"Crawler '{ARGS['CRAWLER_NAME']}' iniciado.")
except glue.exceptions.CrawlerRunningException:
    logger.warn(f"Crawler '{ARGS['CRAWLER_NAME']}' ya estaba ejecutándose.")
except Exception as e:
    logger.error(f"No se pudo iniciar el crawler: {e}")
    raise

# --------------------------- EJECUTAR JOB

def start_udv_job_and_wait(glue_client, job_name: str, arguments: dict, poll_seconds: int = 10):
    resp = glue_client.start_job_run(JobName=job_name, Arguments=arguments)
    run_id = resp["JobRunId"]
    logger.info(f"▶️ UDV job '{job_name}' lanzado. RunId={run_id} Args={json.dumps(arguments)}")
    while True:
        jr = glue_client.get_job_run(JobName=job_name, RunId=run_id)
        state = jr["JobRun"]["JobRunState"]
        if state in ("SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT", "ERROR"):
            logger.info(f"⏹ UDV job '{job_name}' terminó con estado: {state}")
            if state != "SUCCEEDED":
                raise RuntimeError(f"UDV job '{job_name}' terminó en estado {state}")
            break
        time.sleep(poll_seconds)

table_name = file_name  # clientes_transacciones | maestra_clientes

udv_args = {
    "--JOB_NAME":         "triggered-from-rdv",
    "--DATABASE_RDV":     ARGS["DATABASE_RDV"],
    "--TABLE_NAME":       table_name,
    "--FECHA_RUTINA":     ARGS["FECHA_RUTINA"],
    "--S3_OUTPUT_BASE":   ARGS["UDV_S3_OUTPUT_BASE"],
    "--CRAWLER_NAME_UDV": ARGS["UDV_CRAWLER_NAME"],
    "--AWS_REGION":       ARGS["AWS_REGION"],
}

glue.start_job_run(JobName=ARGS["UDV_JOB_NAME"], Arguments=udv_args)

job.commit()
