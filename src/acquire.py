import pandas as pd
import os
import sys
import json
import tqdm
from requests import get
from time import sleep

sys.path.insert(1, '../env.py')
import env

#################################### Acquire Parking Citation Data ######################################
def get_citation_data():
    '''
    Returns the Los Angeles Parking Citation Data as a pandas dataframe.
    
    Prerequisite:
    - Download dataset from https://www.kaggle.com/cityofLA/los-angeles-parking-citations
    
    dataset : pandas.core.DataFrame
        Pandas dataframe of Los Angeles parking citations.
    '''
    dataset = pd.read_csv('./data/raw/parking-citations.csv')
    return dataset


def get_sweep_data(prepared=False):
    '''
    Returns a dataframe of street sweeping citations issued in
    Los Angeles, CA from 01/01/2017 - 03/31/2021.
    
    Parameters
    ----------
    prepared : bool, default False
        False : Returns an unprepared version of the street sweeping violation dataset.
        True : Returns a prepared version of the street sweeping violation dataset.

    Returns
    -------
    dataset : pandas.core.DataFrame
        Dataset of Street Sweeping Violations between 2017-01-01 and 2012-03-31.
    '''
    # File name of street sweeping data
    if prepared == True:
        filename = './data/prepared/train.csv'
    else:
        filename = './data/raw/sweeping-citations.csv'

    if os.path.exists(filename) and prepared == True:
        dataset = pd.read_csv(filename, parse_dates=['issue_date'], infer_datetime_format=True)
        dataset.issue_time = pd.to_datetime(dataset.issue_time).dt.time
    elif os.path.exists(filename) and prepared == False:
        dataset = pd.read_csv(filename)
    else:
        data = get_citation_data()
        
        # Filter for street sweeper citations data issued 2017-Today.
        dataset = data.loc[(data['Issue Date'] >= '2017-01-01')&(data['Issue Date'] <= '2021-03-31')&(data['Violation Description'].str.contains('STREET CLEAN'))]
        
        # Cache the filtered dataset
        dataset.reset_index(drop=True, inplace=True)
        dataset.to_csv(filename, index=False)
    return dataset


#################################### Acquire Twitter Data ###################################################
def auth():
    '''
    Bearer Token to access Twitter's API V2

    Apply for a Twitter Developer account to gain access to Twitter's API.
    
    Returns
    -------
    env.bearer_token : str
        alphanumeric string
    '''
    return env.bearer_token


def auth_header():
    '''
    Header required to access Twitter's API V2
    
    Returns
    -------
    headers : dict
        A dictionary to store login credentials. This 
        header is required for all GET requests to Twitter's API.
    '''
    headers = {"Authorization": "Bearer {}".format(auth())}
    return headers


def check_local_cache(file):
    '''
    Accepts a file name and checks to see if a local
    cached version of the data exists.
    
    Parameters
    ----------
    file : str
        The name of the CSV file in the local directory
        
    Returns
    -------
    Return cached file as a pandas DataFrame if : os.path.isfile(file_name) == True
    Return False otherwise
    '''
    if os.path.isfile(file):
        return pd.read_csv(file, index_col=False)
    else:
        return False


def user_tweets(account, tweet):
    '''
    Structure the Tweets returned from Twitter's API into a pandas DataFrame.

    Parameters
    ----------
    account : str
        The id, name, and username of each city official stored in get_twitter_usernames()
        
    tweet : dict
        A nested dictionary with data for a single tweet.
        
    Returns
    -------
    tweet_data : pandas.core.DataFrame
    '''
    tweet_data = pd.DataFrame({'post_time': pd.to_datetime(tweet['created_at']),
                               'id': account['id'],
                               'name': account['name'],
                               'username': account['username'],
                               'tweet': tweet['text'].lower(),
                               'retweet_count': tweet['public_metrics']['retweet_count'],
                               'reply_count': tweet['public_metrics']['reply_count'],
                               'like_count': tweet['public_metrics']['like_count'],
                               'quote_count': tweet['public_metrics']['quote_count'],
                               'tweet_url_id': tweet['id']
                               },index=[0])
    return tweet_data   
    
    
def get_twitter_data():
    '''
    Returns the twitter data for each city council official that signed the motion to resume Street Sweeping on
    10/15/2020.
    
    Link to document:
    https://github.com/Promeos/LADOT-COVID19-enforcement/blob/main/city-documents/city-council/public-outreach-period.pdf

    Note: Mayor Gracetti did not sign the motion.
    
        
    Returns (Conditional)
    -------
    If `cache` is not False:
        cache : pandas.core.frame.DataFrame
            The cached tweets of each city council representative and LADOT between 09/30/2020 - 10/15/2020
            
    If `cache` is False:
        dataset : pandas.core.frame.DataFrame
             The cached tweets of each city council representative and LADOT between 09/30/2020 - 10/15/2020
    '''
    # Paths to the datasets, if they exist.
    path = './data/prepared/'
    filename_dataset = 'tweets.csv'
    filename_accounts = 'twitter_accounts.csv'
    cache = check_local_cache(file=path+filename_dataset)
    
    if cache is False:
        # Store the dict of council members & LADOT's Twitter info.
        twitter_accounts = pd.read_csv(path+filename_accounts)
        
        # Count the # of Twitter accounts to pass as an arg to tqdm to show user loading time.
        num_accounts = len(twitter_accounts)
        
        # Create an empty DataFrame to store the tweets from each account
        data = pd.DataFrame()

        # Acquire Tweets from 09-30-2020 to 10-14-2020 for each user.
        for _, account in tqdm.tqdm(twitter_accounts.iterrows(), total=num_accounts):
            # API URL to acquire data from a specific Twitter account.
            url = f"https://api.twitter.com/2/users/{account['id']}/tweets?user.fields=created_at,description"\
                + ",entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics"\
                + ",url,username,verified&max_results=100&start_time=2020-09-30T00:00:00Z&end_time=2020-10-15T00:00:00"\
                + "Z&expansions=&tweet.fields=created_at,public_metrics,source,text"
            
            # Send a GET request to Twitter's API using developer credentials #Developer
            response = get(url, headers=auth_header())
            
            # Don't get banned
            sleep(3)

            tweets = json.loads(response.text.encode('UTF-8'))['data']

            # Extract features from each tweet and add it to the dataset.
            for tweet in tweets:
                tweet_data = user_tweets(account=account, tweet=tweet)
                data = pd.concat([data, tweet_data])
                
        # Sort the Tweets by Timestamp
        dataset = data.sort_values(by=['post_time']).reset_index(drop=True)
        
        # Create a new column to store user engagement per Tweet
        dataset = dataset.assign(
            total_engagement = dataset[['retweet_count', 'reply_count', 'like_count', 'quote_count']].sum(axis=1)
        )
        
        # Cache the dataframe as a CSV file in the local directory.
        dataset.to_csv(path+filename_dataset, index=False)
        return dataset
    else:
        # Return Twitter data
        return cache