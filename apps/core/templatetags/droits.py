from django import template

register = template.Library()


@register.filter
def peut(utilisateur, permission):
    """Usage : {% if user|peut:"pelerins.creer" %} ... {% endif %}"""
    return bool(getattr(utilisateur, "is_authenticated", False)) and utilisateur.a_permission(permission)
