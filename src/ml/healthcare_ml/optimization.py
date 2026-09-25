"""Seeded set-based genetic algorithm with tournament selection and elitism."""
import random
import numpy as np

def optimize(p):
    rng=random.Random(p.get('seed',42))
    candidates=p['candidates'];k=p['numberOfHospitals'];n=len(candidates)
    if not 1<=k<=n:raise ValueError('Requested sites exceed feasible candidate count')
    population=np.array(p['population'],dtype=float)
    demand=np.array(p['demand'],dtype=float)
    baseline=np.array(p['baselineMinutes'],dtype=float)
    matrix=np.array(p['candidateMinutes'],dtype=float)
    weights=p['objectiveWeights'];threshold=p.get('threshold',30)
    if matrix.shape!=(n,len(population)):raise ValueError('Invalid travel-time matrix')
    def evaluate(chromosome):
        times=np.minimum(baseline,np.min(matrix[list(chromosome)],axis=0))
        covered=times<=threshold
        improvement=np.maximum(0,baseline-times)
        contributions={'populationCoverage':float(population[covered].sum()/max(population.sum(),1)),
            'demandCoverage':float(demand[covered].sum()/max(demand.sum(),1)),
            'accessibilityImprovement':float(np.average(improvement/np.maximum(baseline,1),weights=np.maximum(population,1))),
            'roadAccess':float(np.mean([candidates[i]['road_access_score'] for i in chromosome])),
            'cost':float(np.mean([candidates[i]['cost_score'] for i in chromosome]))}
        score=sum(weights[key]*value*(-1 if key=='cost' else 1) for key,value in contributions.items())
        return score,contributions,times
    size=p.get('populationSize',100);generations=p.get('generations',150);mutation=p.get('mutationRate',.05)
    pool=[tuple(sorted(rng.sample(range(n),k))) for _ in range(size)]
    history=[]
    def tournament():
        return max(rng.sample(pool,min(3,len(pool))),key=lambda c:evaluate(c)[0])
    for generation in range(generations):
        pool.sort(key=lambda c:evaluate(c)[0],reverse=True)
        history.append(evaluate(pool[0])[0])
        next_pool=pool[:max(1,size//10)]
        while len(next_pool)<size:
            a,b=tournament(),tournament();union=list(set(a)|set(b))
            child=set(rng.sample(union,k))
            if rng.random()<mutation and k<n:
                child.remove(rng.choice(sorted(child)))
                child.add(rng.choice([i for i in range(n) if i not in child]))
            next_pool.append(tuple(sorted(child)))
        pool=next_pool
    best=max(pool,key=lambda c:evaluate(c)[0]);score,parts,times=evaluate(best)
    return {'selectedIndices':list(best),'fitness':score,'contributions':parts,'history':history,
            'populationServed':float(population[times<=threshold].sum()),'meanTravelMinutes':float(np.average(times,weights=np.maximum(population,1))),
            'baselineMeanTravelMinutes':float(np.average(baseline,weights=np.maximum(population,1))),'seed':p.get('seed',42)}
