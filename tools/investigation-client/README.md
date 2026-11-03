# Investigation test client

This temporary browser client uses an Entra user's delegated permission and the deployed TRACE API. It does not bypass Conditional Access. A submission can trigger a paid model call.

1. Create a single-tenant Entra SPA app registration for this client with redirect URI `http://localhost:8765/redirect.html`. Grant it the TRACE API's delegated `access_as_user` permission and obtain the required admin consent. Record its client ID and tenant ID.
2. On a workstation with Python 3, Node.js, `kubectl`, and authorized cluster access, run `npm ci` in this directory.
3. Run `kubectl port-forward -n trace svc/trace-api 18080:80` in one terminal and `python3 server.py` in another.
4. Open `http://localhost:8765`, enter the tenant and client IDs, and sign in. Submit the synthetic investigation once, then check its status and report. The default window applies to the current synthetic fixture only.

The proxy binds to localhost and forwards only investigation requests to the port-forward. Tokens stay in browser memory and are sent to the API through the local proxy. This is a test tool, not the deployed TRACE application.
