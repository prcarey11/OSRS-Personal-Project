import requests
import pandas as pd
import numpy as np
import altair as alt

def generate_table(search='', low=0, high=int(2.1E9)):
    # Define JSON key for query
    json_data = {
        'operationName': 'TABLE_SCORED_ITEMS',
        'variables': {
            'aggMethod': 'latest', 
            'highVolume': False, 
            'f2p': False,
            'dataSource': 'runelite',
            'orderBy': 'score_DESC',
            'searchTerm': search,
            'instaSellPrice_gte': low,
            'instaSellPrice_lte': high
        },
        'query': 'query TABLE_SCORED_ITEMS($f2p: Boolean!, $highVolume: Boolean!, $aggMethod: AggMethodChoice!, $dataSource: DataSourceChoice!, $searchTerm: String, $instaSellPrice_lte: Int, $instaSellPrice_gte: Int, $margin_lte: Int, $margin_gte: Int, $totalQuantity1h_lte: Int, $totalQuantity1h_gte: Int, $returnOnInvestment_lte: Float, $returnOnInvestment_gte: Float, $buySellRatio_lte: Float, $buySellRatio_gte: Float, $minutesOldMax: Int, $idFilter: [Int!], $orderBy: ItemOrderByOptions!)' \
        '{\n  scores(where: {f2p: $f2p, highVolume: $highVolume, aggMethod: $aggMethod, nameContains: $searchTerm, instaSellPrice_lte: $instaSellPrice_lte, instaSellPrice_gte: $instaSellPrice_gte, margin_lte: $margin_lte, margin_gte: $margin_gte, totalQuantity1h_lte: $totalQuantity1h_lte, totalQuantity1h_gte: $totalQuantity1h_gte, returnOnInvestment_lte: $returnOnInvestment_lte, returnOnInvestment_gte: $returnOnInvestment_gte, buySellRatio_lte: $buySellRatio_lte, buySellRatio_gte: $buySellRatio_gte},' \
        'orderBy: $orderBy, limit: 3892, minutesOldMax: $minutesOldMax, dataSource: $dataSource, idFilter: $idFilter)' \
        '{\n    score\n    marketStats {\n      instaBuyPrice\n      instaSellPrice\n      totalQuantity1h\n      returnOnInvestment\n      margin\n      item {\n        name\n        webName\n        buyLimit\n        lastRefreshed\n        id\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n'
    }

    # Create request, generate response and format items into list of JSON keys
    response = requests.post('https://gql.platinumtokens.com/', json=json_data)
    data = response.json()['data']['scores']
    
    # Format data into dataframe object
    df = pd.DataFrame()
    df['name'] = [data[i]['marketStats']['item']['name'] for i in range(len(data))]
    df['buy'] = [data[i]['marketStats']['instaSellPrice'] for i in range(len(data))]
    df['sell'] = [data[i]['marketStats']['instaBuyPrice'] for i in range(len(data))]
    df['margin'] = [data[i]['marketStats']['margin'] for i in range(len(data))]
    df['ROI(%)'] = [round(data[i]['marketStats']['returnOnInvestment']*100, 2) for i in range(len(data))]
    df['tax'] = (df['sell']*0.01).astype(int)
    df['true_margin'] = (df['margin'] - df['tax']).astype(int)
    df['true_ROI(%)'] = round( ( (df['sell'] - df['tax']) / df['buy'] - 1 ) * 100, 2)
    df['quantity'] = [data[i]['marketStats']['totalQuantity1h'] for i in range(len(data))]
    
    # Return final dataframe
    df = df.drop(columns=['margin', 'ROI(%)', 'tax'])
    return df


def generate_favorites_list(items):
    for i in range(len(items)):
        if i == 0:
            df = generate_table(items[0])
        else:
            new_df = generate_table(items[i])
            df = pd.concat([df, new_df])
        
    df = df.reset_index(drop=True)
    return df



def clean_ts_df(df):
    # Cleaning up sellPrice
    for i in range(len(df)):
        if df.loc[i, 'sellPrice'] == 0:
            j = i + 1
            if j >= len(df):
                break
            while not df.loc[j, 'sellPrice']:
                j += 1
                if j >= len(df):
                    break
            if j >= len(df):
                break
            df.loc[i, 'sellPrice'] = df.loc[j, 'sellPrice']
    
    # Cleaning up buyPrice
    for i in range(len(df)):
        if df.loc[i, 'buyPrice'] == 0:
            j = i + 1
            if j >= len(df):
                break
            while not df.loc[j, 'buyPrice']:
                j += 1
                if j >= len(df):
                    break
            if j >= len(df):
                break
            df.loc[i, 'buyPrice'] = df.loc[j, 'buyPrice']
    
    while df.loc[len(df) - 1, 'sellPrice'] == 0 or df.loc[len(df) - 1, 'buyPrice'] == 0:
        df = df.drop([len(df) - 1])
    
    return df


