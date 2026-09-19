from typing import Any, ClassVar

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields: ClassVar[tuple[str, ...]] = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'pin_code',
            'preferred_language',
            'keyboard_layout',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields: ClassVar[tuple[str, ...]] = (
            'id',
            'created_at',
            'updated_at',
        )
        extra_kwargs: ClassVar[dict[str, dict[str, Any]]] = {
            'pin_code': {'write_only': True},
        }

    def create(self, validated_data):
        pin_code = validated_data.pop('pin_code', None)
        user = User.objects.create(**validated_data)
        if pin_code:
            user.set_pin(pin_code)
            user.save(update_fields=['pin_code', 'updated_at'])
        return user

    def update(self, instance, validated_data):
        pin_code = validated_data.pop('pin_code', None)
        instance = super().update(instance, validated_data)
        if pin_code:
            instance.set_pin(pin_code)
            instance.save(update_fields=['pin_code', 'updated_at'])
        return instance


class UserProfileSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields: ClassVar[tuple[str, ...]] = (
            'id',
            'username',
            'role',
            'is_active',
            'created_at',
            'updated_at',
        )


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=200)
    pin = serializers.CharField(max_length=6)


class LogoutResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=300, write_only=True)
    pin = serializers.CharField(max_length=6, min_length=4, write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields: ClassVar[tuple[str, ...]] = ('full_name', 'email', 'pin')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Cette adresse e-mail est déjà utilisée.')
        return value.lower()

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'Le code PIN doit contenir uniquement des chiffres.'
            )
        return value

    def create(self, validated_data):
        full_name = validated_data.pop('full_name').strip()
        name_parts = full_name.split(None, 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        username_base = validated_data['email'].split('@', 1)[0].lower()
        username = username_base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f'{username_base}{suffix}'

        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            first_name=first_name,
            last_name=last_name,
            password=None,
            role='viewer',
        )
        user.set_pin(validated_data['pin'])
        user.save(update_fields=['pin_code', 'updated_at'])
        return user


class PinResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PinResetConfirmSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()
    pin = serializers.CharField(max_length=6, min_length=4)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'Le code PIN doit contenir uniquement des chiffres.'
            )
        return value
