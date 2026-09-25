def test_auth_roles_refresh_and_validation(api):
    http, db = api
    assert http.get('/health').status_code == 200
    assert http.get('/api/v1/auth/me').json()['role'] == 'Admin'
    assert http.post('/api/v1/admin/users', json={'username':'viewer','password':'testing-password-123','email':'v@example.test','role':'Viewer'}).status_code == 201
    login = http.post('/api/v1/auth/login', json={'username':'viewer','password':'testing-password-123'}).json()
    assert http.get('/api/v1/admin/users', headers={'Authorization': 'Bearer '+login['accessToken']}).status_code == 403
    assert http.post('/api/v1/auth/refresh',json={'refreshToken': login['refreshToken']}).status_code == 200
    assert http.post('/api/v1/auth/refresh',json={'refreshToken': login['refreshToken']}).status_code == 401
    assert http.post('/api/v1/auth/login', json={'username':{'$ne':None},'password':'bad'}).status_code == 422
    assert 'password_hash' not in http.get('/api/v1/auth/me').text
