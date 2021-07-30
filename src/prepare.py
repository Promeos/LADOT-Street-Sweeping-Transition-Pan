# Import data prep libraries
from ast import parse
import pandas as pd
import numpy as np
import os
from datetime import time
from calendar import monthrange

# Library to covert coordinates
from pyproj import Proj, transform


################################ Data Prep Functions #########################################
def drop_features(data):
    '''
    Drop unused features from the dataset.
    
    Parameters
    ---------
    data : pandas.core.DataFrame
    
    Returns
    -------
    dataset : pandas.core.DataFrame
        A pandas DataFrame with features:
        - issue_date
        - issue_time
        - location
        - route
        - agency
        - violation_description
        - fine_amount
        - latitude
        - longitude
    '''
    data.drop_duplicates(inplace=True)
    
    # Drop features not relevant to the project.
    features_to_drop =['vin', 'rp_state_plate', 'plate_expiry_date', 'make',
                      'body_style', 'color', 'marked_time', 'color_description',
                      'body_style_description', 'agency_description', 'meter_id',
                      'ticket_number', 'violation_code']
    
    data.drop(columns=features_to_drop, inplace=True)
    
    # Drop citations with missing data or duplicated.
    dataset = data.dropna(axis=0)
    
    return dataset
    

def cast_time(data):
    '''
    Converts citation issue time from a float to a Timestamp data type.
    
    Parameters
    ---------- 
    data : pandas.core.DataFrame
    
    Returns
    -------
    dataset : pandas.core.DataFrame
    '''
    data.issue_date = pd.to_datetime(data.issue_date)
    data.issue_time = data.issue_time.astype('int').astype('str')
    
    times = []

    # Parse each time according to its length.
    for t in data.issue_time:
        if len(t) == 4:
            h = t[:2]
            m = t[2:]
        elif len(t) == 3:
            h = t[0]
            m = t[1:]
        else:
            h = '0'
            m = '0'
        h = int(h)
        m = int(m)
        times.append(time(hour=h, minute=m))
    
    data.issue_time = times
    
    # Remove invalid citation issue times from the dataset.
    dataset = data[data.issue_time != time(hour=0, minute=0, second=0)]
    
    return dataset


def convert_coordinates(data):
    '''
    Transforms lat/long coordinates from NAD1983StatePlaneCaliforniaVFIPS0405 feet projection to
    EPSG:4326 World Geodetic System 1984.
    
    EPSG 4326 is the standard coordinates used in GPS.
    
    Requirements
    ------------
    > pip install pyproj
    
    Parameters
    ----------
    data : pandas.core.DataFrame
        Any pandas dataframe with latitude and longitude coordinates measured
        in NAD1983StatePlaneCaliforniaVFIPS0405 feet projection.
        
    Returns
    -------
    dataset : pandas.core.DataFrame
        A pandas dataframe with latitude and longitude coordinates in EPSG:4326.
    '''
    
    # Conversion string to transform NAD1983StatePlaneCaliforniaVFIPS0405 coordindates to EPSG:4326 
    state_plane = '+proj=lcc +lat_1=34.03333333333333 +lat_2=35.46666666666667 +lat_0=33.5 +lon_0=-118 +x_0=2000000 ' \
         '+y_0=500000.0000000002 +ellps=GRS80 +datum=NAD83 +to_meter=0.3048006096012192 +no_defs'

    # Store lat/long values for transformation 
    lat, long = data['latitude'].values, data['longitude'].values
    
    # Convert
    # Convert coordinates from US Survey Feet to EPSG:4326
    data['longitude'], data['latitude'] = transform(p1=Proj(state_plane, preserve_units=True),
                                                    p2=Proj("+init=epsg:4326"),
                                                    x=lat,
                                                    y=long)
    
    # Normalize lat/long coordinates by rounding to 4 decimal places.
    data.latitude = np.round(data.latitude, 4)
    data.longitude = np.round(data.longitude, 4)
    
    # Drop citations with invalid coordinates.
    dataset = data.loc[(data.longitude != 99999.0)&(data.latitude != 99999.0)]
    
    return dataset


