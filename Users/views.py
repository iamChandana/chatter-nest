from django.shortcuts import render,redirect,get_object_or_404

from .models import Parent_acc,kid_acc,Post,FriendRequest,Comment,Like,ParentNotification,Message
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.hashers import check_password,make_password
from django.contrib.auth.models import User,auth
from django.db import IntegrityError
from django.http import JsonResponse


# Create your views here.
def main(request):
    return render(request,'main.html')

# KID SIGNUP

def kid_signup(request):
    if request.method == "POST":
        kid_id = request.POST.get('kid_id')  
        email = request.POST.get('email')  
        password = request.POST.get('password')  
        parent_code = request.POST.get('p_code')  
        profile = request.FILES.get('profile')  

        try:
            parent = Parent_acc.objects.get(parent_id=parent_code)  
            hashed_password = make_password(password)
            kid = kid_acc.objects.create(
                kid_id=kid_id,
                Email=email,
                password=hashed_password,
                profile=profile,
                parent=parent
            )
            request.session['kid_id'] = kid.kid_id  
            request.session['kid_email'] = kid.Email  
            return redirect('kid_dashboard')  

        except Parent_acc.DoesNotExist:
            return HttpResponse("Invalid Parent ID. Please enter a valid one.")

    return render(request, 'kid_signup.html')

# PARENT SIGNUP

def parent_signup(request):
    if request.method == "POST":
        parent_id = request.POST.get('name')  
        email = request.POST.get('email')  
        password = request.POST.get('password')  
        profile = request.FILES.get('profilePic')  

        if Parent_acc.objects.filter(parent_id=parent_id).exists():
            return render(request, 'parent_signup.html', {'error': 'Parent ID already exists. Choose a different one.'})

        hashed_password = make_password(password)

        try:
            parent = Parent_acc.objects.create(
                parent_id=parent_id,
                Email=email,
                password=hashed_password,
                profile=profile
            )
            request.session['parent_id'] = parent.parent_id  
            print(f"Session Set: {request.session['parent_id']}")  # Debugging

            return redirect('parent_dashboard')  # Redirect to dashboard

        except IntegrityError:
            return render(request, 'parent_signup.html', {'error': 'An error occurred. Try again.'})

    return render(request, 'parent_signup.html')


# KID DASHBOARD

def kid_dashboard(request):
    if 'kid_id' not in request.session:  
        return redirect('kid_login')

    kid_id = request.session.get('kid_id')  
    try:
        kid = kid_acc.objects.get(kid_id=kid_id)
        friends = kid.friends.all()
        friendrequest = FriendRequest.objects.all()
        posts = Post.objects.filter(user__in=[kid, *friends]).order_by('-created_at')
        liked_post_ids = Like.objects.filter(user=kid).values_list('post_id', flat=True)
        search_query = request.GET.get('search_query')
        search_results = None
        if search_query:
            search_results = kid_acc.objects.filter(kid_id__icontains=search_query)

        liked_posts = [post for post in posts if post.likes.filter(user=request.user).exists()]
        new_notifications = kid.received_requests.filter(status='pending', parent_approved=False).exists()

        return render(request, 'kid_dashboard.html', {
            'kid': kid,
            'posts': posts,
            'search_results': search_results,  
            'liked_posts': liked_post_ids,
            'new_notifications':new_notifications,
            'friendrequest': friendrequest,
        })

    except kid_acc.DoesNotExist:
        request.session.flush()  
        return redirect('kid_login')


# Add Kid 

def add_kid(request):
    return render(request,'add_kid.html')

# View Kids Post In Parent Dahsboard

def view_kid_posts(request):
    if 'parent_id' not in request.session:
        return redirect('parent_login')
    parent_id = request.session['parent_id']
    try:
        parent = Parent_acc.objects.get(parent_id=parent_id)  
        kids = kid_acc.objects.filter(parent=parent) 
        posts = Post.objects.filter(user__in=kids).order_by('-created_at')
    except Parent_acc.DoesNotExist:
        request.session.flush()  
        return redirect('parent_login')
    return render(request,'view_kid_posts.html', {'parent': parent, 'kids': kids,'posts':posts})

