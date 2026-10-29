# SQL injection and cross-site scripting

## SQL injection
It happens when user input is pasted into a database query so the input changes the meaning of the query. The fix is parameterised queries (prepared statements), where the database treats input strictly as data. Also use least-privilege database accounts and validate input. Escaping strings by hand is error-prone.

## Cross-site scripting (XSS)
XSS happens when an application shows user-supplied text in a page without making it safe, so a script can run in another user's browser. Defences: encode output for the place it is shown, use frameworks that escape by default, avoid inserting untrusted data as HTML, and add a Content Security Policy header.

## Related ideas
Cross-site request forgery tricks a logged-in user's browser into sending an unwanted request. Use anti-CSRF tokens and SameSite cookies. Set cookies as HttpOnly and Secure.
