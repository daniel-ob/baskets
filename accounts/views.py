from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from accounts.forms import CustomUserForm


@login_required
def profile(request):
    """User profile"""

    user = get_object_or_404(get_user_model(), id=request.user.id)
    form = CustomUserForm(instance=user)
    message = ""

    if request.method == "POST":
        form = CustomUserForm(instance=user, data=request.POST)
        if form.is_valid():
            user.save()
            message = "Vos coordonnées ont été mises à jour avec succès."

    # Render user information. Also displays form errors from POST if there were any
    return render(
        request,
        "account/profile.html",
        {"message": message, "form": form},
    )