# KIDS FRIEND LIST PAGE

def kids_friends(request):
    parent_id = request.session.get('parent_id')

    try:
        parent = Parent_acc.objects.get(parent_id=parent_id)
        kids = kid_acc.objects.filter(parent=parent).prefetch_related('friends')

        return render(request, 'kids_friends.html', {
            'parent': parent,
            'kids': kids,
        })

    except Parent_acc.DoesNotExist:
        request.session.flush()
        return redirect('parent_login')

    return render(request,'kids_friends.html')

# nav 
def nav(request):
    return render(request,'nav.html')

# Profile page

def profile(request):
    if 'kid_id' not in request.session:
        return redirect('kid_login') 
    
    kid_id = request.session.get('kid_id')

    try:
        kid = kid_acc.objects.get(kid_id=kid_id)
        posts = Post.objects.filter(user=kid).order_by('-created_at')
        return render(request, 'profile.html', {
            'kid': kid,
            'posts': posts,
        })

    except kid_acc.DoesNotExist:
        request.session.flush()
        return redirect('kid_login')


# PARENT DASHBOARD

def parent_dashboard(request):
    if 'parent_id' not in request.session:  
        return redirect('parent_login')

    parent_id = request.session['parent_id']  
    try:
        parent = Parent_acc.objects.get(parent_id=parent_id)  
        kids = kid_acc.objects.filter(parent=parent) 
        posts = Post.objects.filter(user__in=kids).order_by('-created_at')
        notifications = ParentNotification.objects.filter(parent=parent, is_read=False).order_by('-timestamp')
        friend_requests = FriendRequest.objects.filter(to_kid__in=kids, parent_approved=None)
        pending_requests = FriendRequest.objects.filter(to_kid__in=kids, status='pending')
    except Parent_acc.DoesNotExist:
        request.session.flush()  
        return redirect('parent_login')

    return render(request, 'parent_dashboard.html', {'parent': parent, 'kids': kids,'posts':posts,'notifications': notifications,'friend_requests': friend_requests,'pending_requests': pending_requests,})

def view_kid_post_notification(request, notification_id):
    try:
        notification = ParentNotification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
        return redirect('view_kid_posts')  
    except ParentNotification.DoesNotExist:
        return HttpResponse("Notification not found", status=404)

def handle_parent_friend_request(request, req_id, action):
    friend_request = get_object_or_404(FriendRequest, id=req_id)

    if 'parent_id' not in request.session:
        return redirect('parent_login')

    if action == 'accept':
        friend_request.parent_approved = True
    elif action == 'reject':
        friend_request.parent_approved = False
    friend_request.save()
    
    return redirect('parent_dashboard')

def handle_request1(request, req_id, action):
    request_obj = get_object_or_404(FriendRequest, id=req_id)
    kid_id = request.session.get('kid_id')

    # if not kid_id or request_obj.to_kid.kid_id != kid_id:
    #     return HttpResponseForbidden()

    if request_obj.parent_approved != True:
        messages.error(request, "Your parent must approve this friend request first.")
        return redirect('kid_dashboard')

    if action == 'accept':
        request_obj.status = 'accepted'
        request_obj.from_kid.friends.add(request_obj.to_kid)
        request_obj.to_kid.friends.add(request_obj.from_kid)
    elif action == 'reject':
        request_obj.status = 'rejected'

    request_obj.save()
    return redirect('kid_dashboard')



# PARENT LOGIN

def parent_login(request):
    if request.method == "POST":
        email = request.POST.get('email')  
        password = request.POST.get('password') 

        try:
            parent = Parent_acc.objects.get(Email=email)  

            if check_password(password, parent.password): 
                request.session['parent_id'] = parent.parent_id  
                return redirect('parent_dashboard') 
            else:
                return HttpResponse("Invalid Password")  
        except Parent_acc.DoesNotExist:
            return HttpResponse("No account found with this email")  

    return render(request, 'parent_login.html')

