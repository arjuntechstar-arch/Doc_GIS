def test_demo_has_varied_repeatable_synthetic_data(api):
    http, db = api

    response = http.post("/api/v1/admin/demo")
    assert response.status_code == 200, response.text
    assert response.json()["synthetic"] is True
    assert response.json()["version"] == "DEMO-CITY-v3"

    areas = list(
        db.population_areas.find({"area_code": {"$regex": "^DEMO-CITY-"}})
    )
    hospitals = list(
        db.hospitals.find({"external_id": {"$regex": "^DEMO-CITY-H"}})
    )
    roads = list(db.roads.find({"external_id": {"$regex": "^DEMO-CITY-R"}}))
    demand = list(
        db.healthcare_demand.find(
            {"source": "DEMO-CITY-v3"}
        ).sort("demand_value", 1)
    )

    assert len(areas) == 16
    assert len(hospitals) == 5
    assert len(roads) == 18
    assert len(demand) == 16 * 14
    assert len({area["population"] for area in areas}) > 10
    assert all(
        area["age_0_14"] + area["age_15_59"] + area["age_60_plus"]
        == area["population"]
        for area in areas
    )
    assert len({hospital["bed_capacity"] for hospital in hospitals}) > 1
    assert {road["road_type"] for road in roads} == {"arterial", "primary", "local"}
    assert len({road["speed_kmh"] for road in roads}) == 3
    assert demand[0]["demand_value"] < demand[-1]["demand_value"]

    first_counts = (
        db.population_areas.count_documents({"area_code": {"$regex": "^DEMO-CITY-"}}),
        db.hospitals.count_documents({"external_id": {"$regex": "^DEMO-CITY-H"}}),
        db.roads.count_documents({"external_id": {"$regex": "^DEMO-CITY-R"}}),
        db.healthcare_demand.count_documents({"source": "DEMO-CITY-v3"}),
    )
    assert http.post("/api/v1/admin/demo").status_code == 200
    assert first_counts == (
        db.population_areas.count_documents({"area_code": {"$regex": "^DEMO-CITY-"}}),
        db.hospitals.count_documents({"external_id": {"$regex": "^DEMO-CITY-H"}}),
        db.roads.count_documents({"external_id": {"$regex": "^DEMO-CITY-R"}}),
        db.healthcare_demand.count_documents({"source": "DEMO-CITY-v3"}),
    )
