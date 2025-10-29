import boto3
import json
import os
from datetime import datetime

glue = boto3.client('glue')

def lambda_handler(event, context):

    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        size = record['s3']['object'].get('size', 0)

    except (KeyError, IndexError) as e:
        error_msg = f"Invalid S3 event structure: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg})
        }
    
    # Validate CSV extension
    if not key.endswith('.csv'):
        error_msg = f"Invalid file type. Expected .csv, got: {key}"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg})
        }
    

    file_name = key.split('/')[-1]
    

    valid_files = ['clientes_transacciones.csv', 'maestra_clientes.csv']
    if file_name not in valid_files:
        error_msg = f"Invalid file name: {file_name}. Expected: {', '.join(valid_files)}"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg})
        }
    
    glue_job_name = os.environ.get('GLUE_JOB_NAME', 'bbva-etl-transacciones-rdv')
    output_base = os.environ.get('S3_OUTPUT_BASE', 's3://bbva-rdv/data/')
    crawler_name = os.environ.get('CRAWLER_NAME', 'crw_rdv_clientes_transacciones')
    glue_region = os.environ.get('GLUE_REGION', 'us-east-2')
    
    fecha_rutina = datetime.now().strftime('%Y-%m-%d')
    
    if file_name == 'clientes_transacciones.csv':
        output_path = f"{output_base}clientes_transacciones/"
    elif file_name == 'maestra_clientes.csv':
        output_path = f"{output_base}maestra_clientes/"
    else:
        output_path = output_base
    
    print(f"🔧 Configuration:")
    print(f"   Job Name: {glue_job_name}")
    print(f"   Output: {output_path}")
    print(f"   Crawler: {crawler_name}")
    print(f"   Region: {glue_region}")
    print(f"   Fecha Rutina: {fecha_rutina}")
    

    job_arguments = {
        '--S3_INPUT': f"s3://{bucket}/{key}",
        '--S3_OUTPUT_BASE': output_path,
        '--FECHA_RUTINA': fecha_rutina,
        '--CRAWLER_NAME': crawler_name,
        '--AWS_REGION': glue_region, 
        '--FILE_NAME': file_name
    }
    
    print(f"📋 Job Arguments: {json.dumps(job_arguments, indent=2)}")
    
    # Start Glue Job
    try:
        response = glue.start_job_run(
            JobName=glue_job_name,
            Arguments=job_arguments
        )
        
        job_run_id = response['JobRunId']
        print(f"Glue Job started successfully!")
        print(f"Job Run ID: {job_run_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ETL job started successfully',
                'job_name': glue_job_name,
                'job_run_id': job_run_id,
                'input_file': f"s3://{bucket}/{key}",
                'output_path': output_path,
                'fecha_rutina': fecha_rutina,
                'file_type': file_name
            })
        }
        
    except Exception as e:
        error_msg = f"Failed to start Glue Job: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'job_name': glue_job_name
            })
        }