# KID LOGIN

def kid_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            kid = kid_acc.objects.get(Email=email)
            if check_password(password, kid.password):  
                request.session["kid_id"] = kid.kid_id  
                return redirect("kid_dashboard")  
            else:
                return HttpResponse("Invalid Password", status=401)
        except kid_acc.DoesNotExist:
            return HttpResponse("Kid account not found", status=404)

    return render(request, "kid_login.html")

# CREATE POST 

def create_post(request):
    if "kid_id" not in request.session:  
        return redirect("kid_login")

    if request.method == "POST":
        description = request.POST.get("description")
        image = request.FILES.get("image")
        
        kid_id = request.session.get("kid_id")
        try:
            kid = kid_acc.objects.get(kid_id=kid_id)

            # Create and save post
            post = Post.objects.create(user=kid, description=description, image=image)
            ParentNotification.objects.create(
                parent=kid.parent,
                kid=kid,
                post=post
            )

            return redirect("kid_dashboard") 

        except kid_acc.DoesNotExist:
            return HttpResponse("Error: Kid account not found.", status=404)

    # Fetch posts of the logged-in user
    kid_id = request.session.get("kid_id")
    kid = kid_acc.objects.get(kid_id=kid_id)
    posts = Post.objects.filter(user=kid).order_by("-created_at")

    return render(request, "kid_dashboard.html", {"posts": posts})

def send_friend_request(request, to_kid_id):
    if 'kid_id' not in request.session:
        return redirect('kid_login')

    try:
        from_kid = kid_acc.objects.get(kid_id=request.session['kid_id'])
        to_kid = kid_acc.objects.get(kid_id=to_kid_id)

        # Prevent sending to self or duplicates
        if from_kid != to_kid:
            existing_request = FriendRequest.objects.filter(
                from_kid=from_kid,
                to_kid=to_kid,
                status='pending'
            ).first()

            if not existing_request:
                FriendRequest.objects.create(from_kid=from_kid, to_kid=to_kid)

    except kid_acc.DoesNotExist:
        return HttpResponse("Kid not found", status=404)

    return redirect('kid_dashboard')

def user_profile(request, kid_id):
    if 'kid_id' not in request.session:
        return redirect('kid_login')

    try:
        logged_in_kid = kid_acc.objects.get(kid_id=request.session['kid_id'])
        profile_kid = kid_acc.objects.get(kid_id=kid_id)

        # Check if request already exists or is accepted
        friend_request = FriendRequest.objects.filter(from_kid=logged_in_kid, to_kid=profile_kid).first()
        already_sent = friend_request and friend_request.status == 'pending'
        already_friends = friend_request and friend_request.status == 'accepted'

        return render(request, 'user_profile.html', {
            'profile_kid': profile_kid,
            'already_sent': already_sent,
            'already_friends': already_friends
        })

    except kid_acc.DoesNotExist:
        return HttpResponse("User not found", status=404)

def handle_request(request, request_id, action):
    if 'kid_id' not in request.session:
        return redirect('kid_login')

    try:
        friend_request = FriendRequest.objects.get(id=request_id)
        logged_in_kid = kid_acc.objects.get(kid_id=request.session['kid_id'])

        # Ensure only the recipient can act
        if friend_request.to_kid != logged_in_kid:
            return HttpResponse("Unauthorized", status=401)

        if action == "accept":
            friend_request.status = "accepted"
            
            # Add both kids to each other's friend list
            friend_request.from_kid.friends.add(friend_request.to_kid)
            friend_request.to_kid.friends.add(friend_request.from_kid)

        elif action == "reject":
            friend_request.status = "rejected"
        
        friend_request.save()
        return redirect('kid_dashboard')

    except FriendRequest.DoesNotExist:
        return HttpResponse("Request not found", status=404)
    
