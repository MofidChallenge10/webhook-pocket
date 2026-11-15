#!/usr/bin/env python3
"""Capture local webhook requests as redacted JSON Lines events."""
import argparse,datetime as dt,json,sys,unittest
from http.server import BaseHTTPRequestHandler,HTTPServer
MAX_BODY=1024*1024
def redact_headers(headers):
    hidden={"authorization","cookie","set-cookie","proxy-authorization"}
    return {k:("[redacted]" if k.lower() in hidden else v) for k,v in headers.items()}
class Tests(unittest.TestCase):
    def test_redaction(self):
        got=redact_headers({"Authorization":"Bearer x","Content-Type":"application/json","Cookie":"a=b"})
        self.assertEqual(got["Authorization"],"[redacted]"); self.assertEqual(got["Content-Type"],"application/json")
    def test_case_insensitive(self): self.assertEqual(redact_headers({"cOoKiE":"x"})["cOoKiE"],"[redacted]")
def serve(host,port,output):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try: size=int(self.headers.get("Content-Length","0"))
            except ValueError: self.send_error(400,"Invalid Content-Length"); return
            if size<0 or size>MAX_BODY: self.send_error(413,"Body limit is 1 MiB"); return
            body=self.rfile.read(size)
            event={"received_at":dt.datetime.now(dt.timezone.utc).isoformat(),"method":self.command,"path":self.path,
                   "headers":redact_headers(dict(self.headers.items())),"body_preview":body[:4000].decode("utf-8","replace")}
            with open(output,"a",encoding="utf-8") as stream: stream.write(json.dumps(event,ensure_ascii=False)+"\n")
            self.send_response(202); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(b'{"captured":true}\n')
        def log_message(self,fmt,*args): print("%s - %s"%(self.client_address[0],fmt%args))
    server=HTTPServer((host,port),Handler)
    print(f"Listening on http://{host}:{port} — POST requests are saved to {output}")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopping.")
    finally: server.server_close()
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=8787); ap.add_argument("--output",default="webhooks.jsonl"); a=ap.parse_args()
    if not 1<=a.port<=65535: ap.error("port must be between 1 and 65535")
    serve(a.host,a.port,a.output)
if __name__=="__main__":
    if "--self-test" in sys.argv: unittest.main(argv=[sys.argv[0]])
    else: main()
