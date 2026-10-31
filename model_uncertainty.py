"""Exploratory paired monthly block bootstrap; not an untouched test."""
import numpy as np
import pandas as pd

def paired_interval(frame, metric='brier', repetitions=1000, seed=42):
    names=('DC + Bayesian (50/50)','Dixon-Coles')
    subset=frame[frame.model.isin(names)].copy()
    pivot=subset.pivot(index=['league','date','home','away'],columns='model',values=metric)
    if not set(names).issubset(pivot) or pivot.isna().any().any():
        raise ValueError('Unpaired model forecasts')
    paired=pivot.reset_index()
    paired['month']=pd.to_datetime(paired.date).dt.to_period('M').astype(str)
    paired['difference']=paired[names[0]]-paired[names[1]]
    blocks=[]
    for _,league in paired.groupby('league'):
        groups=[part.difference.to_numpy() for _,part in league.groupby('month')]
        if len(groups)<3:
            raise ValueError('Too few time blocks')
        blocks.append(groups)
    rng=np.random.default_rng(seed)
    draws=[]
    for _ in range(repetitions):
        total=0.0
        count=0
        for groups in blocks:
            for index in rng.integers(0,len(groups),len(groups)):
                values=groups[index]
                total+=values.sum()
                count+=len(values)
        draws.append(total/count)
    lower,upper=np.quantile(draws,[.025,.975])
    return {'metric':metric,'difference':float(paired.difference.mean()),
            'ci95_lower':float(lower),'ci95_upper':float(upper),
            'blocks':sum(map(len,blocks)),'paired_fixtures':len(paired),
            'repetitions':repetitions,'method':'paired monthly blocks within each league',
            'exploratory_only':True}
