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
  it('offers self-registration and checks password confirmation before submitting',async()=>{
    await TestBed.configureTestingModule({imports:[App]}).compileComponents();
    const fixture=TestBed.createComponent(App);const app=fixture.componentInstance;
    app.showAuth('register');fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Start your planning workspace');
    app.registration={username:'new-user',email:'new@example.test',password:'testing-password-123',confirmPassword:'different-password'};
    await app.register();
    expect(app.error()).toBe('Passwords do not match.');
  });
});
