"""Empirical-Bayes shrinkage goal model for 1X2 probabilities.

Gamma-Poisson posterior means for team venue attack and opponent defence,
with league-rate priors. No bookmaker inputs.
"""
import numpy as np
from scipy.stats import poisson

class BayesianGoals:
    def __init__(self, prior_matches=8.0, max_goals=12):
        self.prior_matches=float(prior_matches)
        self.max_goals=int(max_goals)
        if self.prior_matches<=0 or self.max_goals<3:
            raise ValueError('Invalid Bayesian prior configuration')

    def fit(self, matches):
        if len(matches)<20:
            raise ValueError('Need at least 20 training matches')
        self.home_mean=max(0.1,float(matches.FTHG.mean()))
        self.away_mean=max(0.1,float(matches.FTAG.mean()))
        self.teams=set(matches.HomeTeam)|set(matches.AwayTeam)
        self.hf={};self.ha={};self.af={};self.aa={}
        for row in matches.itertuples():
            for table,key,value in (
                (self.hf,row.HomeTeam,row.FTHG),(self.ha,row.HomeTeam,row.FTAG),
                (self.af,row.AwayTeam,row.FTAG),(self.aa,row.AwayTeam,row.FTHG)):
                count,total=table.get(key,(0,0.0))
                table[key]=(count+1,total+float(value))
        return self

    def _posterior(self,table,team,prior):
        count,total=table.get(team,(0,0.0))
        return (total+self.prior_matches*prior)/(count+self.prior_matches)

    def predict(self,home,away):
        if home not in self.teams or away not in self.teams:
            raise ValueError('Unseen team')
        home_attack=self._posterior(self.hf,home,self.home_mean)
        away_defence=self._posterior(self.aa,away,self.home_mean)
        away_attack=self._posterior(self.af,away,self.away_mean)
        home_defence=self._posterior(self.ha,home,self.away_mean)
        lam=np.clip(home_attack*away_defence/self.home_mean,0.15,6.0)
        mu=np.clip(away_attack*home_defence/self.away_mean,0.15,6.0)
        goals=np.arange(self.max_goals+1)
        grid=np.outer(poisson.pmf(goals,lam),poisson.pmf(goals,mu))
        grid/=grid.sum()
        return np.array([np.tril(grid,-1).sum(),np.trace(grid),np.triu(grid,1).sum()])
