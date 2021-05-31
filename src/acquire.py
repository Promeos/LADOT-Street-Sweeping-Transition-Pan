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
    
    df : pandas.core.DataFrame
        Pandas dataframe of Los Angeles parking citations.
    '''
    df = pd.read_csv('./data/raw/parking-citations.csv')
    return df


def get_sweep_data():
    '''
    Returns a dataframe of Street Sweeping citations issued in
    Los Angeles, CA from 01/01/2017 - 04/12/2021
    
    Returns
    -------
    df_sweep : pandas.core.DataFrame
    '''
    # File name of street sweeping data
    filename = './data/raw/sweeping-citations.csv'

    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        df = get_citation_data()
        
        # Filter for street sweeper citations data issued 2017-Today.
        df_sweep = df.loc[(df['Issue Date'] >= '2017-01-01')&(df['Violation Description'].str.contains('STREET CLEAN'))]
        
        # Cache the filtered dataset
        df_sweep.reset_index(drop=True, inplace=True)
        df_sweep.to_csv(filename, index=False)
        return df_sweep


#################################### Acquire Twitter Data ###################################################
def auth():
    '''
    Bearer Token used to access Twitter's API V2
    
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
        The name of the file in the local directory
        
    Returns
    -------
    Return cached file as a pandas DataFrame if : os.path.isfile(file_name) == True
    Return False otherwise
    '''
    if os.path.isfile(file):
        return pd.read_csv(file, index_col=False)
    else:
        return False
    
    
def get_twitter_usernames():
    '''
    A list of dictionaries containing the unique twitter id, name, and username of
    Los Angeles government officials who signed the motion to resume street sweeping
    on 10/15/2020.
    
    Link to document:
    https://github.com/Promeos/LADOT-COVID19-enforcement/blob/main/city-documents/city-council/public-outreach-period.pdf
    
    Note: Mayor Gracetti did not sign the motion.
    
    Returns
    -------
    twitter_accounts : pandas.core.DataFrame
        A dataframe containing the Twitter numeric id, name of the account holder, and username of the account.
    '''
    data = [
        {
            "id": "17070113",
            "name": "MayorOfLA",
            "username": "MayorOfLA"
        },
        {
            "id": "61261275",
            "name": "LADOT",
            "username": "LADOTofficial"
        },
        {
            "id": "956763276",
            "name": "Nury Martinez",
            "username": "CD6Nury"
        },
        {
            "id": "893602974",
            "name": "Curren D. Price, Jr.",
            "username": "CurrenDPriceJr"
        },
        {
            "id": "341250146",
            "name": "Joe Buscaino",
            "username": "JoeBuscaino"
        }
    ]
    
    # Gil has not tweeted since 2019.
    # {
    # "id": "1167156666",
    # "name": "Gil Cedillo",
    # "username": "cmgilcedillo"
    # }
    
    # Transform the list of dictionaries into a dataframe
    twitter_accounts = pd.DataFrame.from_records(data)
    
    # Replace the account holders' name to be more descriptive.
    twitter_accounts.name = twitter_accounts.name.str.replace('MayorOfLA', 'Eric Garcetti')
    twitter_accounts.name = twitter_accounts.name.str.replace('LADOT', 'Los Angeles Department of Transportation')
    
    # Return the dataframe of Twitter accounts.
    return twitter_accounts


def tweet_info(account, tweet):
    '''
    Structures the data returned from Twitter's API into a Pandas DataFrame.

    Parameters
    ----------
    file : str
        The name of the file in the local directory
        
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
        df : pandas.core.frame.DataFrame
             The cached tweets of each city council representative and LADOT between 09/30/2020 - 10/15/2020
    '''
    # Check the local directory for the Twitter data
    filename = './data/prepared/tweets.csv'
    cache = check_local_cache(file=filename)
    
    
    if cache is False:
        # Store the dict of council members & LADOT's Twitter info.
        twitter_accounts = get_twitter_usernames()
        
        # Calculate the # of Twitter accounts in `twitter_accounts`
        num_accounts = len(twitter_accounts)
        
        # Store the URL header to a variable
        credentials = auth_header()
        
        # Create an empty DataFrame to store the tweets from each account
        df = pd.DataFrame()

        # For each account in the dataframe `twitter_accounts` acquire all tweets from
        # 09-30-2020 to 10-14-2020.
        # "tqdm.tqdm()" used to display loading status.
        for _, account in tqdm.tqdm(twitter_accounts.iterrows(), total=num_accounts):
            # API URL to acquire data from a specific Twitter account.
            url = f"https://api.twitter.com/2/users/{account['id']}/tweets?user.fields=created_at,description"\
                + ",entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics"\
                + ",url,username,verified&max_results=100&start_time=2020-09-30T00:00:00Z&end_time=2020-10-15T00:00:00"\
                + "Z&expansions=&tweet.fields=created_at,public_metrics,source,text"
            
            # Send a GET response to the API using the URL and bearer token credentials
            response = get(url, headers=credentials)
            
            # Set 3 second delay between each GET request
            sleep(3)

            # Use json.loads() to index into the `data` key of the response dictionary.
            # Encode from bytes to UTF-8
            tweets = json.loads(response.text.encode('UTF-8'))['data']

            # Extract the information from each tweet and store it as a row in `df`.
            for tweet in tweets:
                tweet_data = tweet_info(account=account, tweet=tweet)
                df = pd.concat([df, tweet_data])
                
        # Sort the tweets by Timestamp
        df = df.sort_values(by=['post_time']).reset_index(drop=True)
        
        # Create a new column to store user engagement per Tweet
        df = df.assign(
            total_engagement = df[['retweet_count', 'reply_count', 'like_count', 'quote_count']].sum(axis=1)
        )
        
        # Cache the dataframe as a CSV file in the local directory.
        df.to_csv(filename, index=False)
        return df
    else:
        # Return Twitter data
        return cache