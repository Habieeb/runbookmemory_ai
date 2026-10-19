"""Opt-in Ansible callback: send failed/unreachable task metadata to RunbookMemory.
Configure ANSIBLE_CALLBACK_PLUGINS, ANSIBLE_CALLBACKS_ENABLED=runbookmemory,
RBM_API_KEY and RBM_API_URL. No secrets, task arguments, or raw results are sent.
"""
import json,os,urllib.request
from ansible.plugins.callback import CallbackBase
class CallbackModule(CallbackBase):
    CALLBACK_VERSION=2.0
    CALLBACK_TYPE='notification'
    CALLBACK_NAME='runbookmemory'
    CALLBACK_NEEDS_ENABLED=True
    def _send(self,result,kind):
        url=os.getenv('RBM_API_URL','http://127.0.0.1:8000/api/v1/events')
        key=os.getenv('RBM_API_KEY')
        if not key:return
        host=result._host.get_name()
        task=result._task.get_name()
        # Deliberately do not include result._result: it may contain credentials.
        payload={'service':host,'signal':'Ansible task failed' if kind=='failed' else 'Ansible host unreachable','details':f'Host: {host}; task: {task}; result: {kind}. Review Ansible controller logs for redacted error context.','source':'ansible','event_type':kind}
        request=urllib.request.Request(url,json.dumps(payload).encode(),{'Content-Type':'application/json','X-API-Key':key},method='POST')
        try:urllib.request.urlopen(request,timeout=2).close()
        except Exception as exc:self._display.warning(f'RunbookMemory callback could not send event: {type(exc).__name__}')
    def v2_runner_on_failed(self,result,ignore_errors=False):
        if not ignore_errors:self._send(result,'failed')
    def v2_runner_on_unreachable(self,result):self._send(result,'unreachable')
