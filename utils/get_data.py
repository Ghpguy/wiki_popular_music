#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Billboard Data Scraper

Custom Scraping Script to get Billboard Hot 100 Top Ten Singles Data from Wikipedia
"""

import os
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re 
import random
from time import sleep

HEADERS = {"User-Agent": "Mozilla/5.0"}  # Avoid HTTP 403
BASE_URL = "https://en.wikipedia.org/wiki/Lists_of_Billboard_Hot_100_top-ten_singles"

def get_links(url, headers=HEADERS):
    """
    Function to get all relevant links from the base URL.
    Returns a list of URLs to scrape.
    """

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure it succeeded
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all('a', href=True)
    billboard_links = [
        "https://en.wikipedia.org" + link['href']
        for link in links
        if link['href'].startswith('/wiki/List_of_Billboard_Hot_100_top-ten_singles_in')
    ]
    billboard_links = list(set(billboard_links))
    return billboard_links

def scrape_data(urls=None, headers=HEADERS):
    """
    Function for taking a list of URLs and scraping data from each one.
    Returns a pandas DataFrame with the combined data.
    If no URLs are provided, it returns an empty DataFrame.
    """
    all_data = []

    # Final column names
    column_names = [
        'Top Ten Entry Date',
        'Single Name',
        'Artist(s)',
        'Peak',
        'Peak Date',
        'Weeks in Top Ten',
        'Ref',
        'Year'
    ]

    for url in urls:
        print(f"Scraping URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        # We only need the first table on each page
        table = soup.find("table", {"class": "wikitable"})

        # Convert sentinel <th colspan="7"> into <td colspan="7"> so pandas keeps them
        for sentinel in table.find_all("th"):
            if sentinel.get("colspan"):  # only the multi-col sentinel headers
                sentinel.name = "td"

        # Extract default year from URL
        year = int(url[-4:])

        # Read table into DataFrame, but keep all rows (including sentinel rows)
        df = pd.read_html(str(table), header=0)[0]

        # Handle missing 'Ref' column
        if len(df.columns) == 6: 
            df['Ref'] = None

        # Add year column, initially filled with default
        df['Year'] = pd.NA

        # --- Sentinel logic ---
        # Find sentinel rows like "Singles from 2024"
        mask = df.apply(
            lambda row: row.astype(str).str.contains(r"Singles from \d{4}").any(),
            axis=1
        )
        
        if mask.sum() == 0:
            # If no sentinels, fill year column with default year
            df["Year"] = year
        else:
            # Extract year from sentinel rows
            df.loc[mask, "Year"] = df.loc[mask].apply(
                lambda row: int(re.search(r"\d{4}", " ".join(row.astype(str))).group()),
                axis=1
            )
        

        # Forward-fill the year column
        df["Year"] = df["Year"].ffill()

        # Drop the sentinel rows
        df = df[~mask].reset_index(drop=True)

        # Rename columns consistently
        df.columns = column_names

        # Add year to peak date since this will always takes the url's year
        df['Peak Date'] = (
            df['Peak Date']
            .str.replace(r'\(.*\)', '', regex=True)    # remove anything in parentheses
            .str.replace(r'\[\d+\]', '', regex=True)   # remove citation brackets like [1]
            .str.strip()                               # remove leading/trailing whitespace
        )
        df['Peak Date'] = pd.to_datetime(df['Peak Date'].astype(str) + ' ' + str(year), errors='coerce')

        # add year to entry date
        df['Top Ten Entry Date'] = (
            df['Top Ten Entry Date']
            .str.replace(r'\(.*\)', '', regex=True)    # remove anything in parentheses
            .str.replace(r'\[\d+\]', '', regex=True)   # remove citation brackets like [1]
            .str.strip()                               # remove leading/trailing whitespace
        )
        df['Top Ten Entry Date'] = pd.to_datetime(df['Top Ten Entry Date'].astype(str) + ' ' + df['Year'].astype(str), errors='coerce')

        ### lets clean the data up a bit
        #remove everything after the second " in the single name
        df['Single Name'] = df['Single Name'].str.split('"').str[1]
        #convert weeks in top ten to int
        df['Weeks in Top Ten'] = df['Weeks in Top Ten'].astype(str).str.extract(r'(\d+)')  # extract the number
        df['Weeks in Top Ten'] = df['Weeks in Top Ten'].astype(int)
        #convert peak to int
        # Keep only digits and convert to integer
        df['Peak'] = df['Peak'].astype(str).str.extract(r'(\d+)')  # extract the number
        df['Peak'] = df['Peak'].astype(int)  # convert to integer

        all_data.append(df)
        sleep(random.uniform(1, 3))  # sleep between 1 and 3 seconds

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def save_to_csv(df, filename=None):
    """
    Save a pandas DataFrame to the `data` folder.
    """
    if df.empty:
        print("No data to save.")
        return

    # Create a timestamped filename if none is provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y_%m")
        filename = f"billboard_data_{timestamp}.csv"

    # Get the repo root assuming this file is in utils/
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Path to the data folder
    data_folder = os.path.join(repo_root, "data")
    os.makedirs(data_folder, exist_ok=True)  # ensure folder exists

    # Full path to CSV
    file_path = os.path.join(data_folder, filename)

    # Save DataFrame
    df.to_csv(file_path, index=False, encoding='utf-8')

    print(f"Data saved to {file_path}")

def main():
    links = get_links(BASE_URL)
    data = scrape_data(links)
    save_to_csv(data)

if __name__ == "__main__":
    main()