def generate_ts_df(item):
    item = item.lower().replace(' ', '-').replace("'", '').replace('(', '').replace(')', '')

    json_data = {
        'operationName': 'MODAL_ITEM',
        'variables': {
            'dataSource': 'runelite',
            'webName': item,
            'timeframe': 'DAILY',
        },
        'query': 'query MODAL_ITEM($webName: String!, $dataSource: DataSourceChoice!, $timeframe: TimeframeChoice!)' \
        ' {\n  average: marketStats(dataSource: $dataSource, where: {webName: $webName, aggMethod: average}) {\n    instaBuyPrice\n    instaSellPrice\n    totalQuantity24h\n    returnOnInvestment\n    instaBuyQuantity24h\n    instaSellQuantity24h\n    buySellRatio\n    margin\n    item {\n      id\n      name\n      webName\n      buyLimit\n      lastRefreshed\n      highAlch\n      __typename\n    }\n    __typename\n  }\n  latest: marketStats(where: {webName: $webName, aggMethod: latest}, dataSource: $dataSource) {\n    instaBuyPrice\n    instaSellPrice\n    returnOnInvestment\n    margin\n    __typename\n  }\n  nature: scoredItem(where: {aggMethod: average, highVolume: true, f2p: false, webName: "nature-rune"}, dataSource: $dataSource) {\n    marketStats {\n      priceMidPoint\n      __typename\n    }\n    __typename\n  }' \
        '\n  series: tradeSeriesData(timeframe: $timeframe, dataSource: $dataSource, webName: $webName) {\n    overallPrice\n    overallQuantity\n    buyingPrice\n    buyingQuantity\n    sellingPrice\n    sellingQuantity\n    ts\n    __typename\n  }\n}\n',
    }

    response = requests.post('https://gql.platinumtokens.com/', json=json_data)
    ts_data = response.json()['data']['series']
    n = len(ts_data)
    
    df = pd.DataFrame()
    df['sellPrice'] = [ts_data[n - i - 1]['sellingPrice'] for i in range(12)]
    df['buyPrice'] = [ts_data[n - i - 1]['buyingPrice'] for i in range(12)]
    
    df = clean_ts_df(df)
    
    df['sellQuantity'] = [ts_data[n - i - 1]['sellingQuantity'] for i in range(len(df))]
    df['buyQuantity'] = [ts_data[n - i - 1]['buyingQuantity'] for i in range(len(df))]
    df['quantityRatio'] = [df['buyQuantity'][i] / df['sellQuantity'][i] for i in range(len(df))]
    df['trueMargin'] = [int((df['buyPrice'][i] * 0.99) - (df['sellPrice'][i])) for i in range(len(df))]
    df['itemName'] = [item for i in range(len(df))]
    
    return df


def concat_items(dat):
    for i in range(10):
        if i == 0:
            res = generate_ts_df(dat.loc[i, 'name'])
        else:
            new_df = generate_ts_df(dat.loc[i,'name'])
            res = pd.concat([res, new_df])
    
    res.index = res.index * 5
    return res


def check_margins(item):
    dat = generate_ts_df(item)
    dat.index = dat.index * 5
    
    chart = alt.Chart(dat.reset_index()).mark_line(
        point=alt.OverlayMarkDef(color="red")).encode(
        x = alt.X('index:Q', axis=alt.Axis(title='Time Elapsed Since Trade in Minutes'),
                 scale = alt.Scale(domain = [55, -5])),
        y = alt.Y('trueMargin:Q', axis = alt.Axis(title='Margin')),
    ).properties(
        width=300,
        height=250,
        title = 'One Hour of Trade Margins for ' + item
    )
    
    return chart


def check_quantities(item):
    dat = generate_ts_df(item)
    dat.index = dat.index * 5
    
    chart1 = alt.Chart(dat.reset_index()).mark_bar(size=20).encode(
        x = alt.X('index:Q', axis=alt.Axis(title='Time Elapsed Since Trade in Minutes'),
                  scale = alt.Scale(domain = [55, 0])),
        y = alt.Y('sellQuantity:Q', axis = alt.Axis(title='Quantity')),
        opacity=alt.value(0.4),
        color=alt.value('blue')
    ).properties(
        width=300,
        height=250,
        title = 'Quantities Insta Bought and Sold at 5 Minute Intervals for ' + item
    )
 
    chart2 = alt.Chart(dat.reset_index()).mark_bar(size=20).encode(
        x = alt.X('index:Q', axis=alt.Axis(title='Time Elapsed Since Trade in Minutes'),
                  scale = alt.Scale(domain = [55, 0])),
        y = alt.Y('buyQuantity:Q', axis = alt.Axis(title='Quantity')),
        opacity=alt.value(0.4),
        color=alt.value('red')
    )

    res = chart1 + chart2
    return res


def check_prices(item):
    dat = generate_ts_df(item)
    dat.index = dat.index * 5
    
    chart1 = alt.Chart(dat.reset_index()).mark_line(
        point=alt.OverlayMarkDef(color="red")).encode(
        x = alt.X('index:Q', axis=alt.Axis(title='Time Elapsed Since Trade in Minutes'),
                 scale = alt.Scale(domain = [55, -5])),
        y = alt.Y('sellPrice:Q', axis = alt.Axis(title='Price'), scale = alt.Scale(zero=False)),
        color = alt.value('blue'),
        opacity = alt.value(0.4)
    ).properties(
        width=300,
        height=250,
        title = 'One Hour of Trade Margins for ' + item
    )
    
    chart2 = alt.Chart(dat.reset_index()).mark_line(
        point=alt.OverlayMarkDef(color="red")).encode(
        x = alt.X('index:Q', axis=alt.Axis(title='Time Elapsed Since Trade in Minutes'),
                 scale = alt.Scale(domain = [55, -5])),
        y = alt.Y('buyPrice:Q', scale = alt.Scale(zero=False)),
        color = alt.value('red'),
        opacity = alt.value(0.4)
    )
    
    res = chart1 + chart2
    return res


def generate_panel(item):
    return (check_prices(item) & check_quantities(item)) | (check_prices(item) & check_margins(item))