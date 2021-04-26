from leviot import conf, VERSION

base = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="refresh" content="5">
<title>{title}</title>
</head>
<body>
<h1>{title}</h1>
{content}
<br>
<div style="font-style: italic">Powered by LevIoT v""" + VERSION + """</div>
</body>
</html>
"""

index = base.format(
    title=conf.hostname,
    content="""
    <div>
        <h2>Basic control</h2> 
        <ul>
            <li>Power: {power} (turn <a href="/priv-api/on">ON</a>, <a href="/priv-api/off">OFF</a>)</li>
            <li>Fan speed: {speed} (set to <a href="/priv-api/fan?speed=0">Night</a>, <a href="/priv-api/fan?speed=1"
            >I</a>, <a href="/priv-api/fan?speed=2">II</a>, <a href="/priv-api/fan?speed=3">III</a>)</li>
        </ul>
    </div>
    <div>
        <h2>Timer</h2>
        <form action="/priv-api/timer" method="get">
            Set timer to: <input autofocus required inputmode="numeric"
            onfocus="this.setSelectionRange(this.value.length, this.value.length);" name="minutes" id="minutes"
            value="{timer}"><input type="submit" value="Set">
        </form>
        <a href="/priv-api/timer?minutes=0">Turn off timer</a>
    </div>
    """)
