"""Extract safe usage/termination metadata even when no valid answer completed."""
import json


def terminal_metadata(provider,body):
    if provider!='openai':return {}
    terminal=None
    for event in body.replace('\r\n','\n').split('\n\n'):
        data='\n'.join(line[5:].lstrip(' ') for line in event.splitlines() if line.startswith('data:'))
        if not data or data=='[DONE]':continue
        try:d=json.loads(data)
        except ValueError:continue
        if d.get('type') in ['response.completed','response.incomplete','response.failed']:
            terminal=d.get('response',{})
    if terminal is None:return {'termination':'missing_terminal_event'}
    return {'termination':terminal.get('status'),'incomplete_details':terminal.get('incomplete_details'),
            'usage':terminal.get('usage',{}),'returned_model':terminal.get('model'),
            'returned_settings':{k:terminal.get(k) for k in ['temperature','top_p','reasoning','max_output_tokens','truncation','service_tier']}}
