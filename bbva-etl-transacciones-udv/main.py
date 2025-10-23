import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType, DateType, DecimalType, StructType, StructField
)
import boto3

ARGS = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "DATABASE_RDV",       
    "TABLE_NAME", 
    "FECHA_RUTINA",
    "S3_OUTPUT_BASE",    
    "CRAWLER_NAME_UDV", 
    "AWS_REGION",
])

sc = SparkContext()
glue_ctx = GlueContext(sc)
spark = glue_ctx.spark_session
logger = glue_ctx.get_logger()
job = Job(glue_ctx); job.init(ARGS["JOB_NAME"], ARGS)

spark.conf.set("spark.sql.parquet.compression.codec", "snappy")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.hive.metastorePartitionPruningFallbackOnException", "true")


table_rdv = f"{ARGS['DATABASE_RDV']}.{ARGS['TABLE_NAME'].strip().lower()}"
df_raw = spark.table(table_rdv)

print("cantindad",df_raw.count())

if "fecha_rutina" in df_raw.columns:
    df_raw = df_raw.filter(F.col("fecha_rutina") == ARGS["FECHA_RUTINA"])
elif "fecha" in df_raw.columns:
    df_raw = (
        df_raw.filter(F.col("fecha") == ARGS["FECHA_RUTINA"])
              .withColumnRenamed("fecha", "fecha_rutina")
    )
else:
    df_raw = df_raw.withColumn("fecha_rutina", F.lit(ARGS["FECHA_RUTINA"]))

print("cantindad",df_raw.count())

TABLE = ARGS["TABLE_NAME"].strip().lower()

print(TABLE)

SCHEMA_UDV_TRANSACCIONES = StructType([
    StructField("id_cliente",        StringType(), True),
    StructField("fecha_transaccion", DateType(),  True),
    StructField("tipo_transaccion",  StringType(), True),
    StructField("monto",             DecimalType(18,2), True),
    StructField("saldo_cuenta",      DecimalType(18,2), True),
    StructField("canal",             StringType(), True),
])

SCHEMA_UDV_MAESTRA = StructType([
    StructField("id_cliente",         StringType(), True),
    StructField("nombre_completo",    StringType(), True),
    StructField("fecha_nacimiento",   DateType(),  True),
    StructField("genero",             StringType(), True),
    StructField("ciudad",             StringType(), True),
    StructField("segmento_cliente",   StringType(), True),
    StructField("fecha_alta_cliente", DateType(),  True),
])

if TABLE == "clientes_transacciones":
    print("clientes_transacciones <--")
    df = (
        df_raw.select(
            F.col("id_cliente").cast(StringType()),
            F.to_date("fecha_transaccion", "yyyy-MM-dd").alias("fecha_transaccion"),
            F.col("tipo_transaccion").cast(StringType()),
            F.regexp_replace("monto", r"[^\d\.-]", "").alias("monto_str"),
            F.regexp_replace("saldo_cuenta", r"[^\d\.-]", "").alias("saldo_str"),
            F.col("canal").cast(StringType()),
            F.col("fecha_rutina"),
        )
        .withColumn("monto",        F.col("monto_str").cast(DecimalType(18,2)))
        .withColumn("saldo_cuenta", F.col("saldo_str").cast(DecimalType(18,2)))
        .drop("monto_str", "saldo_str")
        .select([f.name for f in SCHEMA_UDV_TRANSACCIONES.fields] + ["fecha_rutina"])
    )

elif TABLE == "maestra_clientes":
    print("maestra_clientes <--")
    df = (
        df_raw.select(
            F.col("id_cliente").cast(StringType()),
            F.col("nombre_completo").cast(StringType()),
            F.to_date("fecha_nacimiento", "yyyy-MM-dd").alias("fecha_nacimiento"),
            F.col("genero").cast(StringType()),
            F.col("ciudad").cast(StringType()),
            F.col("segmento_cliente").cast(StringType()),
            F.to_date("fecha_alta_cliente", "yyyy-MM-dd").alias("fecha_alta_cliente"),
            F.col("fecha_rutina"),
        )
        .select([f.name for f in SCHEMA_UDV_MAESTRA.fields] + ["fecha_rutina"])
    )

else:
    raise ValueError(f"TABLE_NAME '{TABLE}' no soportado.")

print("cantidad: ",df.count())

udv_out = f"{ARGS['S3_OUTPUT_BASE'].rstrip('/')}/{TABLE}"
(
    df.repartition("fecha_rutina")
      .write.mode("overwrite").format("parquet")
      .partitionBy("fecha_rutina").option("compression", "snappy")
      .save(udv_out)
)
logger.info(f"UDV '{TABLE}' escrito en: {udv_out}/fecha_rutina={ARGS['FECHA_RUTINA']}/")

glue = boto3.client("glue", region_name=ARGS["AWS_REGION"])
try:
    glue.start_crawler(Name=ARGS["CRAWLER_NAME_UDV"])
    logger.info(f"Crawler UDV '{ARGS['CRAWLER_NAME_UDV']}' iniciado.")
except glue.exceptions.CrawlerRunningException:
    logger.warn(f"Crawler UDV '{ARGS['CRAWLER_NAME_UDV']}' ya estaba en ejecución.")
except Exception as e:
    logger.error(f"No se pudo iniciar el crawler UDV: {e}")
    raise

job.commit()
