from django.contrib import admin
from .models import Parent_acc, kid_acc,Post,FriendRequest

# Register models
admin.site.register(Parent_acc)
admin.site.register(kid_acc)
admin.site.register(Post)
admin.site.register(FriendRequest)


