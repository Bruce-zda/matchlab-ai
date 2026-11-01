"""Evaluate archived goal-market probabilities against independently settled scores."""
def evaluate_goal_markets(forecast,settlement):
    if forecast['snapshot_id']!=settlement['snapshot_id']:
        raise ValueError('Mismatched snapshots')
    if 'goal_markets' not in forecast:
        return []
    from goal_markets import validate_goal_markets
    data=forecast['goal_markets']
    validate_goal_markets(data)
    h,a=settlement['home_goals'],settlement['away_goals']
    if not all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in (h,a)):
        raise ValueError('Invalid final score')
    outcomes={'btts_yes':int(h>0 and a>0),'btts_no':int(h==0 or a==0)}
    for name,t in [('1_5',1.5),('2_5',2.5),('3_5',3.5)]:
        outcomes['over_'+name]=int(h+a>t)
        outcomes['under_'+name]=1-outcomes['over_'+name]
    for side,g in [('home',h),('away',a)]:
        for name,t in [('0_5',0.5),('1_5',1.5),('2_5',2.5)]:
            outcomes[side+'_over_'+name]=int(g>t)
            outcomes[side+'_under_'+name]=1-outcomes[side+'_over_'+name]
    return [{'market':key,'probability':p,'actual':outcomes[key],
             'brier':(p-outcomes[key])**2}
            for key,p in data['markets'].items() if key in outcomes]
