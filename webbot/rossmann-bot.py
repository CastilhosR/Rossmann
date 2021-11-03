import os
import requests
import json
import pandas as pd
from flask import Flask, request, Response, send_from_directory

# constants
TOKEN = '2095908821:AAE4PLpOkwXY8QnJt0F_jEHAAxg2q64QaFI'

def send_message( chat_id, text ):
    global TOKEN
    url = 'https://api.telegram.org/bot{}/'.format( TOKEN ) 
    url = url + 'sendMessage?chat_id={}'.format( chat_id ) 

    r = requests.post( url, json={'text': text } )
    print( 'Status Code {}'.format( r.status_code ) )

    return None


def load_dataset( store_id ) -> object:
    # loading test dataset
    df10 = pd.read_csv( 'test.csv' )
    df_store_raw = pd.read_csv( 'store.csv' )

    # merge test dataset + store
    df_test = pd.merge( df10, df_store_raw, how='left', on='Store' )

    # choose store for prediction
    df_test = df_test[df_test['Store'] == store_id]

    if df_test.empty:
        data = 'error'

    else:
        # remove closed days
        df_test = df_test[df_test['Open'] != 0]
        df_test = df_test[~df_test['Open'].isnull()]
        df_test = df_test.drop( 'Id', axis=1 )

        # convert Dataframe to json
        data = json.dumps( df_test.to_dict( orient='records' ) )

    return data


def predict( data ):
    # API Call
    url = 'https://rossmann-api.herokuapp.com/rossmann/predict'
    header = {'Content-type': 'application/json' }

    r = requests.post( url, data=data, headers=header )
    print( 'Status Code {}'.format( r.status_code ) )

    d1 = pd.DataFrame( r.json(), columns=r.json()[0].keys() )

    return d1


def parse_message( message ):
    chat_id = message['message']['chat']['id']
    store_id = message['message']['text']

    store_id = store_id.replace( '/', '' )

    try:
        store_id = int( store_id )

    except ValueError:
        store_id = 'error'

    return chat_id, store_id


# API initialize
app = Flask( __name__ )

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route( '/', methods=['GET', 'POST'] )
def index():
    if request.method == 'POST':
        message = request.get_json()

        chat_id, store_id = parse_message( message )

        if store_id == 'error':
            send_message( chat_id, 'Store ID is Wrong' )
            return Response( 'Ok', status=200 )

        else:
            data = load_dataset( store_id ) # loading data

            if data == 'error' :
                send_message( chat_id, 'Store Not Available' )
                return Response( 'Ok', status=200 )

            else:
                d1 = predict( data ) # prediction
                d2 = d1[['store', 'prediction']].groupby( 'store' ).sum().reset_index() # compute
                msg = 'Store Number {} will sell R$ {:,.2f} in the next 6 weeks'.format( d2['store'].values[0], d2['prediction'].values[0] )
                send_message( chat_id, msg )  # return data
                return Response( 'Ok', status=200 )

    else:
        return '<h1> Rossmann Telegram BOT </h1>'

if __name__ == '__main__' :
    port = os.environ.get( 'PORT', 5000 )
    app.run( host='0.0.0.0', port=port )
