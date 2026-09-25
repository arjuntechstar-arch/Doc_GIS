"""Ellipsoidal distance and road-graph routing. No degree-based distance arithmetic."""
import math
import statistics
import networkx as nx
from pyproj import Geod, CRS, Transformer
from shapely.geometry import shape
from shapely.ops import transform

GEOD = Geod(ellps="WGS84")

def distance(a,b):
    return abs(GEOD.inv(a[0],a[1],b[0],b[1])[2])/1000

def center(geometry):
    geom=shape(geometry)
    anchor=geom.representative_point()
    crs=CRS.from_proj4(f"+proj=aeqd +lat_0={anchor.y} +lon_0={anchor.x} +datum=WGS84 +units=m")
    forward=Transformer.from_crs(4326,crs,always_xy=True).transform
    backward=Transformer.from_crs(crs,4326,always_xy=True).transform
    point=transform(backward,transform(forward,geom).centroid)
    if not geom.covers(point): point=anchor
    return [point.x,point.y]

class RoadGraph:
    """Road intersections must be noded in the imported network; grade-separated crossings stay separate."""
    def __init__(self, roads):
        self.graph=nx.DiGraph()
        for road in roads:
            coords=road["geometry"]["coordinates"]
            for a,b in zip(coords,coords[1:]):
                a,b=tuple(round(v,8) for v in a),tuple(round(v,8) for v in b)
                minutes=distance(a,b)/road["speed_kmh"]*60
                if not self.graph.has_edge(a,b) or self.graph[a][b]["weight"]>minutes:
                    self.graph.add_edge(a,b,weight=minutes)
                if not road.get("one_way",False): self.graph.add_edge(b,a,weight=minutes)
        self.nodes=list(self.graph.nodes)
        self.cache={}
    def snap(self, point):
        if not self.nodes: return None,math.inf
        node=min(self.nodes,key=lambda n:distance(point,n))
        return node,distance(point,node)
    def minutes(self,a,b):
        start,offset_a=self.snap(a)
        end,offset_b=self.snap(b)
        if start is None or offset_a>5 or offset_b>5: return None
        if start not in self.cache: self.cache[start]=nx.single_source_dijkstra_path_length(self.graph,start)
        road=self.cache[start].get(end)
        return None if road is None else road+(offset_a+offset_b)/5*60

def classify(score):
    return "Critical" if score<.25 else "Poor" if score<.5 else "Moderate" if score<.75 else "Good"

def summarize(results, areas):
    populations={str(a["_id"]):a["population"] for a in areas}
    total=sum(populations.values())
    covered=sum(populations.get(str(r["area_id"]),0)*r["population_coverage"] for r in results)
    times=[r["travel_time_minutes"] for r in results if r.get("travel_time_minutes") is not None]
    return {"population":total,"coveredPopulation":round(covered),"coveragePercent":100*covered/max(total,1),
        "underservedPopulation":sum(populations.get(str(r["area_id"]),0) for r in results if r["accessibility_index"]<.5),
        "criticalAreas":sum(r["classification"]=="Critical" for r in results),
        "averageTravelTimeMinutes":statistics.mean(times) if times else None,
        "medianTravelTimeMinutes":statistics.median(times) if times else None,
        "unreachableAreas":sum(r.get("travel_time_minutes") is None for r in results),
        "meanAccessibilityIndex":statistics.mean(r["accessibility_index"] for r in results) if results else 0,
        "meanCapacityScore":statistics.mean(r["capacity_score"] for r in results) if results else 0,
        "distribution":{name:sum(r["classification"]==name for r in results) for name in ["Critical","Poor","Moderate","Good"]}}

def analyze(areas,hospitals,graph,weights,travel_mode="road",threshold=30):
    results=[]
    for area in areas:
        point=center(area["geometry"])
        closest=min(hospitals,key=lambda h:distance(point,h["location"]["coordinates"]),default=None)
        reachable=[]
        if travel_mode=="road":
            for h in hospitals:
                minutes=graph.minutes(point,h["location"]["coordinates"])
                if minutes is not None: reachable.append((minutes,h))
        chosen=min(reachable,key=lambda pair:pair[0]) if reachable else None
        hospital=chosen[1] if chosen else closest if travel_mode=="distance" else None
        km=distance(point,closest["location"]["coordinates"]) if closest else None
        minutes=chosen[0] if chosen else None
        cap=min(1,hospital["bed_capacity"]/max(area["population"]*3/1000,1)) if hospital else 0
        emergency=float(bool(hospital and hospital["emergency_available"]))
        score={"distance":max(0,1-km/20) if km is not None else 0,
               "travelTime":max(0,1-minutes/60) if minutes is not None else 0,"capacity":cap,"emergency":emergency}
        active={k:v for k,v in weights.items() if k!="travelTime" or travel_mode=="road"}
        denominator=sum(active.values())
        index=sum(score[k]*v for k,v in active.items())/denominator if denominator else 0
        row={"area_id":area["_id"],"distance_km":km,"travel_time_minutes":minutes,
             "capacity_score":cap,"emergency_score":emergency,
             "population_coverage":float(minutes<=threshold) if minutes is not None else float(km<=10) if km is not None and travel_mode=="distance" else 0.,
             "accessibility_index":index,"classification":classify(index)}
        if hospital: row["nearest_hospital_id"]=hospital["_id"]
        results.append(row)
    return results
