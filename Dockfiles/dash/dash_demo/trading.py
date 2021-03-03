# -*- coding: utf-8 -*-
import dash
import dash_html_components as html
import dash_core_components as dcc
import redis
from dash.dependencies import Output, Input, State
from plotly.data import iris

import kydb
import pickle
from datetime import date
import pandas as pd
import plotly.express as px
from .server import app
from dash.exceptions import PreventUpdate


tsdb = kydb.connect('dynamodb://epython/timeseries')
ts = tsdb['/symbols/fxcm/minutely/USDJPY']
hist_data = ts.curve(date(2018, 4, 8), date(2018, 4, 11))
hist_data.sort_index(inplace=True)

db = kydb.connect('dynamodb://epython')
config = db['/demos/epython-dash-demo/config']

host = config.get('REDIS_HOST', '127.0.0.1')
port = config.get('REDIS_PORT', '6379')
redis_conn = redis.Redis(host=host, port=port)

UNIT_QTY = [
    ('M', 1e6),
    ('k', 1e3),
    ('', 0),
]

layout = html.Div([
    dcc.Slider(
        id='trade-size-slider',
        min=100e3,
        max=2e6,
        step=100e3,
        value=100e3,
    ),
    html.Div([
        dcc.Input(id='book', value='Book1'),
        dcc.Input(id='trade-size',
            style={'font-size': '16pt', 'width': '75px'}),
        html.Button('Buy', id='buy-button', n_clicks=0,
            className='buy-sell-button'),
        html.Button('Sell', id='sell-button', n_clicks=0,
            className='buy-sell-button'),
    ]),
    html.Div(id='trade-msg'),
    html.Div([
        dcc.Graph(id='price-pos-plot')]),
    dcc.Interval(
        id='interval-component',
        interval=1000, # in milliseconds
        n_intervals=0
    ),
    # hidden signal value
    html.Div(id='tick-signal', style={'display': 'none'}),
    html.Div(id='trade-signal', style={'display': 'none'})
])

@app.callback(
    Output('trade-size', 'value'),
    Input('trade-size-slider', 'value'))
def update_trade_size(value):
    unit, qty = next((u, value / (q or 1)) for u, q in UNIT_QTY if value >= q)
    return f'{qty}{unit}'
    

@app.callback(
    Output('tick-signal', 'children'),
    Input('interval-component', 'n_intervals'),
    State('tick-signal', 'children')
    )
def compute_value(n, prev_tick):
    tick = redis_conn.get('tick')
    
    if tick is None:
        raise PreventUpdate
        
    tick = int(tick)
    if prev_tick == tick:
        raise PreventUpdate

    return tick
    

trades_df = None

@app.callback(
    Output('trade-signal', 'children'),
    Input('interval-component', 'n_intervals'),
    )
def check_new_trades(n):
    global trades_df
    prev_len = 0 if trades_df is None else trades_df.shape[0]
    
    if prev_len == int(redis_conn.llen('trades')):
        raise PreventUpdate
        
    trades = [pickle.loads(x) for x in redis_conn.lrange('trades', 0, -1)]
    
    if not trades:
        raise PreventUpdate
    
    def get_row(dt, book, asset, qty):
        hist_row = hist_data.loc[dt]
        return (hist_row.name, book, asset, qty, abs(qty), hist_row.closeprice,
            'BUY' if qty > 0 else 'SELL')
    
    trade_data = [get_row(*x) for x in trades]
    columns = ['dt', 'book', 'asset', 'qty', 'trade_size', 'price', 'trade_type']
    trades_df = pd.DataFrame(trade_data, columns=columns)
        
    return n


@app.callback(
    Output('price-pos-plot', 'figure'),
    Input('tick-signal', 'children'),
    State('trade-signal', 'children'))
def update_price_pos(n, trade):
    if trades_df is None:
        raise PreventUpdate

    price_df = hist_data[:n]
    
    price_fig = px.line(hist_data, y='closeprice')
    scatter_df = trades_df[(trades_df.dt >= price_df.iloc[0].name) &
        (trades_df.dt <= price_df.iloc[-1].name)]
        
    if scatter_df.empty:
        return
    
    fig = px.scatter(scatter_df, x=scatter_df.dt, y=scatter_df.price, size='trade_size', color='trade_type')
    fig.add_scatter(x=price_df.index, y=price_df.closeprice, mode='lines',
        opacity=0.5, name='price')
    return fig


@app.callback(
    Output('trade-msg', 'children'),
    [
        Input('buy-button', 'n_clicks'),
        Input('sell-button', 'n_clicks')
    ],
    [
        State('book', 'value'),
        State('trade-size', 'value'),
        State('tick-signal', 'children')
    ]
    )
def apply_trade(buy_clicks, sell_clicks, book, qty, n):
    if not qty:
        return
    
    if not book:
        return 'Book not defined. Do nothing'
    
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    
    f_qty = next(float(qty[:-1]) * q if u else float(qty) for u, q in UNIT_QTY if qty.endswith(u))
    if not f_qty:
        return '0 quantity. Do nothing'
        
    if 'buy' in  changed_id:
        verb = 'Bought'
    else:
        verb = 'Sold'
        f_qty *= -1
    
    dt = hist_data.index[n]
    trade = (dt, book, 'USDJPY', f_qty)
    redis_conn.lpush('trades', pickle.dumps(trade))
    return f'{verb} {qty}'
