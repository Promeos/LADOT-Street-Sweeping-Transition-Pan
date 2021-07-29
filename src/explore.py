# Import libraries
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

############################### Global Variables #########################################


############################# Exploration Datasets #######################################

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
        Dataset of street sweeping citations

    Returns
    -------
    dataset : pandas.core.DataFrame
        Resample dataset of street sweeping citation revenue
    
    '''
    dataset = data.resample(rule=period)[['fine_amount']].sum()

    if period == 'D':
        dataset['is_week_day'] = np.where(dataset.index.weekday < 5, 1, 0)
        dataset['fine_amount'] = dataset['fine_amount'].where(dataset.index.weekday <= 5, 0).replace(0, np.NaN)
    
    return dataset

############################### Visualizations ###########################################