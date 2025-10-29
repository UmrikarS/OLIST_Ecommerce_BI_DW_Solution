import snowflake.connector
import os

def download_all_tables_to_csv(snowflake_account, snowflake_user, snowflake_password, snowflake_warehouse, snowflake_database, snowflake_schema, output_dir="downloaded_tables"):
    """
    Connects to Snowflake, downloads all tables and views from a schema, and saves them as CSV files.

    Args:
      snowflake_account: Snowflake account identifier.
      snowflake_user: Snowflake username.
      snowflake_password: Snowflake password.
      snowflake_warehouse: The Snowflake warehouse to use.
      snowflake_database: The Snowflake database.
      snowflake_schema: The Snowflake schema.
      output_dir: The directory to save the downloaded CSV files. Defaults to "downloaded_tables".
    """
    conn = None
    cursor = None
    try:
        print(f"Attempting to connect to Snowflake to download tables and views from schema {snowflake_schema}...")
        conn = snowflake.connector.connect(
            account=snowflake_account,
            user=snowflake_user,
            password=snowflake_password,
            warehouse=snowflake_warehouse,
            database=snowflake_database,
            schema=snowflake_schema
        )

        print("Successfully connected to Snowflake.")
        cursor = conn.cursor()

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        # Get list of tables and views in the schema
        list_objects_query = f"""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = UPPER('{snowflake_schema}')
        AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_name;
        """.format(snowflake_schema=snowflake_schema)

        print(f"\nExecuting query to list tables and views: {list_objects_query}")
        cursor.execute(list_objects_query)
        objects_to_download = cursor.fetchall() # Fetch both name and type

        if not objects_to_download:
            print(f"No tables or views found in schema {snowflake_schema}.")
            return

        print(f"\nFound {len(objects_to_download)} tables and views in schema {snowflake_schema}:")
        for obj in objects_to_download:
            print(f"  - {obj[0]} ({obj[1]})")


        # Download each object (table or view)
        for obj_name, obj_type in objects_to_download:
            try:
                print(f"\nDownloading data from {obj_type}: {obj_name}...")
                # Construct the SQL query to select all data from the object
                # Enclose object name in double quotes to handle potential case sensitivity
                query = f'SELECT * FROM "{snowflake_database}"."{snowflake_schema}"."{obj_name}";'


                cursor.execute(query)

                # Use fetch_pandas_all() to directly load data into a pandas DataFrame
                df = cursor.fetch_pandas_all()

                if df is not None and not df.empty:
                    # Define output file path
                    output_csv_path = os.path.join(output_dir, f"{obj_name.lower()}.csv") # Save with lowercase name
                    df.to_csv(output_csv_path, index=False)
                    print(f"Successfully downloaded {len(df)} rows and saved to {output_csv_path}")
                else:
                    print(f"{obj_type} {obj_name} is empty or could not be fetched into DataFrame. Skipping CSV creation.")

            except Exception as e:
                print(f"An error occurred while downloading data from {obj_type} {obj_name}: {e}")
                # Continue to the next object

    except Exception as e:
        print(f"An error occurred during the overall download process: {e}")

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
            print("Snowflake cursor closed.")
        if conn:
            conn.close()
            print("Snowflake connection closed.")

# Define Snowflake connection details using placeholder environment variables
# Replace with your actual Snowflake account details or set environment variables
snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT", "WZATSRO-TP51811")
snowflake_user = os.getenv("SNOWFLAKE_USER", "**********")
snowflake_password = os.getenv("SNOWFLAKE_PASSWORD", "**********")
snowflake_warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "MBI_DW")
snowflake_database = os.getenv("SNOWFLAKE_DATABASE", "OLIST_DB")
snowflake_schema = os.getenv("SNOWFLAKE_SCHEMA", "OLIST_SCHEMA")

# Specify the output directory
output_directory = "downloaded_snowflake_tables"

# Download all tables
download_all_tables_to_csv(
    snowflake_account,
    snowflake_user,
    snowflake_password,
    snowflake_warehouse,
    snowflake_database,
    snowflake_schema,
    output_directory
)