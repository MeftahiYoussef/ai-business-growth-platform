from .models import BusinessMember

WRITE_ROLES = {
    BusinessMember.Role.OWNER,
    BusinessMember.Role.ADMIN,
    BusinessMember.Role.MANAGER,
}

APPROVER_ROLES = {
    BusinessMember.Role.OWNER,
    BusinessMember.Role.ADMIN,
    BusinessMember.Role.MANAGER,
}


def role_for(user, business):
    if business.owner_id == user.id:
        return BusinessMember.Role.OWNER
    membership = BusinessMember.objects.filter(user=user, business=business).first()
    return membership.role if membership else None


def can_manage_team(user, business):
    return role_for(user, business) in {BusinessMember.Role.OWNER, BusinessMember.Role.ADMIN}


def can_write_content(user, business):
    return role_for(user, business) in WRITE_ROLES | {BusinessMember.Role.CREATOR}


def can_approve_content(user, business):
    return role_for(user, business) in APPROVER_ROLES
