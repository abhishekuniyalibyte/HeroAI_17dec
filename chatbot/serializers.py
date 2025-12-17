from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
  restaurant_id = serializers.IntegerField()
  session_id = serializers.CharField(required=False, allow_blank=True)
  message = serializers.CharField()






class MenuChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    restaurant_id = serializers.IntegerField()

