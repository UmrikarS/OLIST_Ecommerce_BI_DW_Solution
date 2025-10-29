import pandas as pd
import logging
import unicodedata

def clean_and_transform_data(raw_data):
    """
    Cleans and transforms raw dataframes according to the snowflake schema design.
    Includes enhanced data validation checks and prepares data for fact table.

    Args:
      raw_data: A dictionary of raw pandas DataFrames extracted from CSVs.

    Returns:
      A dictionary of cleaned and transformed pandas DataFrames ready for loading.
      Returns an empty dictionary if critical dataframes are missing or transformation fails.
    """
    transformed_data = {}
    validation_errors = []
    logging.info("Starting data cleaning and transformation...")

    # --- Data Cleaning and Transformation ---
    try:

        # The lambda function
        strip_accents_lambda = lambda text: ''.join(
        c for c in unicodedata.normalize('NFKD', str(text))
        if not unicodedata.combining(c)
        )

        # Dim_Customer_Location
        if 'customers' in raw_data and raw_data['customers'] is not None:
            dim_customer_df = raw_data['customers']
            print(dim_customer_df.head())
            print(dim_customer_df.info())
            print(dim_customer_df.describe())
            print(dim_customer_df.isnull().sum())
            print(dim_customer_df[dim_customer_df.duplicated()])
            # No duplicates, missing values found in the dataset
            transformed_data['dim_customers'] = dim_customer_df
            logging.info("Cleaned and transformed Dim_Customer.")
        else:
            logging.warning("Raw 'customers' data not available for Dim_Customer transformation.")

        # Dim_Products
        if 'products' in raw_data and raw_data['products'] is not None:
            dim_products_df = raw_data['products']
            print(dim_products_df.head())
            print(dim_products_df.info())
            print(dim_products_df.describe())
            print(dim_products_df.isnull().sum())
            print(dim_products_df[dim_products_df.duplicated()])

            # products joined with product_category to get them in English
            dim_products_df.rename(columns={
                "product_name_lenght" : "product_name_length",
                "product_description_lenght" : "product_description_length"},
                                   inplace=True)

            # Removes product with missing product names
            missing_product_names = dim_products_df[dim_products_df['product_category_name'].isna()]
            dim_products_df.drop(missing_product_names.index, inplace=True)
            numerical_cols = ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']
            for col in numerical_cols:
                median_value = dim_products_df[col].median()
                dim_products_df[col].fillna({col: median_value})
                dim_products_df[col] = dim_products_df[col].astype(float)

            # Removes product with 0 weight, length, height, width
            dim_products_df = dim_products_df[dim_products_df['product_weight_g'] > 0]
            dim_products_df = dim_products_df[(dim_products_df['product_length_cm'] > 0)  &
                                              (dim_products_df['product_height_cm'] > 0) &
                                              (dim_products_df['product_width_cm'] > 0)]

            # Check values after removing missing product
            print(dim_products_df.info())
            print(dim_products_df.isnull().sum())
            print(dim_products_df.nunique())

            # In order to translate the product name to english name find the
            # unique name and merge with the product_category_translation
            products_name_spanish = dim_products_df['product_category_name'].unique()
            print(products_name_spanish)

            # Get the product categories english name
            dim_product_category_df = raw_data['product_category_translation']

            print(dim_product_category_df.info())
            product_names_english = dim_product_category_df['product_category_name'].unique()
            print(product_names_english)

            # Re-check for any missing categories
            missing_names = set(products_name_spanish) - set(product_names_english)
            print("Missing categories:", missing_names)

            add_missing = pd.DataFrame({
                'product_category_name': ['portateis_cozinha_e_preparadores_de_alimentos', 'pc_gamer'],
                'product_category_name_english': ['portable_kitchen_and_food_preparers', 'pc_gamer']})
            dim_product_category_df = pd.concat([dim_product_category_df, add_missing], ignore_index=True)

            product_names_english = dim_product_category_df['product_category_name'].unique()
            print(product_names_english)

            # Ensure no duplicate categories remain after adding new translations
            dim_product_category_df = dim_product_category_df.drop_duplicates(subset=['product_category_name']).reset_index(drop=True)

            dim_products_df = dim_products_df.merge(dim_product_category_df, on='product_category_name', how='left')
            print(dim_products_df.head(10))

            # Check the dataframe after merging
            print(dim_products_df.info())

            transformed_data['dim_products'] = dim_products_df
            logging.info("Cleaned and transformed Dim_Products.")
        else:
             logging.warning("Raw 'products' data not available for Dim_Products transformation.")

        # Dim_Sellers
        if 'sellers' in raw_data and raw_data['sellers'] is not None:
            # Analyze the data
            dim_sellers_df = raw_data['sellers']
            print(dim_sellers_df.head())
            print(dim_sellers_df.info())
            print(dim_sellers_df.describe())
            print(dim_sellers_df.isnull().sum())
            print(dim_sellers_df[dim_sellers_df.duplicated()])
            print(dim_sellers_df['seller_city'].value_counts())

            dim_sellers_df['seller_city'] = dim_sellers_df['seller_city'].str.lower().str.strip()
            # Remove accents from seller city
            dim_sellers_df['seller_city'] = dim_sellers_df['seller_city'].apply(strip_accents_lambda)

            print(dim_sellers_df['seller_city'].duplicated().sum())
            print(dim_sellers_df['seller_city'].value_counts())
            single_entry_cities = dim_sellers_df['seller_city'].value_counts()[dim_sellers_df['seller_city'].value_counts() == 1]
            print(sorted(single_entry_cities.index))

            rename_cities = {'rio de janeiro': 'rio de janeiro','sao miguel': "sao miguel d'oeste",'sao pau': 'sao paulo'}

            for wrong, correct in rename_cities.items():
              dim_sellers_df.loc[dim_sellers_df['seller_city'].str.contains(wrong, case=False, na=False), 'seller_city'] = correct

            print(dim_sellers_df['seller_state'].value_counts())

            transformed_data['dim_sellers'] = dim_sellers_df
            logging.info("Cleaned and transformed Dim_Sellers.")
        else:
            logging.warning("Raw 'sellers' data not available for Dim_Sellers transformation.")

        # Dim_Orders
        if 'orders' in raw_data and raw_data['orders'] is not None:
            dim_orders_df = raw_data['orders']

            print(dim_orders_df.info())
            dim_orders_df.describe()
            print(dim_orders_df.isnull().sum())
            print(dim_orders_df[dim_orders_df.duplicated()])
            print(dim_orders_df['order_status'].value_counts())

            timestamp_cols = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date']
            for col in timestamp_cols:
                dim_orders_df[col] = pd.to_datetime(dim_orders_df[col], errors='coerce')

            # Removing orders that are not valid
            invalid_orders = dim_orders_df[
            (dim_orders_df['order_approved_at'] < dim_orders_df['order_purchase_timestamp']) |
            (dim_orders_df['order_delivered_carrier_date'] < dim_orders_df['order_approved_at']) |
            (dim_orders_df['order_delivered_customer_date'] < dim_orders_df['order_delivered_carrier_date']) |
            (dim_orders_df['order_estimated_delivery_date'] < dim_orders_df['order_purchase_timestamp'])]

            invalid_orders.info()
            # Check if the dates are null
            print(invalid_orders.isnull().sum())

            null_orders = invalid_orders[invalid_orders['order_delivered_customer_date'].isnull()]
            invalid_orders = invalid_orders.drop(null_orders.index)
            invalid_orders.info()
            print(invalid_orders.isnull().sum())
            dim_orders_df = dim_orders_df.drop(invalid_orders.index).reset_index(drop=True)
            print(invalid_orders['order_id'])
            # Check data type of all the dates
            print(dim_orders_df.info())

            # Format datetime columns to a string format Snowflake can easily parse
            for col in timestamp_cols:
                 # Use .dt.strftime('%Y-%m-%d %H:%M:%S') to format, convert NaT to empty string
                 dim_orders_df[col] = dim_orders_df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

            transformed_data['dim_orders'] = dim_orders_df
            logging.info("Cleaned and transformed Dim_Orders.")
        else:
            logging.warning("Raw 'orders' data not available for Dim_Orders transformation.")


        # Dim_Payments
        if 'order_payments' in raw_data and raw_data['order_payments'] is not None:
            dim_payments_df = raw_data['order_payments']
            dim_orders_df = raw_data['orders']
            print(dim_payments_df.info())
            print(dim_payments_df.describe())
            print(dim_payments_df.isnull().sum())
            print(dim_payments_df[dim_payments_df.duplicated()])
            # Replace boleto to bank_slip payment type
            dim_payments_df['payment_type'] = dim_payments_df['payment_type'].replace("boleto", "bank_slip")
            print(dim_payments_df['payment_type'].value_counts())

            print(dim_payments_df.info())
            print(dim_orders_df.info())

            # print(dim_payments_df[dim_payments_df['payment_type'] == 'not_defined'])

            # The not_defined payment type is set for cancelled orders or not approved orders
            # verified by checking the Orders dataset hence can be removed as only 3 orders are undefined
            # Removing it from orders and order_payment dataframe
            # A payment_type is not_defined if the order was not approved
            undefined_pays = dim_payments_df[dim_payments_df['payment_type']=='not_defined']
            undefined_pays = undefined_pays.loc[:,'order_id'].tolist()
            undefined = dim_orders_df[dim_orders_df['order_id'].isin(undefined_pays)]
            print(undefined.shape[0])

            # We can drop cancelled orders since they are very small and our EDA is not for it
            dim_payments_df = dim_payments_df[dim_payments_df['payment_type'] != 'not_defined']
            dim_orders_df = dim_orders_df[~dim_orders_df['order_id'].isin(undefined_pays)]

            # Check dimension after deleting the rows
            print(dim_payments_df.info())
            print(dim_orders_df.info())

            print(dim_payments_df['payment_type'].value_counts())

            transformed_data['dim_payments'] = dim_payments_df
            transformed_data['dim_orders'] = dim_orders_df

            logging.info("Cleaned and transformed Dim_Payments.")
        else:
            logging.warning("Raw 'order_payments' data not available for Dim_Payments transformation.")

        # Dim_Reviews
        if 'order_reviews' in raw_data and raw_data['order_reviews'] is not None:
            dim_reviews_df = raw_data['order_reviews']
            print(dim_reviews_df.info())
            print(dim_reviews_df.describe())
            print(dim_reviews_df.isnull().sum())
            print(dim_reviews_df[dim_reviews_df.duplicated()])

            timestamp_cols = ['review_creation_date', 'review_answer_timestamp']
            for col in timestamp_cols:
                dim_reviews_df[col] = pd.to_datetime(dim_reviews_df[col], errors='coerce')

            # One review for many orders
            review_counts = dim_reviews_df.groupby('review_id').agg({'order_id': 'nunique', 'review_score': 'nunique', 'review_creation_date': 'nunique'}).sort_values(by='order_id', ascending=False)

            # Remove duplicate review rows
            before = dim_reviews_df.shape[0]
            # Example: drop duplicate review_ids
            dim_reviews_df = dim_reviews_df.drop_duplicates(subset=['review_id'], keep='first')
            after = dim_reviews_df.shape[0]

            print(f"Reviews before cleaning: {before}")
            print(f"Removed {before - after} duplicate reviews")
            print(f"Remaining: {after}")

            # Remove accents from comment title and message
            dim_reviews_df.loc[:, 'review_comment_message'] = dim_reviews_df['review_comment_message'].apply(strip_accents_lambda)
            print(dim_reviews_df.head())

            dim_reviews_df.loc[:, 'review_comment_title'] = dim_reviews_df['review_comment_title'].apply(strip_accents_lambda)
            print(dim_reviews_df.head())

            # Format datetime columns to a string format Snowflake can easily parse
            for col in timestamp_cols:
                 # Use .dt.strftime('%Y-%m-%d %H:%M:%S') to format, convert NaT to empty string
                 dim_reviews_df[col] = dim_reviews_df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

            transformed_data['dim_reviews'] = dim_reviews_df
            logging.info("Cleaned and transformed Dim_Reviews.")
        else:
            logging.warning("Raw 'order_reviews' data not available for Dim_Reviews transformation.")


        # Dim_Geolocation
        if 'geolocation' in raw_data and raw_data['geolocation'] is not None:
            dim_geolocation_df = raw_data['geolocation']
            print(dim_geolocation_df.info())
            print(dim_geolocation_df.describe())
            print(dim_geolocation_df.isnull().sum())
            print(dim_geolocation_df[dim_geolocation_df.duplicated()])
            print(dim_geolocation_df['geolocation_zip_code_prefix'].value_counts())
            print(dim_geolocation_df['geolocation_city'].value_counts())
            print(dim_geolocation_df['geolocation_state'].value_counts())
            dim_geolocation_df['geolocation_zip_code_prefix'] = dim_geolocation_df['geolocation_zip_code_prefix'].astype(str)
            dim_geolocation_df['geolocation_city'] = dim_geolocation_df['geolocation_city'].str.lower().str.strip()
            dim_geolocation_df.loc[:, 'geolocation_city'] = dim_geolocation_df['geolocation_city'].apply(strip_accents_lambda)
            print(dim_geolocation_df['geolocation_city'].value_counts())

            transformed_data['dim_geolocation'] = dim_geolocation_df
            logging.info("Cleaned and transformed Dim_Geolocation.")
        else:
            logging.warning("Raw 'geolocation' data not available for Dim_Geolocation transformation.")


        # Fact_Order_Items
        # Select relevant columns from the raw order_items data
        if 'order_items' in raw_data and raw_data['order_items'] is not None:
            fact_order_items_df = raw_data['order_items']
            dim_orders_df = transformed_data['dim_orders']
            dim_products_df = transformed_data['dim_products']
            dim_sellers_df = transformed_data['dim_sellers']

            print(fact_order_items_df.shape)
            print(fact_order_items_df.describe())
            print(fact_order_items_df.isnull().sum())
            print(fact_order_items_df[fact_order_items_df.duplicated()])

            fact_order_items_df = fact_order_items_df[fact_order_items_df['price'] > 0]
            fact_order_items_df = fact_order_items_df[fact_order_items_df['freight_value'] >= 0]

            # Convert shipping_limit_date to datetime, coercing errors to NaT
            fact_order_items_df['shipping_limit_date'] = pd.to_datetime(fact_order_items_df['shipping_limit_date'], errors='coerce')
            fact_order_items_df.rename(columns={"shipping_limit_date" : "shipping_deadline"}, inplace=True)

            # Check the datetypes
            fact_order_items_df.info()

            numerical_cols = ['order_item_id', 'price', 'freight_value']
            for col in numerical_cols:
                 fact_order_items_df[col] = pd.to_numeric(fact_order_items_df[col], errors='coerce').fillna(0)

            # Format datetime columns to a string format Snowflake can easily parse
            # Only shipping_deadline is a timestamp in Fact_Order_Items based on the schema
            if 'shipping_deadline' in fact_order_items_df.columns:
                 fact_order_items_df['shipping_deadline'] = fact_order_items_df['shipping_deadline'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

            # Order_Items is linked to Order, Product and Sellers table.
            # As we cleaned Order, Product and Sellers table, removing the
            # similar records from Order_Items table
            not_in_fact_order_items = fact_order_items_df[~fact_order_items_df['order_id'].isin(dim_orders_df['order_id'])]
            print("Removing Orders which are not linked to Order Items")
            print(not_in_fact_order_items)
            fact_order_items_df.drop(not_in_fact_order_items.index, inplace=True)
            print(fact_order_items_df.shape)
            not_in_fact_order_items = fact_order_items_df[~fact_order_items_df['product_id'].isin(dim_products_df['product_id'])]
            print("Removing Products which are not linked to Order Items")
            print(not_in_fact_order_items)
            fact_order_items_df.drop(not_in_fact_order_items.index, inplace=True)
            print(fact_order_items_df.shape)

            not_in_fact_order_items = fact_order_items_df[~fact_order_items_df['seller_id'].isin(dim_sellers_df['seller_id'])]
            print("Removing Seller which are not linked to Order Items")
            print(not_in_fact_order_items)
            fact_order_items_df.drop(not_in_fact_order_items.index, inplace=True)
            print(fact_order_items_df.shape)

            transformed_data['fact_order_items'] = fact_order_items_df
            logging.info("Cleaned and transformed Fact_Order_Items.")
        else:
            logging.warning("Raw 'order_items' data not available for Fac_Order_Items transformation.")

        # --- Data Validation (before loading) ---
        logging.info("Performing data validation checks...")

        # Example Validation: Check for unexpected nulls in primary/foreign key columns
        pk_fk_checks = {
            'dim_customers': ['customer_id'],
            'dim_products': ['product_id'],
            'dim_sellers': ['seller_id'],
            'dim_orders': ['order_id', 'customer_id'],
            'dim_payments': ['order_id'],
            'dim_reviews': ['review_id', 'order_id'],
            'dim_geolocation': ['geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng'],
            'fact_order_items': ['order_id', 'order_item_id', 'product_id', 'seller_id']
        }

        for table_name, cols_to_check in pk_fk_checks.items():
            if table_name in transformed_data and transformed_data[table_name] is not None:
                df = transformed_data[table_name]
                for col in cols_to_check:
                    if col in df.columns and df[col].isnull().any():
                        validation_errors.append(f"Validation Error: Null values found in key column '{col}' in transformed table '{table_name}'.")
                        logging.error(f"Validation Error: Null values found in key column '{col}' in transformed table '{table_name}'.")

        # Added more validation checks here
        # Example: Check for non-positive prices or freight values in Fact_Order_Items
        if 'fact_order_items' in transformed_data and transformed_data['fact_order_items'] is not None:
            fact_df = transformed_data['fact_order_items']
            if 'price' in fact_df.columns:
                invalid_prices = fact_df[fact_df['price'] < 0]
                if not invalid_prices.empty:
                    validation_errors.append(f"Validation Error: Negative price values found in Fact_Order_Items. Count: {len(invalid_prices)}")
                    logging.error(f"Validation Error: Negative price values found in Fact_Order_Items. Count: {len(invalid_prices)}")

            if 'freight_value' in fact_df.columns:
                 invalid_freight = fact_df[fact_df['freight_value'] < 0]
                 if not invalid_freight.empty:
                    validation_errors.append(f"Validation Error: Negative freight values found in Fact_Order_Items. Count: {len(invalid_freight)}")
                    logging.error(f"Validation Error: Negative freight values found in Fact_Order_Items. Count: {len(invalid_freight)}")

        # Example: Check for valid review scores (assuming 1 to 5)
        if 'dim_reviews' in transformed_data and transformed_data['dim_reviews'] is not None:
             reviews_df = transformed_data['dim_reviews']
             if 'review_score' in reviews_df.columns:
                 invalid_scores = reviews_df[(reviews_df['review_score'] < 1) | (reviews_df['review_score'] > 5)]
                 invalid_scores = invalid_scores[(invalid_scores['review_score'] < 1) | (invalid_scores['review_score'] > 5)]

                 if not invalid_scores.empty:
                    validation_errors.append(f"Validation Error: Invalid review scores found in Dim_Reviews (expected 1-5). Count: {len(invalid_scores)}")
                    logging.error(f"Validation Error: Invalid review scores found in Dim_Reviews (expected 1-5). Count: {len(invalid_scores)}")

        if validation_errors:
            logging.error("Data validation failed with the following errors:")
            for error in validation_errors:
                logging.error(error)

        logging.info("Data validation checks completed.")

    except Exception as e:
        logging.error(f"An error occurred during data cleaning and transformation: {e}", exc_info=True)
        return {} # Return empty dictionary to indicate transformation failure

    return transformed_data
