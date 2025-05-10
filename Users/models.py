from django.db import models
# from .models import kid_acc

# Create your models here.

class Parent_acc(models.Model):
    parent_id = models.CharField(max_length=100, primary_key=True)
    Email = models.EmailField(max_length=100)
    password = models.CharField(max_length=12)
    profile = models.ImageField(upload_to="Parent_profiles", blank=True, null=True)

class kid_acc(models.Model):
    kid_id = models.CharField(max_length=100, primary_key=True)
    Email = models.EmailField(max_length=100)
    password = models.CharField(max_length=12)
    profile = models.ImageField(upload_to="Kid_profiles", blank=True, null=True)
    parent = models.ForeignKey(Parent_acc, on_delete=models.CASCADE, related_name='kids')
    friends = models.ManyToManyField('self', symmetrical=True, blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, blank=True)

class Post(models.Model):
    user = models.ForeignKey(kid_acc, on_delete=models.CASCADE)  
    description = models.TextField()
    image = models.ImageField(upload_to="posts", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bio = models.TextField(blank=True, null=True)

class FriendRequest(models.Model):
    from_kid = models.ForeignKey('kid_acc',on_delete=models.CASCADE,related_name='sent_requests')
    to_kid = models.ForeignKey('kid_acc',on_delete=models.CASCADE,related_name='received_requests')
    status = models.CharField(max_length=10,choices=[('pending', 'Pending'),('accepted', 'Accepted'),('rejected', 'Rejected')],default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)
    parent_approved = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.from_kid.kid_id} to {self.to_kid.kid_id} ({self.status})"

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(kid_acc, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(kid_acc, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ParentNotification(models.Model):
    parent = models.ForeignKey(Parent_acc, on_delete=models.CASCADE, related_name='notifications')
    kid = models.ForeignKey(kid_acc, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)



from django.contrib.auth.models import User

class Message(models.Model):
    sender = models.ForeignKey(kid_acc, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(kid_acc, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Message from {self.sender} to {self.receiver} at {self.timestamp}'

