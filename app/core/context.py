from contextvars import ContextVar

NO_REQUEST_ID = "-"
NO_CLIENT_IP = "-"
request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)
client_ip_var: ContextVar[str] = ContextVar("client_ip", default=NO_CLIENT_IP)
