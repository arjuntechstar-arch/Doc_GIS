from healthcare_ml.models import train,predict,FEATURES

def test_chronological_models_and_artifact(tmp_path,monkeypatch):
    monkeypatch.setenv('MODEL_STORAGE',str(tmp_path))
    rows=[]
    for year in range(2012,2025):
        for area in range(4):
            row={f:float(area+1) for f in FEATURES}
            row.update(year=year,target=float((year-2000)*100+area*10),historical_demand=float((year-2001)*100+area*10),synthetic=True)
            rows.append(row)
    result=train(rows)
    assert set(result['comparison'])=={'linear_regression','random_forest','xgboost'}
    split=result['split_years']
    assert max(split['train'])<min(split['validation'])<min(split['test'])
    assert result['metrics']['mae']>=0
    assert len(predict(result['model_version'],rows[:2])['predictions'])==2
