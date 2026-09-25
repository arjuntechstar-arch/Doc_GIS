import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { Api } from './api';
import { GisMap } from './map';

@Component({selector:'app-root',imports:[CommonModule,FormsModule,MatButtonModule,MatProgressBarModule,GisMap],templateUrl:'./app.html',styleUrl:'./app.css'})
export class App {
  api=inject(Api);page=signal('Dashboard');busy=signal(false);error=signal('');notice=signal('');dashboard=signal<any>(null);items=signal<any[]>([]);history=signal<any[]>([]);models=signal<any[]>([]);scenarios=signal<any[]>([]);current=signal<any>(null);users=signal<any[]>([]);
  pages=['Dashboard','GIS Explorer','Hospitals','Population','Accessibility','Demand Prediction','Candidate Sites','Optimization','Recommendations','Reports','Administration'];
  username='';password='';importKind='hospitals';modelVersion='';predictionYear=2027;selectedRun='';hospitalId='';total=signal(0);listPage=1;search='';
  hospital={name:'',hospital_type:'General',bed_capacity:100,emergency_available:true,specialty_count:5,status:'Active',longitude:80.27,latitude:13.08};
  analysis={analysisName:'Healthcare accessibility baseline',travelMode:'road',areaIds:[] as string[],weights:{distance:.3,travelTime:.3,capacity:.2,emergency:.2},travelTimeThreshold:30};
  candidate={minPopulation:5000,minDemand:1000,minRoadAccessScore:.5,minDistanceFromExistingHospitalKm:3,gridSpacingKm:1.5,excludedLandUse:['water','protected_forest']};
  optimization={numberOfHospitals:3,populationSize:60,generations:60,mutationRate:.05,seed:42,proposedBedCapacity:150,objectiveWeights:{populationCoverage:.35,demandCoverage:.25,accessibilityImprovement:.25,roadAccess:.1,cost:.05}};
  newUser={username:'',email:'',password:'',role:'Viewer'};
  selectedAreas='';
  runs=computed(()=>{const d=this.dashboard()?.latest||{};return {accessibility:d.accessibility?.id,underserved:d.accessibility?.id,demand:d.predict?.id,candidates:d.candidates?.id,recommendations:d.optimization?.id};});
  keys=Object.keys;
  async act(fn:()=>Promise<void>){this.error.set('');this.busy.set(true);try{await fn();}catch(e:any){this.error.set(e.message);}finally{this.busy.set(false);}}
  async login(){await this.act(async()=>{await this.api.login(this.username,this.password);this.password='';await this.refresh();});}
  logout(){this.api.logout();this.dashboard.set(null);this.current.set(null);}
  async refresh(){this.dashboard.set(await this.api.request('/dashboard'));this.history.set((await this.api.request('/analysis/history')).items);}
  async select(page:string){this.page.set(page);this.items.set([]);this.listPage=1;await this.act(async()=>{await this.refresh();if(['Hospitals','Population'].includes(page))await this.loadItems();if(page==='Demand Prediction'){this.models.set((await this.api.request('/demand/models')).items);this.modelVersion=this.models()[0]?.model_version||'';const id=this.runs().demand;if(id)this.items.set((await this.api.request('/demand/predictions?runId='+id)).items);}if(page==='Candidate Sites')this.items.set((await this.api.request('/candidate-sites'+(this.runs().candidates?'?runId='+this.runs().candidates:''))).items);if(page==='Recommendations'&&this.runs().recommendations)this.items.set((await this.api.request('/optimization/runs/'+this.runs().recommendations+'/recommendations')).items);if(page==='Accessibility'&&this.runs().accessibility)this.items.set((await this.api.request('/accessibility/results?runId='+this.runs().accessibility)).items);if(page==='Reports')this.scenarios.set((await this.api.request('/reports/scenarios')).scenarios);if(page==='Administration'&&this.api.can())this.users.set((await this.api.request('/admin/users')).items);});}
  async loadItems(){const path=this.page()==='Population'?'/population/areas':'/hospitals';const data=await this.api.request(path+'?page='+this.listPage+'&search='+encodeURIComponent(this.search));this.items.set(data.items);this.total.set(data.total);}
  async next(delta:number){this.listPage+=delta;await this.act(()=>this.loadItems());}
  async seed(){if(!confirm('Load the clearly labeled synthetic demonstration dataset into this database?'))return;await this.act(async()=>{await this.api.request('/admin/demo','POST',{});await this.refresh();this.notice.set('Synthetic demonstration data loaded.');});}
  async importFile(event:Event){const input=event.target as HTMLInputElement;const file=input.files?.[0];if(!file)return;await this.act(async()=>{const form=new FormData();form.append('file',file);const r=await this.api.request('/'+this.importKind+'/import','POST',form);this.notice.set(`${r.imported} records imported`);await this.refresh();if(['Hospitals','Population'].includes(this.page()))await this.loadItems();});input.value='';}
  async saveHospital(){await this.act(async()=>{const {longitude,latitude,...h}=this.hospital;await this.api.request('/hospitals'+(this.hospitalId?'/'+this.hospitalId:''),this.hospitalId?'PUT':'POST',{...h,location:{type:'Point',coordinates:[Number(longitude),Number(latitude)]}});this.hospitalId='';this.hospital.name='';await this.loadItems();await this.refresh();});}
  editHospital(item:any){this.hospitalId=item.id;this.hospital={name:item.name,hospital_type:item.hospital_type,bed_capacity:item.bed_capacity,emergency_available:item.emergency_available,specialty_count:item.specialty_count,status:item.status,longitude:item.location.coordinates[0],latitude:item.location.coordinates[1]};}
  async deleteHospital(id:string){if(!confirm('Deactivate this hospital? Previous analyses will be preserved.'))return;await this.act(async()=>{await this.api.request('/hospitals/'+id,'DELETE');await this.loadItems();});}
  async run(path:string,body:any){await this.act(async()=>{if(path==='/accessibility/analyze')body={...body,areaIds:this.selectedAreas.split(',').map(x=>x.trim()).filter(Boolean)};const job=await this.api.request(path,'POST',body);this.current.set(job);this.notice.set('Job queued. You may navigate while it runs.');void this.poll(job.id);});}
  async poll(id:string){try{for(let i=0;i<300;i++){const job=await this.api.request('/jobs/'+id);this.current.set(job);if(['COMPLETED','FAILED','CANCELLED'].includes(job.status)){if(job.status==='FAILED')this.error.set(job.error||'Job failed');else this.notice.set('Job '+job.status.toLowerCase());await this.select(this.page());return;}await new Promise(r=>setTimeout(r,1500));}this.error.set('Polling stopped after 7.5 minutes. Check Analysis history for current status.');}catch(e:any){this.error.set(e.message);}}
  async cancel(){await this.act(async()=>{await this.api.request('/jobs/'+this.current().id+'/cancel','POST',{});});}
  async download(format:string){await this.act(()=>this.api.download(this.selectedRun,format));}
  async addUser(){await this.act(async()=>{await this.api.request('/admin/users','POST',this.newUser);this.newUser.password='';this.users.set((await this.api.request('/admin/users')).items);});}
  async updateUser(user:any){await this.act(async()=>{await this.api.request('/admin/users/'+user.id,'PUT',{role:user.role,is_active:user.is_active});this.notice.set('User access updated.');});}
  format(value:any){return value==null?'—':typeof value==='number'?value.toLocaleString(undefined,{maximumFractionDigits:2}):typeof value==='object'?JSON.stringify(value):String(value);}
}
