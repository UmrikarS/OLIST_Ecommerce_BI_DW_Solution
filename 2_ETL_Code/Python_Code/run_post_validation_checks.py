import snowflake.connector
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_post_validation_checks(snowflake_account, snowflake_user, snowflake_password, snowflake_warehouse, snowflake_database, snowflake_schema):
    """
    Connects to Snowflake and runs post-validation checks on the loaded data.

    Args:
      snowflake_account: Snowflake account identifier.
      snowflake_user: Snowflake username.
      snowflake_password: Snowflake password.
      snowflake_warehouse: The Snowflake warehouse to use.
      snowflake_database: The Snowflake database.
      snowflake_schema: The Snowflake schema.
    """
    conn = None
    cursor = None
    try:
        logging.info("Attempting to connect to Snowflake for post-validation checks...")
        conn = snowflake.connector.connect(
            account=snowflake_account,
            user=snowflake_user,
            password=snowflake_password,
            warehouse=snowflake_warehouse,
            database=snowflake_database,
            schema=snowflake_schema
        )

        logging.info("Successfully connected to Snowflake for post-validation checks.")
        cursor = conn.cursor()

        print("\n--- Starting Post-Validation Checks ---")

        # 1. Verify Row Counts (Example - you'll need to compare with source counts)
        print("\n1. Verifying Row Counts...")
        table_row_counts_query = """
        SELECT table_name, row_count
        FROM information_schema.tables
        WHERE table_schema = UPPER('{snowflake_schema}')
        ORDER BY table_name;
        """.format(snowflake_schema=snowflake_schema)

        cursor.execute(table_row_counts_query)
        row_counts = cursor.fetchall()
        print("Row counts in Snowflake tables:")
        for row in row_counts:
            print(f"  - {row[0]}: {row[1]} rows")
        print("Note: Compare these counts with your source data counts.")

        # 2. Data Quality Checks (Nulls, Duplicates, Data Ranges)
        print("\n2. Running Data Quality Checks...")

        # Check for null values in Primary Key columns
        print("\n   - Checking for null values in Primary Key columns:")
        pk_null_check_query = """
        SELECT 'Dim_Customers', 'customer_id', COUNT(*) FROM Dim_Customers WHERE customer_id IS NULL
        UNION ALL
        SELECT 'Dim_Products', 'product_id', COUNT(*) FROM Dim_Products WHERE product_id IS NULL
        UNION ALL
        SELECT 'Dim_Sellers', 'seller_id', COUNT(*) FROM Dim_Sellers WHERE seller_id IS NULL
        UNION ALL
        SELECT 'Dim_Orders', 'order_id', COUNT(*) FROM Dim_Orders WHERE order_id IS NULL
        UNION ALL
        SELECT 'Dim_Payments', 'order_id', COUNT(*) FROM Dim_Payments WHERE order_id IS NULL -- Check part of composite PK
        UNION ALL
        SELECT 'Dim_Payments', 'payment_sequential', COUNT(*) FROM Dim_Payments WHERE payment_sequential IS NULL -- Check part of composite PK
        UNION ALL
        SELECT 'Dim_Reviews', 'review_id', COUNT(*) FROM Dim_Reviews WHERE review_id IS NULL
        UNION ALL
        SELECT 'Dim_Geolocation', 'geolocation_zip_code_prefix', COUNT(*) FROM Dim_Geolocation WHERE geolocation_zip_code_prefix IS NULL -- Check part of composite PK
        UNION ALL
        SELECT 'Dim_Geolocation', 'geolocation_lat', COUNT(*) FROM Dim_Geolocation WHERE geolocation_lat IS NULL -- Check part of composite PK
        UNION ALL
        SELECT 'Dim_Geolocation', 'geolocation_lng', COUNT(*) FROM Dim_Geolocation WHERE geolocation_lng IS NULL -- Check part of composite PK
        UNION ALL
        SELECT 'Fact_Order_Items', 'order_id', COUNT(*) FROM Fact_Order_Items WHERE order_id IS NULL -- Check part of composite PK
        UNION ALL
        SELECT 'Fact_Order_Items', 'order_item_id', COUNT(*) FROM Fact_Order_Items WHERE order_item_id IS NULL; -- Check part of composite PK
        """
        cursor.execute(pk_null_check_query)
        pk_null_results = cursor.fetchall()
        for row in pk_null_results:
            if row[2] > 0:
                print(f"     - WARNING: Table '{row[0]}', Column '{row[1]}' has {row[2]} null values.")
            else:
                print(f"     - Table '{row[0]}', Column '{row[1]}' has no null values.")

        # Check for duplicate records based on Primary Keys
        print("\n   - Checking for duplicate records based on Primary Keys:")
        duplicate_check_queries = [
            ("""SELECT 'Dim_Customers' AS table_name, customer_id AS pk_value, COUNT(*) AS duplicate_count FROM Dim_Customers GROUP BY customer_id HAVING COUNT(*) > 1;""", ['Dim_Customers', 'customer_id']),
            ("""SELECT 'Dim_Products' AS table_name, product_id AS pk_value, COUNT(*) AS duplicate_count FROM Dim_Products GROUP BY product_id HAVING COUNT(*) > 1;""", ['Dim_Products', 'product_id']),
            ("""SELECT 'Dim_Sellers' AS table_name, seller_id AS pk_value, COUNT(*) AS duplicate_count FROM Dim_Sellers GROUP BY seller_id HAVING COUNT(*) > 1;""", ['Dim_Sellers', 'seller_id']),
            ("""SELECT 'Dim_Orders' AS table_name, order_id AS pk_value, COUNT(*) AS duplicate_count FROM Dim_Orders GROUP BY order_id HAVING COUNT(*) > 1;""", ['Dim_Orders', 'order_id']),
            ("""SELECT 'Dim_Payments' AS table_name, order_id, payment_sequential, COUNT(*) AS duplicate_count FROM Dim_Payments GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1;""", ['Dim_Payments', 'order_id', 'payment_sequential']), # Composite PK
            ("""SELECT 'Dim_Reviews' AS table_name, review_id AS pk_value, COUNT(*) AS duplicate_count FROM Dim_Reviews GROUP BY review_id HAVING COUNT(*) > 1;""", ['Dim_Reviews', 'review_id']),
            ("""SELECT 'Dim_Geolocation' AS table_name, geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, COUNT(*) AS duplicate_count FROM Dim_Geolocation GROUP BY geolocation_zip_code_prefix, geolocation_lat, geolocation_lng HAVING COUNT(*) > 1;""", ['Dim_Geolocation', 'geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng']), # Composite PK
            ("""SELECT 'Fact_Order_Items' AS table_name, order_id, order_item_id, COUNT(*) AS duplicate_count FROM Fact_Order_Items GROUP BY order_id, order_item_id HAVING COUNT(*) > 1;""", ['Fact_Order_Items', 'order_id', 'order_item_id']) # Composite PK
        ]

        for query, pk_cols in duplicate_check_queries:
            cursor.execute(query)
            duplicate_results = cursor.fetchall()
            if duplicate_results:
                table_name = duplicate_results[0][0] # Get table name from the first result row
                print(f"     - WARNING: Duplicates found in table '{table_name}' based on PK columns {pk_cols}. First few duplicates:")
                for row in duplicate_results[:5]: # Print up to 5 duplicate examples
                     print(f"       - {row}")
            else:
                print(f"     - No duplicates found for table '{pk_cols[0]}'.")

        # Check for non-positive values in price and freight_value in Fact_Order_Items
        print("\n   - Checking for non-positive price/freight values in Fact_Order_Items:")
        price_freight_check_query = """
        SELECT 'Fact_Order_Items' AS table_name, 'price' AS column_name, COUNT(*) AS invalid_count FROM Fact_Order_Items WHERE price < 0
        UNION ALL
        SELECT 'Fact_Order_Items', 'freight_value', COUNT(*) FROM Fact_Order_Items WHERE freight_value < 0;
        """
        cursor.execute(price_freight_check_query)
        price_freight_results = cursor.fetchall()
        for row in price_freight_results:
            if row[2] > 0:
                print(f"     - WARNING: Table '{row[0]}', Column '{row[1]}' has {row[2]} non-positive values.")
            else:
                print(f"     - Table '{row[0]}', Column '{row[1]}' has no non-positive values.")

        # Check for invalid review scores
        print("\n   - Checking for invalid review scores in Dim_Reviews:")
        invalid_review_score_query = """
        SELECT 'Dim_Reviews' AS table_name, 'review_score' AS column_name, COUNT(*) AS invalid_count
        FROM Dim_Reviews
        WHERE review_score < 1 OR review_score > 5;
        """
        cursor.execute(invalid_review_score_query)
        invalid_review_results = cursor.fetchall()
        for row in invalid_review_results:
            if row[2] > 0:
                 print(f"     - WARNING: Table '{row[0]}', Column '{row[1]}' has {row[2]} invalid scores (expected 1-5).")
            else:
                 print(f"     - Table '{row[0]}', Column '{row[1]}' has no invalid scores.")


        # 3. Referential Integrity Checks (Orphaned Records)
        print("\n3. Running Referential Integrity Checks (checking for orphaned records)...")

        # Check for order_ids in Fact_Order_Items that do not exist in Dim_Orders
        print("   - Checking for orphaned records in Fact_Order_Items (order_id)...")
        orphan_order_check_query = """
        SELECT fo.order_id
        FROM Fact_Order_Items fo
        LEFT JOIN Dim_Orders d ON fo.order_id = d.order_id
        WHERE d.order_id IS NULL
        LIMIT 10; -- Limit results as there could be many
        """
        cursor.execute(orphan_order_check_query)
        orphan_order_results = cursor.fetchall()
        if orphan_order_results:
            print(f"     - WARNING: Found {len(orphan_order_results)} orphaned order_ids in Fact_Order_Items (first 10):")
            for row in orphan_order_results:
                print(f"       - {row[0]}")
        else:
            print("     - No orphaned order_ids found in Fact_Order_Items.")

        # Check for product_ids in Fact_Order_Items that do not exist in Dim_Products
        print("   - Checking for orphaned records in Fact_Order_Items (product_id)...")
        orphan_product_check_query = """
        SELECT fo.product_id
        FROM Fact_Order_Items fo
        LEFT JOIN Dim_Products dp ON fo.product_id = dp.product_id
        WHERE dp.product_id IS NULL
        LIMIT 10; -- Limit results as there could be many
        """
        cursor.execute(orphan_product_check_query)
        orphan_product_results = cursor.fetchall()
        if orphan_product_results:
            print(f"     - WARNING: Found {len(orphan_product_results)} orphaned product_ids in Fact_Order_Items (first 10):")
            for row in orphan_product_results:
                print(f"       - {row[0]}")
        else:
            print("     - No orphaned product_ids found in Fact_Order_Items.")

        # Check for seller_ids in Fact_Order_Items that do not exist in Dim_Sellers
        print("   - Checking for orphaned records in Fact_Order_Items (seller_id)...")
        orphan_seller_check_query = """
        SELECT fo.seller_id
        FROM Fact_Order_Items fo
        LEFT JOIN Dim_Sellers ds ON fo.seller_id = ds.seller_id
        WHERE ds.seller_id IS NULL
        LIMIT 10; -- Limit results as there could be many
        """
        cursor.execute(orphan_seller_check_query)
        orphan_seller_results = cursor.fetchall()
        if orphan_seller_results:
            print(f"     - WARNING: Found {len(orphan_seller_results)} orphaned seller_ids in Fact_Order_Items (first 10):")
            for row in orphan_seller_results:
                print(f"       - {row[0]}")
        else:
            print("     - No orphaned seller_ids found in Fact_Order_Items.")


        print("\n--- Post-Validation Checks Finished ---")


    except Exception as e:
        logging.error(f"An error occurred during post-validation checks: {e}", exc_info=True)
        print(f"An error occurred during post-validation checks: {e}")


    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
            logging.info("Snowflake cursor closed.")
        if conn:
            conn.close()
            logging.info("Snowflake connection closed after post-validation checks.")

# Define Snowflake connection details using placeholder environment variables
# In a real-world scenario, these would be set securely in your environment
# or using a secrets management tool.
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "WZATSRO-TP51811")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "***********")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "************")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "MBI_DW")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "OLIST_DB")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "OLIST_SCHEMA")

# Run the post-validation checks
if __name__ == "__main__":
    run_post_validation_checks(SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA)