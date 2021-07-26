# Import libraries
import pandas as pd
import plotly.express as px

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

    dataset = data.set_index('issue_time')
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
    dataset = data.resample(rule=period)['fine_amount'].sum()
    return dataset

############################### Visualizations ###########################################