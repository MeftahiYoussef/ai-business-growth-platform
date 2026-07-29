from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from common.serializers import MongoCompatMixin, dt

from .models import User


class UserSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    fullName = serializers.CharField(source="full_name")
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "_id", "fullName", "email", "role", "createdAt", "updatedAt"]

    def get_id(self, obj):
        return str(obj.id)

    def get_createdAt(self, obj):
        return dt(obj.created_at)

    def get_updatedAt(self, obj):
        return dt(obj.updated_at)


class RegisterSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=255, trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False, default=User.Role.OWNER)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["fullName"],
            role=validated_data.get("role", User.Role.OWNER),
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"].lower(), password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        attrs["user"] = user
        return attrs


def token_payload(user):
    refresh = RefreshToken.for_user(user)
    return {"token": str(refresh.access_token), "refreshToken": str(refresh)}
