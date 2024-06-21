import sys
print(sys.path)
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routers.routes import handle_invite_login

result = handle_invite_login("RandomGuy", "957400978")
print(result)
