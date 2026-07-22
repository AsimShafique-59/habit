from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import AudioContent, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "icon", "order", "is_active")


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "icon", "order", "is_active")


class AudioContentSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)

    class Meta:
        model = AudioContent
        fields = (
            "id", "title", "description", "category",
            "audio_url", "thumbnail_url",
            "duration_seconds", "tags", "is_published", "published_at",
        )

    def _build_url(self, request, file_field):
        if not file_field:
            return None
        if request:
            return request.build_absolute_uri(file_field.url)
        return file_field.url

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_audio_url(self, obj):
        return self._build_url(self.context.get("request"), obj.audio_file)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_thumbnail_url(self, obj):
        return self._build_url(self.context.get("request"), obj.thumbnail)


class AudioContentCreateSerializer(serializers.ModelSerializer):
    audio_file = serializers.FileField()
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = AudioContent
        fields = (
            "title", "description", "category_id",
            "audio_file", "thumbnail",
            "duration_seconds", "tags", "is_published",
        )

    def validate_tags(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("tags must be a JSON array.")
        return value
