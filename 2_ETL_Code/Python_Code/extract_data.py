import pandas as pd
import numpy as np
import snowflake.connector
import os
import io
import logging

def extract_data(file_paths):
  """
  Extracts data from CSV files into pandas DataFrames.

  Args:
    file_paths: A dictionary where keys are dataset names (e.g., 'customers')
                and values are the corresponding CSV file paths.

  Returns:
    A dictionary where keys are dataset names and values are pandas DataFrames.
  """
  dataframes = {}
  logging.info("Starting data extraction...")
  for name, path in file_paths.items():
    try:
      dataframes[name] = pd.read_csv(path)
      logging.info(f"Successfully extracted data from {path} into '{name}' DataFrame.")
    except FileNotFoundError:
      logging.error(f"Error: File not found at {path}", exc_info=True)
      dataframes[name] = None # Indicate failure to load this specific file
    except Exception as e:
      logging.error(f"An error occurred while reading {path}: {e}", exc_info=True)
      dataframes[name] = None # Indicate failure to load this specific file
  logging.info("Data extraction finished.")
  return dataframes