import snowflake.connector
import os
import io
import logging

def load_data_to_snowflake(transformed_data, snowflake_account, snowflake_user, snowflake_password, snowflake_warehouse, snowflake_database, snowflake_schema):
    """
    Loads transformed data from pandas DataFrames into Snowflake tables using COPY INTO command.

    Args:
      transformed_data: A dictionary of cleaned and transformed pandas DataFrames.
      snowflake_account: Snowflake account identifier.
      snowflake_user: Snowflake username.
      snowflake_password: Snowflake password.
      snowflake_warehouse: The Snowflake warehouse to use.
      snowflake_database: The Snowflake database to load data into.
      snowflake_schema: The Snowflake schema to load data into.
    """
    conn = None
    cursor = None
    try:
        logging.info("Attempting to connect to Snowflake for loading...")
        conn = snowflake.connector.connect(
            account=snowflake_account,
            user=snowflake_user,
            password=snowflake_password,
            warehouse=snowflake_warehouse,
            database=snowflake_database,
            schema=snowflake_schema
        )

        logging.info("Successfully connected to Snowflake for loading.")
        cursor = conn.cursor()

        # Define the loading order based on foreign key dependencies
        loading_order = [
            'dim_customers',
            'dim_products',
            'dim_sellers',
            'dim_orders', # Depends on dim_customers
            'dim_payments', # Depends on dim_orders
            'dim_reviews', # Depends on dim_orders
            'dim_geolocation', # No dependencies in this schema
            'fact_order_items' # Depends on dim_orders, dim_products, dim_sellers
        ]

        for table_name in loading_order:
            if table_name in transformed_data and transformed_data[table_name] is not None:
                df = transformed_data[table_name]
                logging.info(f"Loading data into {table_name} using COPY INTO...")

                # Convert DataFrame to CSV format in memory
                csv_buffer = io.StringIO()
                # Ensure column names are uppercase for Snowflake mapping
                df.columns = df.columns.str.upper()
                df.to_csv(csv_buffer, index=False, header=True)
                csv_buffer.seek(0) # Reset buffer position to the beginning

                # Define the stage name and file path within the stage
                stage_name = f'@{snowflake_database}.{snowflake_schema}.csv_upload_stage'
                file_path = f'{table_name.upper()}/{table_name.upper()}_data.csv'

                # Put the data into the internal stage
                temp_file_path = f'/tmp/{table_name.upper()}_data.csv'
                with open(temp_file_path, 'w') as f:
                    f.write(csv_buffer.getvalue())

                put_sql = f"PUT file://{temp_file_path} {stage_name}/{table_name.upper()}/ auto_compress=true;"
                logging.info(f"Executing PUT command for {table_name.upper()}...")
                cursor.execute(put_sql)
                logging.info(f"Data put into stage {stage_name}/{table_name.upper()}/")

                # Construct the COPY INTO statement
                copy_sql = f"""
                COPY INTO {snowflake_database}.{snowflake_schema}.{table_name.upper()}
                FROM {stage_name}/{file_path}
                FILE_FORMAT = (TYPE = CSV FIELD_DELIMITER = ',' SKIP_HEADER = 1 NULL_IF = ('', 'NULL'))
                ON_ERROR = 'continue'; -- Continue loading even if some records fail
                """
                logging.info(f"Executing COPY INTO command for {table_name.upper()}...")
                cursor.execute(copy_sql)
                logging.info(f"Data copied into table {table_name.upper()}.")

                # Clean up the temporary local file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logging.info(f"Removed temporary file {temp_file_path}")

        # Commit the changes
        conn.commit()
        logging.info("Changes committed successfully.")

    except Exception as e:
        logging.error(f"An error occurred during data loading: {e}", exc_info=True)
        if conn:
            conn.rollback() # Rollback changes in case of error
            logging.info("Changes rolled back.")

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
            logging.info("Snowflake cursor closed.")
        if conn:
            conn.close()
            logging.info("Snowflake connection closed after loading.")