def add_features(data):
    '''
    Add new features: citation_year, citation_month, citation_day,
    citation_hour, day_of_week, citation_hour, and citation_minute
    
    Parameters
    ---------- 
    data : pandas.core.DataFrame
    
    Returns
    -------
    dataset : pandas.core.DataFrame
    '''

    # Create features using issue_data and issue_time
    dataset = data.assign(
        citation_year = data.issue_date.dt.year,
        citation_month = data.issue_date.dt.month,
        citation_day = data.issue_date.dt.day,
        day_of_week = data.issue_date.dt.day_name()
        )   
    dataset.issue_date.dt.date
    dataset['citation_hour'] = pd.to_datetime(data.issue_time, format='%H:%M:%S').dt.hour
    dataset['citation_minute'] = pd.to_datetime(data.issue_time, format='%H:%M:%S').dt.minute
    
    return dataset


##################################################################################################

# Time Series Preparation

##################################################################################################
def street_sweep(data):
    '''
    Set the index of the street sweeping dataset to 'issue_time' for resampling.
    
    Parameters
    ----------
    data : pandas.core.DataFrame
        dataset of steet sweeping citations.
    
    Returns
    -------
    dataset : pandas.core.DataFrame
        dataset of street sweeping citations indexed by issue date.
    '''

    dataset = data.copy().set_index('issue_date')
    return dataset


def resample_period(data, period='D'):
    '''
    Calculate citation revenue for the specified time period.
    
    Parameters
    ----------
    data : pandas.core.DataFrame
        Street sweeping citations

    Returns
    -------
    dataset : pandas.core.DataFrame
        Resampled street sweeping citation revenue
    
    '''
    dataset = data.resample(rule=period)[['fine_amount']].sum()

    if period == 'D':
        dataset['is_business_day'] = dataset.index.map(lambda x: np.is_busday(pd.to_datetime(x).date()))
        dataset['fine_amount'] = dataset['fine_amount'].where(dataset.is_business_day != False, np.NaN).replace(0, np.NaN)

    dataset.rename(columns={'fine_amount':'revenue'}, inplace=True)
    
    return dataset


def aggregate_sweep_days(data):
    '''
    The total of days each month with regularly scheduled street sweeping.

    Parameters
    ----------
    data : pandas.core.DataFrame
        Dataset of street sweeping citations resample by month

    Returns
    -------
    dataset : pandas.core.DataFrame
        Resampled street sweeping citation revenue
    '''
    dataset = data[(data.is_business_day == True)&(data.revenue > 69532)]
    dataset = dataset.groupby(by=[dataset.index.year, dataset.index.month]).size()
    dataset.index = dataset.index.set_names(names=['year', 'month'])
    dataset = dataset.reset_index(name='num_days_cited')

    dataset.index = pd.to_datetime(dataset['year'].astype('str') + '-' + dataset['month'].astype('str') + '-01')
    dataset.drop(columns=['year', 'month'], inplace=True)
    dataset = dataset.resample('M').sum()

    return dataset

##################################################################################################

# Prepare Street Sweeping Data

##################################################################################################
def prep_sweep_data(data=None):
    '''
    Return prepared street sweeping data for exploration.
    
    Requirements
    ------------
    You will need to install `pyproj` to use this function.
    > pip install pyproj
    
    Parameters
    ----------
    data : pandas.core.DataFrame
        Parking citation data from The City of Los Angeles.

    Returns
    -------
    dataset : pandas.core.DataFrame
        Returns street sweeping pandas DataFrame.
    '''
    filename = './data/prepared/train.csv'
    
    if os.path.exists(filename):
        dataset = pd.read_csv(filename, parse_dates=['issue_date'], infer_datetime_format=True)
        dataset.issue_time = pd.to_datetime(dataset.issue_time).dt.time
        return dataset
    else: 
        # Remove spaces and lowercase column names.
        formatted_feature_names = [x.replace(' ', '_').lower() for x in data.columns.to_list()]
        data.columns = formatted_feature_names

        # Drop unused features, filter, cast date and time datatypes, convert coordinates, and add new features.
        data = drop_features(data)
        data = cast_time(data)
        data = convert_coordinates(data)
        data = add_features(data)
        
        # Drop the index and sort by issue_date
        dataset = data.sort_values(by=['issue_date', 'issue_time'])
        dataset.reset_index(drop=True, inplace=True)
        
        # Filter citation times between 7:30 - 15:30
        min_time = time(hour=7, minute=30)
        max_time = time(hour=15, minute=30)
        
        dataset = dataset[(dataset['issue_time'] >= min_time)&(dataset['issue_time'] <= max_time)]
        
        # Cache file
        dataset.to_csv(filename, index=False)
        
        # Return the prepared dataframe.
        return dataset