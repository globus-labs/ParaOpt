from functools import wraps
import os
from flask import session, request, redirect, url_for

from config import _load_funcx_client, in_production

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    # check auth if in prod
    # if not in_production:
    #   return f(*args, **kwargs)
    # if user already has auth'd session, continue call
    if not in_production or session.get('is_authenticated') == True:
      return f(*args, **kwargs)
    # if use set Authorization header, check if token is valid
    elif 'Authorization' in request.headers:
      at = request.headers.get('Authorization').replace('Bearer', '').strip()
      if at:
        client = _load_funcx_client()
        data = client.oauth2_token_introspect(at)
        if data.get('active', False) != True:
          return "Invalid token - token not active for client", 401
        else: # valid token
          return f(*args, **kwargs)
    # no auth, redirect to login
    else:
      return redirect(url_for('login', next=request.url))
  return decorated_function