# post delete
def delete_post(request, post_id):
    if 'kid_id' not in request.session:
        return redirect('kid_login')

    kid = kid_acc.objects.get(kid_id=request.session['kid_id'])
    try:
        post = Post.objects.get(id=post_id)
        if post.user == kid:
            post.delete()
    except Post.DoesNotExist:
        pass

    return redirect('kid_dashboard')



# profile edit 
def edit_profile(request):
    if 'kid_id' not in request.session:
        return redirect('kid_login')

    kid_id = request.session['kid_id']
    try:
        kid = kid_acc.objects.get(kid_id=kid_id)

        if request.method == 'POST':
            bio = request.POST.get('bio')
            profile = request.FILES.get('profile')

            if bio:
                kid.bio = bio
            if profile:
                kid.profile = profile

            kid.save()
            return redirect('profile')

        return render(request, 'profile.html', {'kid': kid})
    
    except kid_acc.DoesNotExist:
        return HttpResponse("Kid not found", status=404)


# COMMENT

def comment_post(request, post_id):
    if 'kid_id' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=401)

    if request.method == 'POST':
        kid = kid_acc.objects.get(kid_id=request.session['kid_id'])
        content = request.POST.get('content')
        post = Post.objects.get(id=post_id)

        comment = Comment.objects.create(post=post, user=kid, text=content)

        return JsonResponse({
            'success': True,
            'comment_id': comment.id,
            'comment_text': comment.text,
            'user': kid.kid_id
        })

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)



def delete_comment(request, comment_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    if 'kid_id' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=401)

    try:
        comment = Comment.objects.get(id=comment_id)
        kid = kid_acc.objects.get(kid_id=request.session['kid_id'])

        if comment.user.kid_id == kid.kid_id:
            comment.delete()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    except Comment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Comment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# search
def search_kids(request):
    if 'kid_id' not in request.session:
        return JsonResponse({'error': 'Not logged in'}, status=401)

    logged_in_id = request.session['kid_id']
    query = request.GET.get('search_query', '').strip()
    results = []

    if query:
        kids = kid_acc.objects.filter(kid_id__icontains=query)
        for kid in kids:
            results.append({
                'kid_id': kid.kid_id,
                'profile': kid.profile.url if kid.profile else '',
                'is_self': kid.kid_id == logged_in_id
            })

    return JsonResponse({'results': results})



# LOGOUT VIEW FUNCTION

def parent_logout(request):
    if 'parent_id' in request.session:
        request.session.flush() 
    return redirect('main')  

def kid_logout(request):
    if 'kid_id' in request.session:
        request.session.flush()  
    return redirect('main') 

def parent_approve_request(request, request_id):
    req = get_object_or_404(FriendRequest, id=request_id)
    if request.method == 'POST':
        req.parent_approved = True
        req.save()
        return redirect('parent_dashboard')  # or wherever appropriate


# Parent Profile Change
def edit_parent_profile(request):
    if 'parent_id' not in request.session:
        return redirect('parent_login') 
    
    parent_id = request.session.get('parent_id')
    try:
        parent = Parent_acc.objects.get(parent_id = parent_id)

        if request.method == 'POST':
            profile = request.FILES.get('profile')

            if profile:
                parent.profile = profile
                parent.save()
                return redirect('parent_dashboard')

        return render(request, 'parent_dashboard.html', {'parent': parent})

    except Parent_acc.DoesNotExist:
        return HttpResponse("Parent not found", status=404)
    
from django.contrib.auth.hashers import check_password, make_password
from django.contrib import messages

def change_password(request):
    if 'parent_id' not in request.session:
        return redirect('parent_login')

    parent_id = request.session['parent_id']
    try:
        parent = Parent_acc.objects.get(parent_id=parent_id)

        if request.method == 'POST':
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not check_password(old_password, parent.password):
                messages.error(request, "Current password is incorrect.")
                return redirect('parent_dashboard')

            if new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
                return redirect('parent_dashboard')

            parent.password = make_password(new_password1)
            parent.save()
            messages.success(request, "Password changed successfully.")
            return redirect('parent_dashboard')

    except Parent_acc.DoesNotExist:
        return HttpResponse("Parent not found", status=404)



