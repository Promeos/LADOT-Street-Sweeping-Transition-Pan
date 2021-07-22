# Import data prep libraries
import pandas as pd
import numpy as np
import os

# Library to covert coordinates
from pyproj import Proj, transform


################################ Data Prep Functions #########################################
def drop_features(data):
    '''
    Drop unused features from the dataset.
    
    Parameters
    ---------
    data : pandas.core.DataFrame
    
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
    dataset : pandas.core.DataFrame
        Any pandas dataframe with latitude and longitude coordinates measured
        in NAD1983StatePlaneCaliforniaVFIPS0405 feet projection.
        
    Returns
    -------
    df : pandas.core.DataFrame
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


## Bug Fix in Progess
# def add_features(data):
#     '''
#     Cast date and time values to datetime data type. Add new features day_of_week, issue_year, issue_hour, and issue_minute
#     '''
#     # Cast issue_date and issue_time from a string to a datetime data type.
#     data.issue_date = pd.to_datetime(data.issue_date)
#     data.issue_time = pd.to_datetime(data.issue_time, format='%H%M', errors='coerce').dt.time
    
#     # Combine new features and casting inside of the pandas assign function.
#     # Create features using issue_data and issue_time
#     df = df.assign(
#     day_of_week = df.issue_date.dt.day_name(),
#     issue_year = df.issue_date.dt.year,
#     issue_hour = df.issue_time.dt.hour,
#     issue_minute = df.issue_time.dt.minute,
# )
#     print(type(df.issue_hour))
#     print(type(df.issue_hour))
    
#     # Cast new features from float to int dtype.
#     df.issue_year = df.issue_year.astype(int)
#     df.issue_hour = df.issue_hour.astype(int)
#     df.issue_minute = df.issue_minute.astype(int)
    
#     # Return data
#     return 

  
##################################################################################################

# Prepare Street Sweeping Data

##################################################################################################
def prep_sweep_data(data):
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
        return pd.read_csv(filename)
    else: 
        # Remove spaces and lowercase column names.
        formatted_feature_names = [x.replace(' ', '_').lower() for x in data.columns.to_list()]
        data.columns = formatted_feature_names

        # Drop columns, convert coordinates, and add new features
        data = drop_features(data)
        data = convert_coordinates(data)
        data = add_features(data)
        
        # Drop the index and sort by issue_date
        dataset = data.sort_values(by=['issue_date', 'issue_time'])
        dataset.reset_index(drop=True, inplace=True)
        
        # Cache file
        dataset.to_csv(filename, index=False)
        
        # Return the prepared dataframe.
        return dataset