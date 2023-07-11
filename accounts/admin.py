from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import StringAgg
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


from accounts.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "groups_str", "is_active", "is_staff")
    fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "groups",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            groups_=StringAgg("groups__name", ", ")
        )  # PostgreSQL specific aggregation function
        return qs

    @admin.display(description=_("groups"), ordering="groups_")
    def groups_str(self, obj):
        return obj.groups_


# Custom Group admin
admin.site.unregister(Group)


class MembershipInline(admin.TabularInline):
    model = Group.user_set.through
    verbose_name_plural = _("List of group members")
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "members_count", "email")
    exclude = ("permissions",)
    inlines = [MembershipInline]

    class Media:
        css = {"all": ("baskets/css/hide_admin_original.css",)}

    @admin.display(description=_("number of members"))
    def members_count(self, obj):
        return obj.user_set.count()

    @staticmethod
    def email(group):
        emails_str = ", ".join(group.user_set.values_list("email", flat=True))
        link_text = _("email the group")
        return (
            format_html(f"<a href='mailto:?bcc={emails_str}'>{link_text}</a>")
            if emails_str
            else ""
        )
