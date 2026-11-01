"""Derive goal market probabilities from a normalized pre-match score grid.

The input grid rows are home goals, columns away goals. This module never
uses results, odds or post-kickoff data to generate forecasts.
"""
import math
import numpy as np

def market_probabilities(grid, top_n=6):
    grid=np.asarray(grid,dtype=float)
    if grid.ndim!=2 or min(grid.shape)<4 or not np.isfinite(grid).all() or (grid<0).any():
        raise ValueError('Invalid score probability grid')
    total=float(grid.sum())
    if total<=0:
        raise ValueError('Empty score probability grid')
    grid=grid/total
    h,a=np.indices(grid.shape)
    markets={
        'btts_yes':float(grid[(h>0)&(a>0)].sum()),
        'btts_no':float(grid[(h==0)|(a==0)].sum()),
    }
    for threshold in (1.5,2.5,3.5):
        tag=str(threshold).replace('.','_')
        over=float(grid[(h+a)>threshold].sum())
        markets['over_'+tag]=over
        markets['under_'+tag]=1-over
    for team,counts in [('home',h),('away',a)]:
        for threshold in (0.5,1.5,2.5):
            tag=str(threshold).replace('.','_')
            over=float(grid[counts>threshold].sum())
            markets[team+'_over_'+tag]=over
            markets[team+'_under_'+tag]=1-over
    scores=sorted(((int(i),int(j),float(grid[i,j])) for i,j in np.ndindex(grid.shape)),key=lambda x:(-x[2],x[0],x[1]))[:top_n]
    return {'markets':markets,'correct_scores':[{'home_goals':i,'away_goals':j,'probability':p} for i,j,p in scores],
            'grid_max_goals':list(np.array(grid.shape)-1),'grid_truncated_and_renormalized':True}

def validate_goal_markets(data):
    if not isinstance(data,dict) or not isinstance(data.get('markets'),dict):
        raise ValueError('Missing goal markets')
    m=data['markets']
    for left,right in [('btts_yes','btts_no')]+[
        (prefix+'over_'+tag,prefix+'under_'+tag)
        for prefix in ('','home_','away_')
        for tag in ('0_5','1_5','2_5','3_5')
        if (prefix=='' and tag!='0_5') or (prefix!='' and tag!='3_5')
    ]:
        if left not in m or right not in m:
            raise ValueError('Missing complementary market')
        x,y=m[left],m[right]
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in (x,y)):
            raise ValueError('Invalid market probability')
        if abs(x+y-1)>1e-6:
            raise ValueError('Market probabilities do not sum to one')
    scores=data.get('correct_scores')
    if not isinstance(scores,list) or not scores:
        raise ValueError('Missing correct-score forecasts')
    for score in scores:
        if any(not isinstance(score.get(k),int) or isinstance(score[k],bool) or score[k]<0 for k in ('home_goals','away_goals')):
            raise ValueError('Invalid correct score')
        p=score.get('probability')
        if not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1:
            raise ValueError('Invalid correct-score probability')
    if sum(x['probability'] for x in scores)>1+1e-6:
        raise ValueError('Correct-score probabilities exceed one')
    return True
