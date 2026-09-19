import requests
from django.conf import settings

from core.models import AppSetting


def _get_setting(key, default=''):
    value = AppSetting.objects.filter(key=key).values_list('value', flat=True).first()
    return value if value not in (None, '') else default


def dispatch_whatsapp_notification(notification):
    if not notification.recipient_phone:
        return {'success': False, 'error': 'Aucun destinataire WhatsApp configuré.'}

    endpoint = _get_setting('whatsapp_api_endpoint')
    api_key = _get_setting('whatsapp_api_key')
    sender_id = _get_setting('whatsapp_sender_id')

    if not endpoint:
        return {
            'success': True,
            'provider_response': {
                'mode': 'local-dev-fallback',
                'status': 'queued',
                'recipient': notification.recipient_phone,
                'message': notification.message,
            },
        }

    payload = {
        'to': notification.recipient_phone,
        'message': notification.message,
        'sender': sender_id,
        'event_type': notification.event_type,
    }
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'} if api_key else {'Content-Type': 'application/json'}

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        if response.status_code >= 400 or not getattr(response, 'ok', True):
            return {'success': False, 'error': f'Erreur provider WhatsApp: {response.status_code}'}

        data = response.json() if hasattr(response, 'json') else {}
        return {'success': True, 'provider_response': data}
    except requests.RequestException as exc:
        return {'success': False, 'error': str(exc)}
