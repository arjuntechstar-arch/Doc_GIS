from healthcare_ml.optimization import optimize

def test_genetic_algorithm_unique_reproducible_improvement():
    payload={'candidates':[{'road_access_score':1.,'cost_score':.5} for _ in range(6)],'numberOfHospitals':3,'population':[1000,2000,3000],'demand':[100,200,300],'baselineMinutes':[60,60,60],'candidateMinutes':[[5,60,60],[60,5,60],[60,60,5],[30,30,30],[55,55,55],[50,50,50]],'objectiveWeights':{'populationCoverage':.35,'demandCoverage':.25,'accessibilityImprovement':.25,'roadAccess':.1,'cost':.05},'populationSize':30,'generations':20,'mutationRate':.2,'seed':42}
    result=optimize(payload)
    assert result==optimize(payload)
    assert len(set(result['selectedIndices']))==3
    assert result['meanTravelMinutes']<result['baselineMeanTravelMinutes']
    assert all(b>=a for a,b in zip(result['history'],result['history'][1:]))
