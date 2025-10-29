import os
import logging
from extract_data import extract_data
from clean_and_transform_data import clean_and_transform_data
from load_data_to_snowflake import load_data_to_snowflake
from snowflake_setup import setup_snowflake_database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the file paths for the source CSV files
csv_file_paths = {
    'customers': '/content/olist_customers_dataset.csv',
    'geolocation': '/content/olist_geolocation_dataset.csv',
    'order_items': '/content/olist_order_items_dataset.csv',
    'order_payments': '/content/olist_order_payments_dataset.csv',
    'order_reviews': '/content/olist_order_reviews_dataset.csv',
    'orders': '/content/olist_orders_dataset.csv',
    'products': '/content/olist_products_dataset.csv',
    'sellers': '/content/olist_sellers_dataset.csv',
    'product_category_translation': '/content/product_category_name_translation.csv'
}

# Define Snowflake connection details using placeholder environment variables
# In a real-world scenario, these would be set securely in your environment
# or using a secrets management tool.
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "WZATSRO-TP51811")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "**********")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "*********")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "MBI_DW")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "OLIST_DB")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "OLIST_SCHEMA")

# --- ETL Pipeline Execution ---

if __name__ == "__main__":
    logging.info("Starting ETL pipeline...")

    try:
        # Set up Snowflake database, warehouse, schema, and tables
        # logging.info("Setting up Snowflake database...")
        setup_snowflake_database(SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA)

        # 1. Extraction
        logging.info("Step 1: Extracting data...")
        raw_data = extract_data(csv_file_paths)

        # Check if extraction was successful for all files
        if any(df is None for df in raw_data.values()):
            logging.error("ETL pipeline halted due to extraction errors.")
        else:
            # 2. Cleaning and Transformation
            logging.info("Step 2: Cleaning and transforming data...")
            transformed_data = clean_and_transform_data(raw_data)

            # Check if transformation was successful and transformed_data is not empty
            if transformed_data:
                # 3. Loading
                logging.info("Step 3: Loading data into Snowflake...")
                load_data_to_snowflake(transformed_data, SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA)

                logging.info("ETL pipeline finished successfully.")
            else:
                logging.error("ETL pipeline halted due to transformation errors or no data to load.")

    except Exception as e:
        logging.error(f"An unhandled error occurred during ETL pipeline execution: {e}", exc_info=True)
        print(f"An unhandled error occurred during ETL pipeline execution: {e}") # Also print to stdout for immediate visibility