import requests

API_KEY = 'AIzaSyAf4_4eptXy6MH13zZdKjOFjCjrjuhzzQk'
data = {
    "email": "Sandy@gmail.com",
    "password": "Sandy@1",
    "returnSecureToken": True
}
url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
resp = requests.post(url, json=data)
id_token = resp.json().get("idToken")
print(id_token)
