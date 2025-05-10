import os
from django.core.asgi import get_asgi_application
import Users.routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack  # ✅ use session middleware instead of auth

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Social_media.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionMiddlewareStack(  # ✅ updated here
        URLRouter(
            Users.routing.websocket_urlpatterns
        )
    ),
})
