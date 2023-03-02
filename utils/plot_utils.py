import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patheffects as pe
import seaborn as sns
import random

def plot_timeseries_volume(
    df,
    cmap,
    interval: 'time intervals to plot, e.g. "M", "Q", "Y"' = 'Q',
    constrain_source = False,
    title = False
):
    
    if type(constrain_source) == str:
        df = df.loc[df['source'] == constrain_source].copy()
        source_title = constrain_source.title()
    else:
        source_title = 'all venues'
        
    interval_dict = {
        'Y': 'yearly',
        'Q': 'quarterly',
        'M': 'monthly',
        'W': 'weekly',
        'D': 'daily'
    }
    
    interval_title = interval_dict[interval]
    
    df['date'] = pd.to_datetime(df['start_time']).copy()
    stack_data = pd.DataFrame(df.groupby(
        by = [
            pd.Grouper(key='date', freq=interval),
            pd.Grouper(key = 'party')
        ]
    ).count()['doc']).reset_index()
    stack_data['doc'] = stack_data.groupby('date')['doc'].apply(lambda x: x*100/x.sum())

    stack = stack_data.pivot(index = ['date'], columns = 'party')
    stack.columns = [col[1] for col in stack.columns]
    stack_dict = stack.to_dict(orient ='list')
    for key in stack_dict.keys():
        for idx, val in enumerate(stack_dict[key]):
            if np.isnan(val):
                stack_dict[key][idx] = 0

    order = pd.DataFrame(stack_dict).T
    order['sum_col'] = order.sum(axis='columns')
    order = order.sort_values(by='sum_col').drop(columns=['sum_col']).T.to_dict(orient='list')
    stack_palette = pd.Series(order.keys()).map(cmap)

    year = stack.index
    population_by_continent = order

    fig, ax = plt.subplots(figsize=(10,5))
    
    ax.stackplot(
        year,
        population_by_continent.values(),
        labels=population_by_continent.keys(),
        edgecolor='black',
        linewidth=.33,
        colors = stack_palette,
        #baseline = 'weighted_wiggle'
    )
    
    for loc in ['top', 'bottom', 'right', 'left']:
        ax.spines[loc].set_visible(False)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], loc='center left', bbox_to_anchor=(1, 0.5))
    
    notable_dates = {
        '2019-06-05': 'National election',
        '2022-10-01': 'National election'
    } #, '2020-03-11', '2020-09-25', '2021-10-16',
    
    
    for date, desc in notable_dates.items():
        plt.axvline(pd.to_datetime(date), linestyle = '--', color = 'white')
        #plt.text(pd.to_datetime(date), 80, '\n'+desc, color = 'white', weight = 'bold')

    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_yticks([0, 50,100])
    #ax.set_xticks(notable_dates)
    
    if title:
        ax.set_title(f'Proportion of {interval_title} utterances by party ({source_title})\n', size = 14, weight = 'bold')
    plt.margins(x=0, y=0)
    ax.grid(False)
    
    plt.show()
    
def calculate_outliers(df, col):
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1    #IQR is interquartile range. 

    filter = (df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 *IQR) # TODO: Per group
    outliers = df.loc[filter]
    
    return outliers

def draw_volume_boxes(df, cmap, source = 'parliament', label_jitter = 1, remove_list=[], title = False):

    politician_docs = (
        pd.DataFrame(
            df
            .loc[
                (df['level'] == 'politician') &
                (~df['party'].isin(remove_list))
            ]
            .groupby(['full_name', 'party', 'source']).count()['doc'])
            .reset_index()
    )

    politician_docs = politician_docs.loc[politician_docs['source'] == source]

    politician_docs['color'] = politician_docs['party'].map(cmap).fillna('lightgrey')

    sort = politician_docs.groupby('party').median().sort_values(by = 'doc', ascending = False).index

    #politician_docs.plot(x = 'party', y = 'doc', kind='scatter', color = politician_docs['color']);
    PROPS = {
        'boxprops':{'alpha':.3},
        'medianprops':{'alpha':.3},
        'whiskerprops':{'alpha':.3},
        'capprops':{'alpha':.3}
    }

    sns.catplot(
        y = 'party',
        x = 'doc',
        data = politician_docs,
        color = None,
        palette = cmap,
        height = 6,
        aspect = 1.8,
        order = sort,
        kind = 'box',
        orient = 'horizontal',
        showcaps = False,
        saturation = 1,
        flierprops = {
            'marker': 'x',
        }
        #boxprops={'alpha':.5},
        #**PROPS
    )

    #sns.stripplot(
    #    y = 'party',
    #    x = 'doc',
    #    data = politician_docs,
    #    palette = new_cmap,
    #    order = sort,
    #    orient = 'horizontal',
    #    alpha = 1
    #)
    parties = list(sort)
    outlier_list = []

    for party in parties:
        party_df = politician_docs.loc[politician_docs['party'] == party]
        outliers = calculate_outliers(party_df, 'doc')
        outlier_list.append(outliers)

    outliers_combined = pd.concat(outlier_list)
    
    for row in outliers_combined.itertuples():
        party_position = list(sort).index(row[2]) + random.uniform(-label_jitter, label_jitter)
        docs = row[4] + 10
        name = row[1]
        
        plt.text(
            docs,
            party_position,
            f'{name}',
            ha='left',
            va='center',
            path_effects=[pe.withStroke(linewidth=3, foreground='white')]
        )
    if title:
        plt.title(
            f'Distribution of MP utterance volumes by party ({source.title()})\n',
            weight = 'bold',
            size = 16
        )
    plt.xlabel('')
    plt.ylabel('')
    plt.show()