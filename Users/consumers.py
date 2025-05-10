import json
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        kid_id = self.scope["session"].get("kid_id")
        print("KID ID FROM SESSION:", kid_id)

        if not kid_id:
            await self.close()
            return

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
            sender_id = self.scope["session"]["kid_id"]  # Use session ID

            # Validate sender
            if text_data_json.get('sender_id') != sender_id:
                await self.close(code=4001)
                return

            # Save to DB
            await self.save_message(
                sender_id,
                text_data_json['receiver_id'],
                message
            )

            # Broadcast message
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': sender_id,
                    'timestamp': str(datetime.now())
                }
            )

        except Exception as e:
            print(f"Error: {str(e)}")
            await self.close(code=4002)

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
        from .models import Message, kid_acc
        sender = kid_acc.objects.get(kid_id=sender_id)
        receiver = kid_acc.objects.get(kid_id=receiver_id)
        Message.objects.create(
            sender=sender,
            receiver=receiver,
            content=content
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp']
        }))
