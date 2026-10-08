"""Relative match evidence. Never an absolute/human Elo assignment."""
import math,random
def delta(score):return None if score<=0 or score>=1 else 400*math.log10(score/(1-score))
def summarize(run):
    results=run['results'];w=sum(r['score']==1 for r in results);d=sum(r['score']==.5 for r in results);l=sum(r['score']==0 for r in results);unfinished=sum(r['score'] is None for r in results)
    n=w+d+l;score=(w+.5*d)/n if n else None
    out=dict(wins=w,draws=d,losses=l,unfinished=unfinished,completed=n,score=score,relative_elo=None,interval=None,promotable=False)
    unresolved=run['games']-n
    points=w+.5*d
    bounds=[points/run['games'],(points+unresolved)/run['games']]
    out.update(unresolved=unresolved,score_bounds=bounds,elo_bounds=[delta(bounds[0]),delta(bounds[1])])
    # Excluding capped games biases estimates. Withhold Elo/promotion if any are unresolved.
    if not run['finished'] or unfinished or n!=run['games'] or not n:return out
    pairs=[(results[i]['score']+results[i+1]['score'])/2 for i in range(0,n,2)]
    rng=random.Random(314)
    means=sorted(sum(rng.choice(pairs) for _ in pairs)/len(pairs) for _ in range(2000))
    lo,hi=means[49],means[1949]
    out.update(relative_elo=delta(score),interval=[lo,hi],elo_interval=[delta(lo),delta(hi)],
               promotable=n>=40 and lo>.5 and run['opponent']==run['champion_at_start'])
    return out
