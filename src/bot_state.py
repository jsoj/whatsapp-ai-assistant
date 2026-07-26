# Gestão de IDs de mensagens enviadas pela IA para evitar loops infinitos em conversas consigo mesmo
BOT_MESSAGE_IDS: set[str] = set()

def register_bot_message_id(msg_id: str):
    if msg_id:
        BOT_MESSAGE_IDS.add(msg_id)
        if len(BOT_MESSAGE_IDS) > 1000:
            BOT_MESSAGE_IDS.clear()

def is_bot_message(msg_id: str) -> bool:
    if not msg_id:
        return False
    if msg_id in BOT_MESSAGE_IDS:
        BOT_MESSAGE_IDS.discard(msg_id)
        return True
    return False
