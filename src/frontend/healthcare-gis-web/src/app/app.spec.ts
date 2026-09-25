import { TestBed } from '@angular/core/testing';
import { App } from './app';
import { Api } from './api';
import { describe,it,expect } from 'vitest';

describe('Healthcare workspace',()=>{
  it('shows sign-in and hides planning actions until authenticated',async()=>{
    await TestBed.configureTestingModule({imports:[App]}).compileComponents();
    const fixture=TestBed.createComponent(App);fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Sign in to your workspace');
    expect(fixture.nativeElement.textContent).not.toContain('Load synthetic demo');
  });
  it('enforces frontend role visibility',()=>{
    const api=new Api();api.user.set({role:'Viewer'});expect(api.can('GISAnalyst')).toBe(false);
    api.user.set({role:'Admin'});expect(api.can('GISAnalyst')).toBe(true);
  });
});
