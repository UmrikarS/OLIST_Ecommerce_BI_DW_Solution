import snowflake.connector

def setup_snowflake_database(snowflake_account, snowflake_user, snowflake_password, snowflake_warehouse, snowflake_database, snowflake_schema):
    """
    Connects to Snowflake and creates the warehouse, database, schema, and tables.
    """
    conn = None
    cursor = None
    try:
        print("Attempting to connect to Snowflake to set up database...")
        conn = snowflake.connector.connect(
            account=snowflake_account,
            user=snowflake_user,
            password=snowflake_password
            # Do not specify warehouse, database, schema initially for creation
        )

        print("Successfully connected to Snowflake!")
        cursor = conn.cursor()

        # SQL statements to create warehouse, database, and schema if they don't exist
        create_warehouse_sql = f"CREATE WAREHOUSE IF NOT EXISTS {snowflake_warehouse} WITH WAREHOUSE_SIZE = 'SMALL';"
        create_database_sql = f"CREATE DATABASE IF NOT EXISTS {snowflake_database};"
        create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {snowflake_schema};"

        # Execute warehouse creation
        print(f"Creating warehouse: {snowflake_warehouse}...")
        cursor.execute(create_warehouse_sql)
        print(f"Warehouse {snowflake_warehouse} created or already exists.")

        # Use the newly created warehouse
        use_warehouse_sql = f"USE WAREHOUSE {snowflake_warehouse};"
        print(f"Using warehouse: {snowflake_warehouse}...")
        cursor.execute(use_warehouse_sql)
        print(f"Warehouse {snowflake_warehouse} is now in use.")

        # Execute database and schema creation
        print(f"Creating database: {snowflake_database}...")
        cursor.execute(create_database_sql)
        print(f"Database {snowflake_database} created or already exists.")

        print(f"Creating schema: {snowflake_schema}...")
        cursor.execute(create_schema_sql)
        print(f"Schema {snowflake_schema} created or already exists.")

        # Use the newly created database and schema
        cursor.execute(f"USE DATABASE {snowflake_database};")
        cursor.execute(f"USE SCHEMA {snowflake_schema};")

        # SQL statements to create tables with constraints
        create_dim_customers_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Customers (
            customer_id VARCHAR PRIMARY KEY,
            customer_unique_id VARCHAR,
            customer_zip_code_prefix VARCHAR,
            customer_city VARCHAR,
            customer_state VARCHAR
        );
        """
        create_dim_products_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Products (
            product_id VARCHAR PRIMARY KEY,
            product_category_name VARCHAR,
            product_name_length NUMBER,
            product_description_length NUMBER,
            product_photos_qty NUMBER,
            product_weight_g NUMBER,
            product_length_cm NUMBER,
            product_height_cm NUMBER,
            product_width_cm NUMBER,
            product_category_name_english VARCHAR
        );
        """
        create_dim_sellers_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Sellers (
            seller_id VARCHAR PRIMARY KEY,
            seller_zip_code_prefix VARCHAR,
            seller_city VARCHAR,
            seller_state VARCHAR
        );
        """
        create_dim_orders_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Orders (
            order_id VARCHAR PRIMARY KEY,
            customer_id VARCHAR,
            order_status VARCHAR,
            order_purchase_timestamp TIMESTAMP,
            order_approved_at TIMESTAMP,
            order_delivered_carrier_date TIMESTAMP,
            order_delivered_customer_date TIMESTAMP,
            order_estimated_delivery_date TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES Dim_Customers(customer_id)
        );
        """
        create_dim_payments_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Payments (
            order_id VARCHAR,
            payment_sequential NUMBER,
            payment_type VARCHAR,
            payment_installments NUMBER,
            payment_value DECIMAL(10, 2),
            PRIMARY KEY (order_id, payment_sequential),
            FOREIGN KEY (order_id) REFERENCES Dim_Orders(order_id)
        );
        """
        create_dim_reviews_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Reviews (
            review_id VARCHAR PRIMARY KEY,
            order_id VARCHAR,
            review_score NUMBER,
            review_comment_title VARCHAR,
            review_comment_message VARCHAR,
            review_creation_date TIMESTAMP,
            review_answer_timestamp TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES Dim_Orders(order_id)
        );
        """
        # Dim_Geolocation is a standalone dimension in this schema design
        create_dim_geolocation_sql = """
        CREATE TABLE IF NOT EXISTS Dim_Geolocation (
            geolocation_zip_code_prefix VARCHAR,
            geolocation_lat FLOAT,
            geolocation_lng FLOAT,
            geolocation_city VARCHAR,
            geolocation_state VARCHAR,
            PRIMARY KEY (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng)
        );
        """
        create_fact_order_items_sql = """
        CREATE TABLE IF NOT EXISTS Fact_Order_Items (
            order_id VARCHAR,
            order_item_id NUMBER,
            product_id VARCHAR,
            seller_id VARCHAR,
            shipping_deadline TIMESTAMP,
            price DECIMAL(10, 2),
            freight_value DECIMAL(10, 2),
            PRIMARY KEY (order_id, order_item_id),
            FOREIGN KEY (order_id) REFERENCES Dim_Orders(order_id),
            FOREIGN KEY (product_id) REFERENCES Dim_Products(product_id),
            FOREIGN KEY (seller_id) REFERENCES Dim_Sellers(seller_id)
        );
        """
        print("Creating tables...")
        cursor.execute(create_dim_customers_sql)
        print("Table Dim_Customers created or already exists.")

        cursor.execute(create_dim_products_sql)
        print("Table Dim_Products created or already exists.")

        cursor.execute(create_dim_sellers_sql)
        print("Table Dim_Sellers created or already exists.")

        # Create Dim_Orders after Dim_Customers
        cursor.execute(create_dim_orders_sql)
        print("Table Dim_Orders created or already exists.")

        # Create Dim_Payments and Dim_Reviews after Dim_Orders
        cursor.execute(create_dim_payments_sql)
        print("Table Dim_Payments created or already exists.")

        cursor.execute(create_dim_reviews_sql)
        print("Table Dim_Reviews created or already exists.")

        # Create Dim_Geolocation (no dependencies on other dimension tables)
        cursor.execute(create_dim_geolocation_sql)
        print("Table Dim_Geolocation created or already exists.")

        # Create Fact_Order_Items after its dependent dimension tables
        cursor.execute(create_fact_order_items_sql)
        print("Table Fact_Order_Items created or already exists.")

        # Create an internal stage for data loading if it doesn't exist
        create_stage_sql = f"CREATE OR REPLACE STAGE {snowflake_database}.{snowflake_schema}.csv_upload_stage;"
        print(f"Creating internal stage: csv_upload_stage...")
        cursor.execute(create_stage_sql)
        print(f"Internal stage csv_upload_stage created or already exists.")

        conn.commit()
        print("Snowflake setup committed successfully.")

    except Exception as e:
        print(f"An error occurred during Snowflake setup: {e}")
        if conn:
            conn.rollback() # Rollback changes in case of error
            print("Changes rolled back during setup.")

    finally:
        if cursor:
            cursor.close()
            print("Snowflake cursor closed.")
        if conn:
            conn.close()
            print("Snowflake connection closed after setup.")