from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Message, User

def chat_page(request):
    if 'kid_id' not in request.session:
        return redirect('kid_login')

    kid_id = request.session['kid_id']
    try:
        kid = kid_acc.objects.get(kid_id=kid_id)
        friends = kid.friends.all()
        return render(request, 'chat.html', {
            'kid': kid,
            'friends': friends,
        })
    except kid_acc.DoesNotExist:
        return redirect('kid_login')


from .models import Message, kid_acc

def get_messages(request):
    print("Session:", request.session.items())  # Check session
    receiver_id = request.GET.get('receiver_id')
    print("Receiver ID:", receiver_id)

    if 'kid_id' not in request.session:
        print("Not logged in")
        return JsonResponse({'error': 'Not logged in'}, status=403)

    try:
        current_kid = kid_acc.objects.get(kid_id=request.session['kid_id'])
        friend = kid_acc.objects.get(kid_id=receiver_id)
    except kid_acc.DoesNotExist:
        print("Either sender or receiver does not exist")
        return JsonResponse({'error': 'Invalid user'}, status=400)

    messages = Message.objects.filter(
        sender__in=[current_kid, friend],
        receiver__in=[current_kid, friend]
    ).order_by('timestamp')

    data = [
        {
            'sender': msg.sender.kid_id,
            'receiver': msg.receiver.kid_id,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for msg in messages
    ]

    print("✅ Messages sent")
    return JsonResponse(data, safe=False)



from .models import Post, Like, kid_acc

def toggle_like(request, post_id):
    if request.method == 'POST':
        kid_id = request.session.get('kid_id')
        if not kid_id:
            return JsonResponse({'error': 'Not logged in'}, status=403)

        try:
            kid = kid_acc.objects.get(kid_id=kid_id)
            post = Post.objects.get(id=post_id)
            
        except (kid_acc.DoesNotExist, Post.DoesNotExist):
            return JsonResponse({'error': 'Invalid user or post'}, status=404)

        like, created = Like.objects.get_or_create(user=kid, post=post)
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        return JsonResponse({'liked': liked, 'like_count': post.likes.count()})

    return JsonResponse({'error': 'Invalid request'}, status=400)


def kid_change_password(request):
    if 'kid_id' not in request.session:
        return redirect('kid_login')  

    kid_id = request.session['kid_id']
    try:
        kid = kid_acc.objects.get(kid_id=kid_id)

        if request.method == 'POST':
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not check_password(old_password, kid.password):
                messages.error(request, "Current password is incorrect.")
                return redirect('profile')  # Or 'kid_dashboard'

            if new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
                return redirect('profile')

            kid.password = make_password(new_password1)
            kid.save()
            messages.success(request, "Password changed successfully.")
            return redirect('profile')

    except kid_acc.DoesNotExist:
        return HttpResponse("Kid not found", status=404)
    
# friend remove
def remove_friend(request, friend_id):
    if 'kid_id' not in request.session:
        messages.error(request, "You must be logged in as a kid to do this.")
        return redirect('kid_login')

    current_kid_id = request.session['kid_id']
    current_kid = get_object_or_404(kid_acc, kid_id=current_kid_id)
    friend = get_object_or_404(kid_acc, kid_id=friend_id)

    # Remove each other as friends
    current_kid.friends.remove(friend)
    friend.friends.remove(current_kid)

    messages.success(request, f'You removed {friend.kid_id} from your friend list.')
    return redirect('profile')

# block user
def block_friend(request, friend_id):
    friend = get_object_or_404(kid_acc, kid_id=friend_id)
    request.user.kid.blocked_users.add(friend)
    request.user.kid.friends.remove(friend)
    friend.friends.remove(request.user.kid)
    messages.success(request, f'You blocked {friend.kid_id}.')
    return redirect('profile')




