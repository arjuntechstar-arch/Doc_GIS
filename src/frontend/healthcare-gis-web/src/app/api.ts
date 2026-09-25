import { Injectable, signal } from '@angular/core';

@Injectable({providedIn:'root'})
export class Api {
  readonly user = signal<any>(null);
  private access = '';
  private refresh = '';
  async login(username:string,password:string) {
    const pair=await this.request('/auth/login','POST',{username,password});
    this.access=pair.accessToken;this.refresh=pair.refreshToken;
    this.user.set(await this.request('/auth/me'));
  }
  logout(){this.access='';this.refresh='';this.user.set(null);}
  can(...roles:string[]){return this.user()?.role==='Admin'||roles.includes(this.user()?.role);}
  async request(path:string,method='GET',body?:any,retry=true):Promise<any>{
    const headers:Record<string,string>={};
    if(this.access)headers['Authorization']='Bearer '+this.access;
    if(body && !(body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch('/api/v1'+path,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined});
    if(response.status===401 && this.refresh && retry && path!='/auth/refresh'){
      try{const pair=await this.request('/auth/refresh','POST',{refreshToken:this.refresh},false);this.access=pair.accessToken;this.refresh=pair.refreshToken;return this.request(path,method,body,false);}
      catch{this.logout();throw new Error('Session expired. Please sign in again.');}
    }
    if(!response.ok){const error=await response.json().catch(()=>({detail:'Request failed'}));throw new Error(error.detail+(error.errors?' — '+error.errors.map((e:any)=>e.msg).join('; '):''));}
    return response.json();
  }
  async download(run:string,format:string){
    const response=await fetch('/api/v1/reports/export/'+run+'?format='+format,{headers:{Authorization:'Bearer '+this.access}});
    if(!response.ok)throw new Error((await response.json()).detail);
    const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='healthcare-'+run+'.'+format;a.click();URL.revokeObjectURL(url);
  }
}
